"""
Consolidate Step

Consolidates multiple resolved SoA tables into a unified per-protocol structure.

This is structural consolidation only:
- Activity matching across tables (exact, fuzzy, cross-parent)
- Column alignment into timeline segments (main, domain, track, subsidiary)
- Annotation consolidation with deduplication
- Schedule matrix construction

Semantic interpretation (USDM timeline patterns, annotation logic) is out of scope.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Tuple, Union
from collections import defaultdict

from .base import PipelineStepBase
from . import config


# =============================================================================
# Matching Thresholds
# =============================================================================

AUTO_MATCH_THRESHOLD = 0.85
CROSS_PARENT_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.60


# =============================================================================
# Utility Functions
# =============================================================================

def detect_population_track(table_purpose: str, table_title: str = "") -> Optional[str]:
    """Detect population track from table purpose/title text."""
    text = f"{table_purpose} {table_title}".lower()
    if 'nonrespond' in text or 'non-respond' in text:
        return 'Nonresponders'
    if 'responder' in text:
        return 'Responders'
    if 'maintenance' in text:
        return 'Maintenance'
    return None


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().replace('-', ' ').replace('/', ' ')
    text = re.sub(r'\([^)]*\)', '', text)
    return ' '.join(text.split()).strip()


def get_word_set(text: str) -> set:
    """Extract significant words from text."""
    return {w for w in normalize_text(text).split() if len(w) > 2}


def word_overlap_score(text1: str, text2: str) -> float:
    """Calculate word overlap score between two texts."""
    words1, words2 = get_word_set(text1), get_word_set(text2)
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    coverage = len(intersection) / min(len(words1), len(words2))
    jaccard = len(intersection) / len(union)
    return 0.6 * coverage + 0.4 * jaccard


def find_best_match(name: str, candidates: list, threshold: float = 0.5):
    """Find best matching candidate by word overlap."""
    best, best_score = None, 0.0
    for c in candidates:
        score = word_overlap_score(name, c['activity_name'])
        if score > best_score and score >= threshold:
            best, best_score = c, score
    return best, best_score


def extract_property_hierarchy(table: dict) -> List[dict]:
    """Extract property hierarchy from a resolved table."""
    props = table.get('schedule_properties', [])
    # Sort: hierarchical first (by level), then qualifiers (level=None) by type
    def sort_key(p):
        level = p.get('hierarchical_level')
        if level is not None:
            return (0, level, '')  # Hierarchical first, sorted by level
        return (1, 0, p.get('property_type', ''))  # Qualifiers after, sorted by type
    
    sorted_props = sorted(props, key=sort_key)
    return [
        {
            'hierarchical_level': p.get('hierarchical_level'),  # Preserve None
            'property_name': p.get('property_name', ''),
            'property_type': p.get('property_type', 'other'),
            'property_comment': p.get('property_comment', '')
        }
        for p in sorted_props
    ]


# =============================================================================
# Activity Consolidation
# =============================================================================

@dataclass
class UnifiedActivity:
    """An activity consolidated across tables."""
    xact_id: str
    activity_name: str
    parent_name: str
    qualified_key: str
    is_section_header: bool
    hierarchy_level: int = 0
    parent_xact_id: Optional[str] = None
    display_order: int = 0
    source_refs: list = field(default_factory=list)
    name_variations: list = field(default_factory=list)
    match_status: str = "new"
    match_confidence: float = 1.0

    def add_source(self, table_id: str, table_num: int, activity_id: str, 
                   row_position: int, activity_name: str):
        """Add a source reference."""
        self.source_refs.append({
            'table_id': table_id,
            'table_num': table_num,
            'activity_id': activity_id,
            'row_position': row_position
        })
        if activity_name not in self.name_variations:
            self.name_variations.append(activity_name)

    @property
    def table_nums(self) -> Set[int]:
        """Get set of table numbers this activity appears in."""
        return {sr['table_num'] for sr in self.source_refs}
    
    def get_primary_row_position(self) -> Tuple[int, int]:
        """Get (table_num, row_position) from earliest source for ordering."""
        if not self.source_refs:
            return (999, 999)
        # Sort by table_num then row_position, return first
        sorted_refs = sorted(self.source_refs, key=lambda r: (r['table_num'], r['row_position']))
        return (sorted_refs[0]['table_num'], sorted_refs[0]['row_position'])

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            'xact_id': self.xact_id,
            'activity_name': self.activity_name,
            'parent_name': self.parent_name,
            'parent_xact_id': self.parent_xact_id,
            'hierarchy_level': self.hierarchy_level,
            'display_order': self.display_order,
            'qualified_key': self.qualified_key,
            'is_section_header': self.is_section_header,
            'source_refs': self.source_refs,
            'name_variations': self.name_variations,
            'match_status': self.match_status,
            'match_confidence': self.match_confidence,
            'table_count': len(self.table_nums)
        }


class ActivityConsolidator:
    """Consolidates activities across multiple tables."""

    def __init__(self):
        self.unified_activities: List[UnifiedActivity] = []
        self.xact_counter = 0
        self.key_to_unified: Dict[str, UnifiedActivity] = {}
        self.review_queue: List[dict] = []
        self.match_stats = {
            'exact': 0,
            'fuzzy_auto': 0,
            'fuzzy_cross_parent': 0,
            'fuzzy_review': 0,
            'new': 0
        }

    def _make_xact_id(self) -> str:
        """Generate next cross-table activity ID."""
        self.xact_counter += 1
        return f"xact-{self.xact_counter:03d}"

    def _get_parent_name(self, act: dict, act_by_id: dict) -> str:
        """Get parent activity name."""
        pid = act.get('parent_activity_id')
        return act_by_id[pid]['activity_name'] if pid and pid in act_by_id else ""

    def _find_match(self, act: dict, parent_name: str, table_num: int):
        """Find matching unified activity using multiple strategies."""
        act_name = act['activity_name']
        qual_key = f"{parent_name}::{act_name}"

        # Strategy 1: Exact qualified key
        if qual_key in self.key_to_unified:
            ua = self.key_to_unified[qual_key]
            if table_num not in ua.table_nums:
                return ua, 'exact', 1.0

        # Strategy 2: Exact name match
        for ua in self.unified_activities:
            if ua.activity_name == act_name and table_num not in ua.table_nums:
                return ua, 'exact', 1.0

        # Strategy 3: Fuzzy same-parent
        same_parent = [
            ua for ua in self.unified_activities
            if table_num not in ua.table_nums and ua.parent_name == parent_name
        ]
        if same_parent:
            candidates = [{'activity_name': ua.activity_name, 'ua': ua} for ua in same_parent]
            best, score = find_best_match(act_name, candidates)
            if best and score >= AUTO_MATCH_THRESHOLD:
                return best['ua'], 'fuzzy_auto', score
            elif best and score >= REVIEW_THRESHOLD:
                return best['ua'], 'fuzzy_review', score

        # Strategy 4: Fuzzy cross-parent
        cross_parent = [
            ua for ua in self.unified_activities
            if table_num not in ua.table_nums 
            and ua.parent_name != parent_name 
            and not ua.is_section_header
        ]
        if cross_parent:
            candidates = [{'activity_name': ua.activity_name, 'ua': ua} for ua in cross_parent]
            best, score = find_best_match(act_name, candidates)
            if best and score >= CROSS_PARENT_THRESHOLD:
                return best['ua'], 'fuzzy_cross_parent', score

        return None, 'new', 0.0

    def process_table(self, table: dict, table_num: int, is_base: bool = False):
        """Process activities from a resolved table."""
        acts = table['activities']
        act_by_id = {a['activity_id']: a for a in acts}
        table_id = table['table_metadata']['table_id']

        for act in acts:
            act_name = act['activity_name']
            parent_name = self._get_parent_name(act, act_by_id)
            qual_key = f"{parent_name}::{act_name}"

            if is_base:
                ua = UnifiedActivity(
                    xact_id=self._make_xact_id(),
                    activity_name=act_name,
                    parent_name=parent_name,
                    qualified_key=qual_key,
                    is_section_header=act.get('is_section_header', False),
                    hierarchy_level=act.get('hierarchy_level', 0)
                )
                ua.add_source(table_id, table_num, act['activity_id'], 
                              act['row_position'], act_name)
                self.unified_activities.append(ua)
                self.key_to_unified[qual_key] = ua
                self.match_stats['new'] += 1
            else:
                matched_ua, status, confidence = self._find_match(act, parent_name, table_num)

                if matched_ua:
                    matched_ua.add_source(table_id, table_num, act['activity_id'],
                                          act['row_position'], act_name)
                    matched_ua.match_status = status
                    matched_ua.match_confidence = min(matched_ua.match_confidence, confidence)
                    self.match_stats[status] += 1

                    if status == 'fuzzy_cross_parent' and matched_ua.parent_name != parent_name:
                        matched_ua.parent_name = f"{matched_ua.parent_name} / {parent_name}"

                    if status == 'fuzzy_review':
                        self.review_queue.append({
                            'xact_id': matched_ua.xact_id,
                            'confidence': confidence,
                            'existing_name': matched_ua.activity_name,
                            'new_name': act_name
                        })
                else:
                    ua = UnifiedActivity(
                        xact_id=self._make_xact_id(),
                        activity_name=act_name,
                        parent_name=parent_name,
                        qualified_key=qual_key,
                        is_section_header=act.get('is_section_header', False),
                        hierarchy_level=act.get('hierarchy_level', 0)
                    )
                    ua.add_source(table_id, table_num, act['activity_id'],
                                  act['row_position'], act_name)
                    self.unified_activities.append(ua)
                    self.key_to_unified[qual_key] = ua
                    self.match_stats['new'] += 1

    def resolve_parent_references(self):
        """Resolve parent_xact_id by matching parent_name to activity_name.
        
        Must be called after all tables are processed.
        """
        # Build name -> xact_id lookup (use first match for ambiguous names)
        name_to_xact: Dict[str, str] = {}
        for ua in self.unified_activities:
            if ua.activity_name not in name_to_xact:
                name_to_xact[ua.activity_name] = ua.xact_id
        
        # Resolve parent references
        for ua in self.unified_activities:
            if ua.parent_name:
                # Handle cross-parent matches that have " / " in parent_name
                # Use first parent for resolution
                primary_parent = ua.parent_name.split(' / ')[0] if ' / ' in ua.parent_name else ua.parent_name
                ua.parent_xact_id = name_to_xact.get(primary_parent)

    def compute_display_order(self):
        """Compute display_order for hierarchical presentation.
        
        Assigns sequential display_order values so activities appear:
        1. Parents before their children
        2. Siblings in source row_position order (earliest table first)
        3. Activities from later tables inserted near their parent/siblings
        
        Must be called after resolve_parent_references().
        """
        # Build lookup structures
        xact_to_ua: Dict[str, UnifiedActivity] = {ua.xact_id: ua for ua in self.unified_activities}
        
        # Build children lookup: parent_xact_id -> list of children
        children_of: Dict[Optional[str], List[UnifiedActivity]] = defaultdict(list)
        for ua in self.unified_activities:
            children_of[ua.parent_xact_id].append(ua)
        
        # Sort children by their primary row position (table_num, row_position)
        for parent_id in children_of:
            children_of[parent_id].sort(key=lambda ua: ua.get_primary_row_position())
        
        # Depth-first traversal to assign display_order
        display_counter = 0
        
        def assign_order(ua: UnifiedActivity):
            nonlocal display_counter
            display_counter += 1
            ua.display_order = display_counter
            # Recursively process children
            for child in children_of.get(ua.xact_id, []):
                assign_order(child)
        
        # Start with top-level activities (no parent)
        for ua in children_of.get(None, []):
            assign_order(ua)
        
        # Re-sort unified_activities by display_order
        self.unified_activities.sort(key=lambda ua: ua.display_order)


# =============================================================================
# Column Consolidation
# =============================================================================

@dataclass
class PropertyInfo:
    """Property metadata from a source table."""
    property_id: str
    property_type: str
    property_name: str
    hierarchical_level: Optional[int]
    property_comment: str = ""

    def to_dict(self) -> dict:
        return {
            'property_id': self.property_id,
            'property_type': self.property_type,
            'property_name': self.property_name,
            'hierarchical_level': self.hierarchical_level,
            'property_comment': self.property_comment
        }


@dataclass
class ColumnPropertyValue:
    """A property value for a specific column."""
    property_id: str
    property_type: str
    property_name: str
    hierarchical_level: Optional[int]
    value: str

    def to_dict(self) -> dict:
        return {
            'level': self.hierarchical_level,
            'property_type': self.property_type,
            'property_name': self.property_name,
            'value': self.value
        }


@dataclass
class UnifiedColumn:
    """A column in the unified timeline."""
    xcol_id: str
    composite_label: str
    segment: str
    property_values: List[ColumnPropertyValue] = field(default_factory=list)
    population_track: Optional[str] = None
    source_columns: list = field(default_factory=list)

    @property
    def table_nums(self) -> Set[int]:
        return {sc['table_num'] for sc in self.source_columns}

    def to_dict(self) -> dict:
        return {
            'xcol_id': self.xcol_id,
            'composite_label': self.composite_label,
            'segment': self.segment,
            'population_track': self.population_track,
            'property_values': [pv.to_dict() for pv in self.property_values],
            'source_columns': self.source_columns
        }


class ColumnConsolidator:
    """Builds unified columns preserving property structure."""

    def __init__(self):
        self.columns: List[UnifiedColumn] = []
        self.xcol_counter = 0
        # Keys: int for hierarchical levels, str (f"q_{type}") for qualifiers
        self.property_info: Dict[Union[int, str], PropertyInfo] = {}
        self.max_level = 0

    def _make_xcol_id(self) -> str:
        """Generate next cross-table column ID."""
        self.xcol_counter += 1
        return f"xcol-{self.xcol_counter:03d}"

    def _build_property_lookup(self, table: dict) -> Dict[str, dict]:
        """Build lookup from property_id to property info."""
        return {
            p['property_id']: {
                'property_type': p.get('property_type', 'other'),
                'property_name': p.get('property_name', ''),
                'hierarchical_level': p.get('hierarchical_level'),  # Preserve None
                'property_comment': p.get('property_comment', '')
            }
            for p in table.get('schedule_properties', [])
        }

    def _extract_column_properties(self, column: dict, 
                                    prop_lookup: dict) -> List[ColumnPropertyValue]:
        """Extract property values for a column."""
        result = []
        for cv in column.get('column_values', []):
            prop_id = cv.get('property_id', '')
            if prop_id in prop_lookup:
                info = prop_lookup[prop_id]
                level = info['hierarchical_level']  # May be None for qualifiers
                result.append(ColumnPropertyValue(
                    property_id=prop_id,
                    property_type=info['property_type'],
                    property_name=info['property_name'],
                    hierarchical_level=level,
                    value=cv.get('value', '')
                ))

                # Key for property_info: int for hierarchical, str for qualifiers
                if level is not None:
                    prop_key = level
                    self.max_level = max(self.max_level, level)
                else:
                    # Include property_name to avoid collision when multiple
                    # qualifiers share the same type (e.g., two modality rows:
                    # "Fasting Visit" and "Telephone Visit")
                    prop_key = f"q_{info['property_type']}_{info['property_name']}"
                
                if prop_key not in self.property_info:
                    self.property_info[prop_key] = PropertyInfo(
                        property_id=prop_id,
                        property_type=info['property_type'],
                        property_name=info['property_name'],
                        hierarchical_level=level,
                        property_comment=info['property_comment']
                    )

        # Sort: hierarchical by level, then qualifiers
        def sort_key(x):
            if x.hierarchical_level is not None:
                return (0, x.hierarchical_level)
            return (1, x.property_type)
        result.sort(key=sort_key)
        return result

    def process_tables(self, tables: Dict[int, dict], 
                       tables_by_type: Dict[str, List[int]]):
        """Process all tables and build unified columns."""
        # Main timeline
        for tnum in tables_by_type.get('main_soa', []):
            self._add_table_columns(tables[tnum], tnum, 'main', None)

        # Continuation extends main
        for tnum in tables_by_type.get('continuation', []):
            self._add_table_columns(tables[tnum], tnum, 'main', None)

        # Domain tables share main timeline columns (same column structure)
        for tnum in tables_by_type.get('domain', []):
            self._add_table_columns(tables[tnum], tnum, 'domain', None)

        # Track tables have separate timelines for different populations/phases
        for tnum in tables_by_type.get('track', []):
            table = tables[tnum]
            meta = table['table_metadata']
            track = meta.get('track_label') or detect_population_track(
                meta.get('table_purpose', ''),
                meta.get('table_title', '')
            ) or f"Track-T{tnum}"
            self._add_table_columns(table, tnum, 'track', track)

        # Subsidiary
        for tnum in tables_by_type.get('subsidiary', []):
            self._add_table_columns(tables[tnum], tnum, 'subsidiary', None)

    def _add_table_columns(self, table: dict, table_num: int, 
                           segment: str, track: Optional[str]):
        """Add columns from a table."""
        table_id = table['table_metadata']['table_id']
        prop_lookup = self._build_property_lookup(table)

        data_cols = [
            c for c in table['schedule_columns']
            if not c.get('is_label_column', False)
        ]

        for col in data_cols:
            prop_values = self._extract_column_properties(col, prop_lookup)

            ucol = UnifiedColumn(
                xcol_id=self._make_xcol_id(),
                composite_label=col.get('composite_label', ''),
                segment=segment,
                property_values=prop_values,
                population_track=track
            )
            ucol.source_columns.append({
                'table_id': table_id,
                'table_num': table_num,
                'column_id': col['column_id'],
                'column_position': col['column_position']
            })
            self.columns.append(ucol)

    def get_columns_by_segment(self) -> Dict[str, List[UnifiedColumn]]:
        """Get columns organized by segment."""
        by_segment = defaultdict(list)
        for col in self.columns:
            by_segment[col.segment].append(col)
        return dict(by_segment)

    def get_property_hierarchy(self) -> List[PropertyInfo]:
        """Get unified property hierarchy (hierarchical first, then qualifiers)."""
        # Separate hierarchical (int keys) from qualifiers (str keys)
        hierarchical = [(k, v) for k, v in self.property_info.items() if isinstance(k, int)]
        qualifiers = [(k, v) for k, v in self.property_info.items() if isinstance(k, str)]
        
        # Sort hierarchical by level, qualifiers by type
        hierarchical.sort(key=lambda x: x[0])
        qualifiers.sort(key=lambda x: x[0])
        
        return [v for _, v in hierarchical] + [v for _, v in qualifiers]


# =============================================================================
# Annotation Consolidation
# =============================================================================

def normalize_annotation_text(text: str) -> str:
    """Normalize annotation text for duplicate detection."""
    # Lowercase, collapse whitespace, strip
    return ' '.join(text.lower().split())


@dataclass
class UnifiedAnnotation:
    """An annotation consolidated across tables."""
    xannot_id: str
    annotation_type: str
    annotation_text: str
    normalized_text: str
    source_occurrences: list = field(default_factory=list)
    referenced_xacts: list = field(default_factory=list)
    referenced_xcols: list = field(default_factory=list)
    cell_references: list = field(default_factory=list)

    def add_occurrence(self, table_num: int, marker: str, annot_id: str):
        """Add a source occurrence."""
        self.source_occurrences.append({
            'table_num': table_num,
            'marker': marker,
            'annotation_id': annot_id
        })

    def get_display_markers(self) -> str:
        """Generate human-readable marker display (e.g., 'T1:e, T2-4:a')."""
        if not self.source_occurrences:
            return ""
        
        # Group by marker
        by_marker: Dict[str, List[int]] = defaultdict(list)
        for occ in self.source_occurrences:
            by_marker[occ['marker']].append(occ['table_num'])
        
        parts = []
        for marker, tables in sorted(by_marker.items(), key=lambda x: min(x[1])):
            tables = sorted(tables)
            if len(tables) == 1:
                parts.append(f"T{tables[0]}:{marker}")
            elif tables == list(range(min(tables), max(tables) + 1)):
                # Consecutive range
                parts.append(f"T{min(tables)}-{max(tables)}:{marker}")
            else:
                parts.append(f"T{','.join(str(t) for t in tables)}:{marker}")
        
        return ", ".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            'xannot_id': self.xannot_id,
            'annotation_type': self.annotation_type,
            'annotation_text': self.annotation_text,
            'display_markers': self.get_display_markers(),
            'source_occurrences': self.source_occurrences,
            'referenced_xacts': self.referenced_xacts,
            'referenced_xcols': self.referenced_xcols,
            'cell_references': self.cell_references,
            'occurrence_count': len(self.source_occurrences)
        }


class AnnotationConsolidator:
    """Consolidates annotations across multiple tables."""

    def __init__(self):
        self.unified_annotations: List[UnifiedAnnotation] = []
        self.xannot_counter = 0
        self.text_to_unified: Dict[str, UnifiedAnnotation] = {}  # normalized_text -> UA
        self.source_annotation_count = 0

    def _make_xannot_id(self) -> str:
        """Generate next cross-table annotation ID."""
        self.xannot_counter += 1
        return f"xannot-{self.xannot_counter:03d}"

    def process_tables(
        self,
        tables: Dict[int, dict],
        act_to_xact: Dict[Tuple[int, str], str],
        col_to_xcol: Dict[Tuple[int, str], str]
    ):
        """Process annotations from all tables.
        
        Args:
            tables: Dict of table_num -> resolved table data
            act_to_xact: Mapping (table_num, activity_id) -> xact_id
            col_to_xcol: Mapping (table_num, column_id) -> xcol_id
        """
        for table_num, table in sorted(tables.items()):
            annotations = table.get('annotations', [])
            
            # Build property_id -> column_ids mapping for this table
            prop_to_cols: Dict[str, List[str]] = defaultdict(list)
            for col in table.get('schedule_columns', []):
                col_id = col.get('column_id', '')
                for cv in col.get('column_values', []):
                    prop_id = cv.get('property_id', '')
                    if prop_id and col_id not in prop_to_cols[prop_id]:
                        prop_to_cols[prop_id].append(col_id)
            
            # Build row_position -> activity_id mapping for marker_locations fallback
            row_to_act: Dict[int, str] = {}
            for act in table.get('activities', []):
                rp = act.get('row_position')
                aid = act.get('activity_id', '')
                if rp is not None and aid:
                    row_to_act[rp] = aid

            for annot in annotations:
                self.source_annotation_count += 1
                self._process_annotation(annot, table_num, act_to_xact, col_to_xcol, prop_to_cols, row_to_act)

    def _process_annotation(
        self,
        annot: dict,
        table_num: int,
        act_to_xact: Dict[Tuple[int, str], str],
        col_to_xcol: Dict[Tuple[int, str], str],
        prop_to_cols: Dict[str, List[str]],
        row_to_act: Dict[int, str]
    ):
        """Process a single annotation."""
        text = annot.get('annotation_text', '')
        normalized = normalize_annotation_text(text)
        marker = annot.get('annotation_marker', '')
        annot_id = annot.get('annotation_id', '')
        annot_type = annot.get('annotation_type', 'footnote')
        
        # Map referenced elements to cross-table IDs
        refs = annot.get('referenced_elements', {})
        
        xacts = []
        for act_id in refs.get('activity_ids', []):
            xact = act_to_xact.get((table_num, act_id))
            if xact and xact not in xacts:
                xacts.append(xact)
        
        # Fallback: if no activity_ids resolved, use marker_locations
        # This catches instruction-style annotations where markers were placed
        # in a separate column (not on activity rows), so the resolver couldn't
        # map them to activity_ids — but marker_locations preserves row_position.
        if not xacts:
            for loc in annot.get('marker_locations', []):
                rp = loc.get('row_position')
                if rp is not None and rp in row_to_act:
                    act_id = row_to_act[rp]
                    xact = act_to_xact.get((table_num, act_id))
                    if xact and xact not in xacts:
                        xacts.append(xact)
        
        xcols = []
        # Direct column references only — do NOT expand property references
        # to columns. Property-to-column expansion is over-broad: an annotation
        # referencing the "cycle" property would incorrectly map to all columns
        # including screening and follow-up. Property-level annotations keep
        # empty referenced_xcols; the annotation text conveys semantic scope.
        for col_id in refs.get('column_ids', []):
            xcol = col_to_xcol.get((table_num, col_id))
            if xcol and xcol not in xcols:
                xcols.append(xcol)
        
        cell_refs = []
        for cell_ref in refs.get('cell_references', []):
            xact = act_to_xact.get((table_num, cell_ref.get('activity_id', '')))
            xcol = col_to_xcol.get((table_num, cell_ref.get('column_id', '')))
            if xact and xcol:
                cell_refs.append({'xact_id': xact, 'xcol_id': xcol})
        
        # Check for existing annotation with same normalized text
        if normalized in self.text_to_unified:
            # Deduplicate: add occurrence to existing
            ua = self.text_to_unified[normalized]
            ua.add_occurrence(table_num, marker, annot_id)
            
            # Merge referenced elements (avoid duplicates)
            for xact in xacts:
                if xact not in ua.referenced_xacts:
                    ua.referenced_xacts.append(xact)
            for xcol in xcols:
                if xcol not in ua.referenced_xcols:
                    ua.referenced_xcols.append(xcol)
            for cell_ref in cell_refs:
                if cell_ref not in ua.cell_references:
                    ua.cell_references.append(cell_ref)
        else:
            # New unique annotation
            ua = UnifiedAnnotation(
                xannot_id=self._make_xannot_id(),
                annotation_type=annot_type,
                annotation_text=text,
                normalized_text=normalized,
                referenced_xacts=xacts,
                referenced_xcols=xcols,
                cell_references=cell_refs
            )
            ua.add_occurrence(table_num, marker, annot_id)
            self.unified_annotations.append(ua)
            self.text_to_unified[normalized] = ua

    def get_stats(self) -> dict:
        """Get consolidation statistics."""
        unified_count = len(self.unified_annotations)
        dedup_count = self.source_annotation_count - unified_count
        dedup_percent = round(dedup_count / self.source_annotation_count * 100) if self.source_annotation_count else 0
        
        # Count by type
        by_type: Dict[str, int] = defaultdict(int)
        for ua in self.unified_annotations:
            by_type[ua.annotation_type] += 1
        
        return {
            'source_annotation_count': self.source_annotation_count,
            'unified_annotation_count': unified_count,
            'deduplicated_count': dedup_count,
            'deduplication_percent': dedup_percent,
            'by_type': dict(by_type)
        }


# =============================================================================
# Validation
# =============================================================================

@dataclass
class ConsolidationValidationResult:
    """Results of consolidated output validation."""
    structure_valid: bool = True
    references_valid: bool = True
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        elif self.warnings:
            return "consolidated_with_warnings"
        else:
            return "consolidated"


def validate_consolidated(data: dict) -> ConsolidationValidationResult:
    """Validate consolidated output structure and cross-references.
    
    Checks:
    - Required top-level fields exist
    - ID formats follow patterns (xact-NNN, xcol-NNN, xannot-NNN)
    - Cross-references point to existing IDs
    - Schedule matrix references valid activities and columns
    - Annotations reference valid activities and columns
    """
    result = ConsolidationValidationResult()
    
    # Check required top-level fields
    required_fields = [
        "schema_name", "schema_version", "protocol_id",
        "consolidation_metadata", "unified_activities",
        "timeline_segments", "schedule_matrix", "unified_annotations"
    ]
    for field_name in required_fields:
        if field_name not in data:
            result.errors.append(f"Missing required field: {field_name}")
            result.structure_valid = False
    
    if not result.structure_valid:
        return result
    
    # Validate schema identifiers
    if data.get("schema_name") != "soa-tables-consolidated":
        result.errors.append(f"Invalid schema_name: {data.get('schema_name')}")
    
    # Build sets of valid IDs for cross-reference validation
    valid_xact_ids: Set[str] = set()
    valid_xcol_ids: Set[str] = set()
    
    # Validate unified_activities
    xact_pattern = re.compile(r'^xact-\d{3}$')
    for ua in data.get("unified_activities", []):
        xact_id = ua.get("xact_id", "")
        if not xact_pattern.match(xact_id):
            result.errors.append(f"Invalid xact_id format: {xact_id}")
        else:
            valid_xact_ids.add(xact_id)
        
        # Check required activity fields
        if not ua.get("activity_name"):
            result.warnings.append(f"{xact_id}: empty activity_name")
        if not ua.get("source_refs"):
            result.warnings.append(f"{xact_id}: no source_refs")
    
    # Validate timeline_segments and collect column IDs
    xcol_pattern = re.compile(r'^xcol-\d{3}$')
    valid_segments = {"main", "domain", "track", "subsidiary"}
    
    for segment, columns in data.get("timeline_segments", {}).items():
        if segment not in valid_segments:
            result.warnings.append(f"Unknown timeline segment: {segment}")
        
        for col in columns:
            xcol_id = col.get("xcol_id", "")
            if not xcol_pattern.match(xcol_id):
                result.errors.append(f"Invalid xcol_id format: {xcol_id}")
            else:
                valid_xcol_ids.add(xcol_id)
    
    # Validate schedule_matrix references
    for cell in data.get("schedule_matrix", []):
        xact_id = cell.get("xact_id", "")
        xcol_id = cell.get("xcol_id", "")
        
        if xact_id not in valid_xact_ids:
            result.errors.append(f"schedule_matrix references unknown xact_id: {xact_id}")
            result.references_valid = False
        if xcol_id not in valid_xcol_ids:
            result.errors.append(f"schedule_matrix references unknown xcol_id: {xcol_id}")
            result.references_valid = False
    
    # Validate unified_annotations
    xannot_pattern = re.compile(r'^xannot-\d{3}$')
    for ua in data.get("unified_annotations", []):
        xannot_id = ua.get("xannot_id", "")
        if not xannot_pattern.match(xannot_id):
            result.errors.append(f"Invalid xannot_id format: {xannot_id}")
        
        # Validate referenced IDs exist
        for ref_xact in ua.get("referenced_xacts", []):
            if ref_xact not in valid_xact_ids:
                result.errors.append(f"{xannot_id} references unknown xact_id: {ref_xact}")
                result.references_valid = False
        
        for ref_xcol in ua.get("referenced_xcols", []):
            if ref_xcol not in valid_xcol_ids:
                result.errors.append(f"{xannot_id} references unknown xcol_id: {ref_xcol}")
                result.references_valid = False
        
        for cell_ref in ua.get("cell_references", []):
            if cell_ref.get("xact_id") not in valid_xact_ids:
                result.errors.append(f"{xannot_id} cell_ref has unknown xact_id")
                result.references_valid = False
            if cell_ref.get("xcol_id") not in valid_xcol_ids:
                result.errors.append(f"{xannot_id} cell_ref has unknown xcol_id")
                result.references_valid = False
    
        
        # Warn about orphaned annotations (no references at all)
        has_refs = (
            ua.get("referenced_xacts")
            or ua.get("referenced_xcols")
            or ua.get("cell_references")
        )
        if not has_refs:
            result.warnings.append(
                f"{xannot_id}: orphaned annotation \u2014 no referenced_xacts, "
                f"referenced_xcols, or cell_references"
            )
    
    # Validate property_hierarchy completeness against source tables
    consolidated_props = data.get("property_hierarchy", [])
    consolidated_names = {p.get("property_name", "") for p in consolidated_props}
    source_tables = data.get("consolidation_metadata", {}).get("source_tables", [])
    for st in source_tables:
        for sp in st.get("property_hierarchy", []):
            sp_name = sp.get("property_name", "")
            if sp_name and sp_name not in consolidated_names:
                tnum = st.get("table_num", "?")
                ptype = sp.get("property_type", "?")
                result.warnings.append(
                    f"property_hierarchy missing '{sp_name}' "
                    f"(type={ptype}) from table {tnum}"
                )
    return result


# =============================================================================
# Cross-Table Mappings
# =============================================================================

def build_cross_table_mappings(
    unified_activities: List[UnifiedActivity],
    columns: ColumnConsolidator
) -> Tuple[Dict[Tuple[int, str], str], Dict[Tuple[int, str], str]]:
    """Build mappings from (table_num, id) to cross-table IDs.
    
    Returns:
        Tuple of (act_to_xact, col_to_xcol) mappings
    """
    # Activity lookup: (table_num, activity_id) -> xact_id
    act_to_xact = {}
    for ua in unified_activities:
        for sr in ua.source_refs:
            act_to_xact[(sr['table_num'], sr['activity_id'])] = ua.xact_id

    # Column lookup: (table_num, column_id) -> xcol_id
    col_to_xcol = {}
    for ucol in columns.columns:
        for sc in ucol.source_columns:
            col_to_xcol[(sc['table_num'], sc['column_id'])] = ucol.xcol_id

    return act_to_xact, col_to_xcol


# =============================================================================
# Schedule Matrix
# =============================================================================

def build_schedule_matrix(
    tables: Dict[int, dict],
    act_to_xact: Dict[Tuple[int, str], str],
    col_to_xcol: Dict[Tuple[int, str], str]
) -> List[dict]:
    """Build matrix mapping (xact_id, xcol_id) -> cell data.
    
    Args:
        tables: Dict of table_num -> resolved table data
        act_to_xact: Mapping (table_num, activity_id) -> xact_id
        col_to_xcol: Mapping (table_num, column_id) -> xcol_id
    
    Returns:
        List of schedule cells with consolidated values
    """
    # Build matrix
    matrix: Dict[Tuple[str, str], dict] = {}
    for tnum, table in tables.items():
        for sched in table['activity_schedule']:
            xact = act_to_xact.get((tnum, sched['activity_id']))
            xcol = col_to_xcol.get((tnum, sched['column_id']))

            if xact and xcol:
                key = (xact, xcol)
                if key not in matrix:
                    matrix[key] = {'values': {}}

                if sched.get('cell_value'):
                    matrix[key]['values'][tnum] = sched['cell_value']

    # Compute consolidated values and convert to list
    result = []
    for (xact, xcol), data in matrix.items():
        values = list(data['values'].values())
        unique = set(v for v in values if v)

        if len(unique) == 1:
            consolidated = unique.pop()
        elif len(unique) > 1:
            consolidated = "[" + ", ".join(sorted(unique)) + "]"
        else:
            consolidated = ""

        if consolidated:
            result.append({
                'xact_id': xact,
                'xcol_id': xcol,
                'consolidated_value': consolidated,
                'source_values': {str(k): v for k, v in data['values'].items()}
            })

    return result


# =============================================================================
# Core Consolidation Function
# =============================================================================

def consolidate_tables(protocol_id: str, resolved_files: List[Path]) -> dict:
    """Consolidate multiple resolved tables into unified structure.
    
    Args:
        protocol_id: Protocol identifier
        resolved_files: List of paths to resolved JSON files
        
    Returns:
        Consolidated JSON data structure
    """
    # Load tables
    tables = {}
    for f in resolved_files:
        with open(f) as fp:
            data = json.load(fp)
        tables[data['table_metadata']['table_number']] = data

    # Classify by type
    tables_by_type = defaultdict(list)
    for num, t in tables.items():
        tables_by_type[t['table_metadata']['table_type']].append(num)

    # Activity consolidation
    act_consolidator = ActivityConsolidator()

    # Process main tables first as base
    for num in tables_by_type.get('main_soa', []):
        act_consolidator.process_table(tables[num], num, is_base=True)

    # Process remaining tables (except reference)
    for num in sorted(tables.keys()):
        if num in tables_by_type.get('main_soa', []):
            continue
        if num in tables_by_type.get('reference', []):
            continue
        act_consolidator.process_table(tables[num], num, is_base=False)

    # Resolve parent_xact_id references now that all activities exist
    act_consolidator.resolve_parent_references()
    
    # Compute display_order for hierarchical presentation
    act_consolidator.compute_display_order()

    # Column consolidation
    col_consolidator = ColumnConsolidator()
    col_consolidator.process_tables(tables, tables_by_type)

    # Build cross-table mappings (used by matrix and annotation consolidation)
    act_to_xact, col_to_xcol = build_cross_table_mappings(
        act_consolidator.unified_activities,
        col_consolidator
    )

    # Build schedule matrix
    matrix = build_schedule_matrix(tables, act_to_xact, col_to_xcol)

    # Annotation consolidation
    annot_consolidator = AnnotationConsolidator()
    annot_consolidator.process_tables(tables, act_to_xact, col_to_xcol)

    # Calculate stats
    total_src = sum(
        len(t['activities']) for t in tables.values()
        if t['table_metadata']['table_type'] != 'reference'
    )
    unified_count = len(act_consolidator.unified_activities)
    compression = round((1 - unified_count / total_src) * 100) if total_src else 0

    by_segment = col_consolidator.get_columns_by_segment()
    prop_hierarchy = col_consolidator.get_property_hierarchy()

    # Build output
    return {
        "schema_name": "soa-tables-consolidated",
        "schema_version": "1.1",
        "protocol_id": protocol_id,
        "consolidation_metadata": {
            "consolidated_at": datetime.now(timezone.utc).isoformat(),
            "consolidator": "soa2usdm.steps.consolidate v1.1",
            "source_tables": [
                {
                    "table_id": t['table_metadata']['table_id'],
                    "table_num": n,
                    "table_type": t['table_metadata']['table_type'],
                    "table_title": t['table_metadata'].get('table_title', ''),
                    "table_purpose": t['table_metadata'].get('table_purpose', ''),
                    "track_label": t['table_metadata'].get('track_label', ''),
                    "activity_count": len(t['activities']),
                    "column_count": len([
                        c for c in t['schedule_columns']
                        if not c.get('is_label_column')
                    ]),
                    "annotation_count": len(t.get('annotations', [])),
                    "property_hierarchy": extract_property_hierarchy(t)
                }
                for n, t in sorted(tables.items())
            ],
            "match_stats": act_consolidator.match_stats,
            "source_activity_count": total_src,
            "unified_activity_count": unified_count,
            "compression_percent": compression,
            "annotation_stats": annot_consolidator.get_stats()
        },
        "property_hierarchy": [p.to_dict() for p in prop_hierarchy],
        "review_queue": act_consolidator.review_queue,
        "unified_activities": [ua.to_dict() for ua in act_consolidator.unified_activities],
        "timeline_segments": {
            segment: [col.to_dict() for col in cols]
            for segment, cols in by_segment.items()
        },
        "schedule_matrix": matrix,
        "unified_annotations": [ua.to_dict() for ua in annot_consolidator.unified_annotations]
    }


# =============================================================================
# Pipeline Step Class
# =============================================================================

class ConsolidateStep(PipelineStepBase):
    """Consolidate resolved tables for a protocol."""

    step_name = "consolidate"

    def execute(self, data: dict) -> dict:
        """Execute consolidation for a protocol.
        
        Args:
            data: Must contain 'source' with protocol_id, collection
            
        Returns:
            Dict with input_files, output_file, and consolidation stats
        """
        source = data.get("source", {})
        protocol_id = source.get("protocol_id")
        collection = source.get("collection")

        if not protocol_id or not collection:
            self._log_error("Missing protocol_id or collection in source")
            return {"input_files": [], "output_file": None}

        # Find resolved files
        resolved_files = config.find_resolved_files(protocol_id, collection)

        if not resolved_files:
            self._log_error(
                "No resolved files found",
                {"protocol_id": protocol_id, "collection": collection}
            )
            return {"input_files": [], "output_file": None}

        self._analytics.record("resolved_files_found", len(resolved_files))

        # Run consolidation
        try:
            consolidated = consolidate_tables(protocol_id, resolved_files)
        except Exception as e:
            self._log_error(f"Consolidation failed: {e}")
            return {
                "input_files": [str(f) for f in resolved_files],
                "output_file": None,
                "error": str(e)
            }

        # Validate consolidated output
        validation = validate_consolidated(consolidated)
        if not validation.is_valid:
            for err in validation.errors:
                self._log_error(f"Validation: {err}")
            return {
                "input_files": [str(f) for f in resolved_files],
                "output_file": None,
                "validation_status": validation.status,
                "validation_errors": validation.errors
            }
        
        # Log warnings but continue
        for warn in validation.warnings:
            self._analytics.increment("validation_warnings")

        # Write output
        output_dir = config.get_consolidated_dir(protocol_id, collection)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{protocol_id}_consolidated.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False)

        # Extract stats for return
        meta = consolidated['consolidation_metadata']
        annot_stats = meta.get('annotation_stats', {})

        self._analytics.record("source_activities", meta['source_activity_count'])
        self._analytics.record("unified_activities", meta['unified_activity_count'])
        self._analytics.record("compression_percent", meta['compression_percent'])
        self._analytics.record("source_annotations", annot_stats.get('source_annotation_count', 0))
        self._analytics.record("unified_annotations", annot_stats.get('unified_annotation_count', 0))

        return {
            "input_files": [str(f) for f in resolved_files],
            "output_file": str(output_file),
            "output_dir": str(output_dir),
            "tables": len(meta['source_tables']),
            "source_activities": meta['source_activity_count'],
            "unified_activities": meta['unified_activity_count'],
            "compression_percent": meta['compression_percent'],
            "match_stats": meta['match_stats'],
            "review_queue_count": len(consolidated['review_queue']),
            "columns_by_segment": {
                seg: len(cols)
                for seg, cols in consolidated['timeline_segments'].items()
            },
            "schedule_cells": len(consolidated['schedule_matrix']),
            "annotation_stats": annot_stats,
            "validation_status": validation.status,
            "validation_warnings": validation.warnings
        }
