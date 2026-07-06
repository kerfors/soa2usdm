"""
Visualize Step

Generates HTML visualization from consolidated JSON files (Layer 3).

Features:
- Property Hierarchy Comparison with per-table comments shown
- Frozen columns for Activity and In columns
- Population-specific coloring for track segments
"""

import json
import html as html_lib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
from dataclasses import dataclass

from .base import PipelineStepBase
from . import config


# =============================================================================
# Color Scheme
# =============================================================================

LEVEL_COLORS = ['#375623', '#548235', '#70AD47', '#A9D08E', '#C6E0B4', '#E2EFDA']

POPULATION_PALETTE = [
    ('#28a745', '#d4edda', '#28a745'),  # Green
    ('#dc3545', '#f8d7da', '#dc3545'),  # Red
    ('#17a2b8', '#d1ecf1', '#17a2b8'),  # Teal
    ('#fd7e14', '#ffe5d0', '#fd7e14'),  # Orange
    ('#6f42c1', '#e2d9f3', '#6f42c1'),  # Purple
    ('#20c997', '#d2f4ea', '#20c997'),  # Cyan
]

COLORS = {
    'header': '#1F4788',
    'metadata': '#1F4788',
    'tables': '#5B9BD5',
    'properties': '#70AD47',
    'activities': '#C65911',
    'schedule': '#7030A0',
    'pop_default': '#6c757d',
    'cell_common': '#BDD7EE',
    'cell_data': '#BDD7EE',
    'match_exact': '#d4edda',
    'match_fuzzy': '#cce5ff',
    'match_cross': '#e1bee7',
    'match_single': '#f0f0f0',
    'qualifier_bg': '#f5f5f5',
    'qualifier_text': '#666',
}


class PopulationColorMapper:
    """Assigns colors to population tracks dynamically."""
    
    def __init__(self):
        self._track_to_index: Dict[str, int] = {}
        self._next_index = 0
    
    def get_colors(self, track: Optional[str]) -> tuple:
        if not track:
            return (COLORS['pop_default'], COLORS['cell_data'], '#333')
        if track not in self._track_to_index:
            self._track_to_index[track] = self._next_index
            self._next_index += 1
        idx = self._track_to_index[track] % len(POPULATION_PALETTE)
        return POPULATION_PALETTE[idx]
    
    def get_header_color(self, track: Optional[str]) -> str:
        return self.get_colors(track)[0]
    
    def get_cell_color(self, track: Optional[str]) -> str:
        return self.get_colors(track)[1]
    
    def get_text_color(self, track: Optional[str]) -> str:
        return self.get_colors(track)[2]
    
    def get_track_list(self) -> List[tuple]:
        return [(track, *self.get_colors(track)[:2]) 
                for track in sorted(self._track_to_index.keys(), 
                                   key=lambda t: self._track_to_index[t])]


# =============================================================================
# Navigation
# =============================================================================

@dataclass
class NavContext:
    """Navigation context for consolidated HTML pages."""
    protocol_id: str
    collection: str
    all_tables: list  # List of (table_num, html_filename)


def gen_navigation(nav) -> str:
    """Generate navigation bar HTML for consolidated view."""
    if nav is None:
        return ''
    
    # Breadcrumb: Collection > Protocol > Consolidated
    parts = [f'<a href="../../../index.html" class="nav-link">{nav.collection}</a>']
    parts.append('<span class="nav-sep">›</span>')
    parts.append(f'<span class="nav-current">{nav.protocol_id}</span>')
    parts.append('<span class="nav-sep">›</span>')
    parts.append('<span class="nav-current">Consolidated</span>')
    
    breadcrumb = ''.join(parts)
    
    # Links to individual table views
    table_links = ''
    if nav.all_tables:
        table_btns = []
        for tnum, fname in nav.all_tables:
            table_btns.append(f'<a href="../resolved/{fname}" class="nav-table-btn">T{tnum}</a>')
        table_links = f"""
        <div class="nav-tables">
            <span class="nav-tables-label">Tables:</span>
            <span class="nav-table-list">{' '.join(table_btns)}</span>
        </div>"""
    
    return f"""
    <nav class="navigation">
        <div class="nav-breadcrumb">{breadcrumb}</div>
        {table_links}
    </nav>"""


def get_level_color(level: int) -> str:
    idx = min(level - 1, len(LEVEL_COLORS) - 1)
    return LEVEL_COLORS[max(0, idx)]

def get_level_text_color(level: int) -> str:
    return 'white' if level <= 2 else '#333'

def get_match_color(status: str, table_count: int) -> str:
    if table_count == 1:
        return COLORS['match_single']
    if status == 'fuzzy_cross_parent':
        return COLORS['match_cross']
    if 'fuzzy' in status:
        return COLORS['match_fuzzy']
    return COLORS['match_exact']


# =============================================================================
# HTML Utilities
# =============================================================================

def esc(text) -> str:
    return html_lib.escape(str(text)) if text else ""

def format_value(value, trace: bool = False) -> str:
    cls = 'trace' if trace else 'data'
    if value is None:
        return f'<span class="{cls} null">null</span>'
    elif isinstance(value, bool):
        return f'<span class="{cls} bool">{str(value).lower()}</span>'
    elif isinstance(value, (int, float)):
        return f'<span class="{cls}">{value}</span>'
    elif isinstance(value, str):
        return f'<span class="{cls}">{esc(value)}</span>'
    elif isinstance(value, list):
        return f'<span class="{cls} arr">[{len(value)}]</span>'
    elif isinstance(value, dict):
        return f'<span class="{cls} obj">{{...}}</span>'
    return f'<span class="{cls}">{esc(str(value))}</span>'


# =============================================================================
# Component View Generators
# =============================================================================

def gen_metadata_component(data: dict) -> str:
    """Generate Consolidation Metadata component."""
    meta = data.get('consolidation_metadata', {})
    
    rows = []
    fields = ['consolidated_at', 'source_activity_count', 'unified_activity_count', 'compression_percent']
    for f in fields:
        if f in meta:
            rows.append(f'<tr><td class="field">{f}</td><td>{format_value(meta[f])}</td></tr>')
    
    stats = meta.get('match_stats', {})
    if stats:
        stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items() if v > 0)
        rows.append(f'<tr><td class="field">match_stats</td><td>{esc(stats_str)}</td></tr>')
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['metadata']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Consolidation Metadata</span>
            <span class="comp-desc">Process information</span>
        </div>
        <div class="comp-body">
            <table class="comp-table"><tbody>{''.join(rows)}</tbody></table>
        </div>
    </div>'''


def gen_tables_component(data: dict, pop_colors: PopulationColorMapper) -> str:
    """Generate Source Tables component."""
    tables = data.get('consolidation_metadata', {}).get('source_tables', [])
    
    rows = []
    for t in tables:
        tnum = t.get('table_num', '')
        ttype = t.get('table_type', '')
        track = t.get('track_label', '')
        
        # Color the track label with population colors
        if track:
            bg_color = pop_colors.get_header_color(track)
            track_display = f'<span class="track-label" style="background: {bg_color}; color: white;">{esc(track)}</span>'
        else:
            track_display = ''
        
        title = t.get('table_title', '')
        purpose = t.get('table_purpose', '')
        title_purpose = f"{esc(title)}"
        if purpose:
            title_purpose += f"<br/><span class='purpose-text'>{esc(purpose)}</span>"
        
        rows.append(f'''<tr>
            <td class="id">T{tnum}</td>
            <td class="type">{ttype}</td>
            <td>{track_display}</td>
            <td class="title-full">{title_purpose}</td>
            <td class="trace">{t.get('activity_count', '')}</td>
            <td class="trace">{t.get('column_count', '')}</td>
            <td class="trace">{len(t.get('property_hierarchy', []))}</td>
        </tr>''')
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['tables']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Source Tables</span>
            <span class="comp-desc">{len(tables)} tables</span>
        </div>
        <div class="comp-body">
            <table class="comp-table">
                <thead><tr>
                    <th>table</th><th>type</th><th>track</th><th>title / purpose</th><th>acts</th><th>cols</th><th>props</th>
                </tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </div>'''


def gen_property_comparison_component(data: dict) -> str:
    """Generate Property Hierarchy Comparison with per-table comments shown.
    
    Only compares main timeline tables (main_soa, continuation, subsidiary).
    Track, domain, and reference tables have different structures by design.
    Separates hierarchical properties from column qualifiers.
    """
    tables = data.get('consolidation_metadata', {}).get('source_tables', [])
    
    # Only compare main timeline tables - track/domain/reference have different structures by design
    tables = [t for t in tables if t.get('table_type') in ('main_soa', 'continuation', 'subsidiary')]
    
    if len(tables) < 2:
        return ''
    
    # Find max hierarchical level (excluding None/qualifiers)
    max_level = 0
    has_qualifiers = False
    for t in tables:
        props = t.get('property_hierarchy', [])
        for p in props:
            level = p.get('hierarchical_level')
            if level is not None:
                max_level = max(max_level, level)
            else:
                has_qualifiers = True
    
    if max_level == 0 and not has_qualifiers:
        return ''
    
    header_cells = '<th>Level</th>'
    for t in tables:
        tnum = t.get('table_num', '')
        ttype = t.get('table_type', '')
        track = t.get('track_label', '')
        label = f"T{tnum}"
        if track:
            label += f"<br/><span class='track-small'>{esc(track)}</span>"
        header_cells += f'<th class="table-col" title="{esc(ttype)}">{label}</th>'
    header_cells += '<th class="conclusion-col">Conclusion</th>'
    
    rows = []
    
    # Hierarchical levels first
    for level in range(1, max_level + 1):
        bg_color = get_level_color(level)
        text_color = get_level_text_color(level)
        
        row_cells = f'<td class="level-cell" style="background: {bg_color}; color: {text_color};">L{level}</td>'
        
        level_props = []
        for t in tables:
            props = t.get('property_hierarchy', [])
            prop_at_level = None
            for p in props:
                if p.get('hierarchical_level') == level:
                    prop_at_level = p
                    break
            level_props.append(prop_at_level)
            
            if prop_at_level:
                pname = prop_at_level.get('property_name', '')
                ptype = prop_at_level.get('property_type', '')
                pcomment = prop_at_level.get('property_comment', '')
                
                comment_display = pcomment  # Full comment, no truncation
                
                cell_content = f'''<div class="prop-cell-content">
                    <div class="prop-name">{esc(pname) if pname else '<em>(implicit)</em>'}</div>
                    <div class="prop-type">[{ptype}]</div>
                    <div class="prop-comment">{esc(comment_display)}</div>
                </div>'''
                row_cells += f'<td class="prop-data" style="background: {bg_color}; color: {text_color};" title="{esc(pcomment)}">{cell_content}</td>'
            else:
                row_cells += '<td class="prop-empty">—</td>'
        
        present = [p for p in level_props if p is not None]
        if not present:
            conclusion = '<span class="conc-empty">—</span>'
        elif len(present) == len(tables):
            types = set(p.get('property_type', '') for p in present)
            names = set(p.get('property_name', '') for p in present)
            if len(types) == 1 and len(names) == 1:
                conclusion = '<span class="conc-match">✓ Identical</span>'
            elif len(types) == 1:
                conclusion = '<span class="conc-similar">≈ Same type</span>'
            else:
                conclusion = '<span class="conc-differ">≠ Differs</span>'
        else:
            conclusion = f'<span class="conc-partial">{len(present)}/{len(tables)} tables</span>'
        
        row_cells += f'<td class="conclusion-cell">{conclusion}</td>'
        rows.append(f'<tr>{row_cells}</tr>')
    
    # Column Qualifiers section (properties with null hierarchical_level)
    if has_qualifiers:
        # Collect all unique qualifier types across tables
        qualifier_types = set()
        for t in tables:
            props = t.get('property_hierarchy', [])
            for p in props:
                if p.get('hierarchical_level') is None:
                    qualifier_types.add(p.get('property_type', 'other'))
        
        if qualifier_types:
            # Section divider
            rows.append(f'<tr><td colspan="{len(tables) + 2}" style="background: #e9ecef; padding: 6px 10px; font-size: 10px; font-weight: 600; color: #666;">Column Qualifiers</td></tr>')
            
            for qtype in sorted(qualifier_types):
                row_cells = f'<td class="level-cell" style="background: {COLORS["qualifier_bg"]}; color: {COLORS["qualifier_text"]};">—</td>'
                
                type_props = []
                for t in tables:
                    props = t.get('property_hierarchy', [])
                    prop_of_type = None
                    for p in props:
                        if p.get('hierarchical_level') is None and p.get('property_type') == qtype:
                            prop_of_type = p
                            break
                    type_props.append(prop_of_type)
                    
                    if prop_of_type:
                        pname = prop_of_type.get('property_name', '')
                        pcomment = prop_of_type.get('property_comment', '')
                        
                        cell_content = f'''<div class="prop-cell-content">
                            <div class="prop-name">{esc(pname) if pname else '<em>(implicit)</em>'}</div>
                            <div class="prop-type">[{qtype}]</div>
                            <div class="prop-comment" style="color: #555;">{esc(pcomment)}</div>
                        </div>'''
                        row_cells += f'<td class="prop-data" style="background: {COLORS["qualifier_bg"]}; color: {COLORS["qualifier_text"]};" title="{esc(pcomment)}">{cell_content}</td>'
                    else:
                        row_cells += '<td class="prop-empty">—</td>'
                
                present = [p for p in type_props if p is not None]
                if not present:
                    conclusion = '<span class="conc-empty">—</span>'
                elif len(present) == len(tables):
                    conclusion = '<span class="conc-match">✓ All tables</span>'
                else:
                    conclusion = f'<span class="conc-partial">{len(present)}/{len(tables)} tables</span>'
                
                row_cells += f'<td class="conclusion-cell">{conclusion}</td>'
                rows.append(f'<tr>{row_cells}</tr>')
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['properties']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Property Hierarchy Comparison</span>
            <span class="comp-desc">{len(tables)} main timeline tables, {max_level} levels max</span>
        </div>
        <div class="comp-body">
            <p class="comp-note">Compares main timeline tables only (main_soa, continuation, subsidiary). Track, domain, and reference tables excluded — different structure by design.</p>
            <table class="comp-table prop-comparison">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </div>'''


def gen_activities_component(data: dict) -> str:
    """Generate Unified Activities component."""
    activities = data.get('unified_activities', [])
    
    rows = []
    for ua in activities:
        bg = get_match_color(ua.get('match_status', 'new'), ua.get('table_count', 1))
        source_refs = ua.get('source_refs', [])
        tables = ', '.join(f"T{sr['table_num']}" for sr in source_refs)
        
        name_variations = ua.get('name_variations', [])
        if name_variations and len(set(name_variations)) > 1:
            unique_names = list(dict.fromkeys(name_variations))
            name_display = f"<strong>{esc(unique_names[0])}</strong>"
            if len(unique_names) > 1:
                name_display += f"<br/><span class='variations'>≈ {'; '.join(esc(n) for n in unique_names[1:])}</span>"
        else:
            name_display = esc(ua.get('activity_name', ''))
        
        rows.append(f'''<tr style="background: {bg};">
            <td class="id">{ua.get('xact_id', '')}</td>
            <td class="text-full">{name_display}</td>
            <td class="trace">{esc(ua.get('parent_name', '')[:40])}</td>
            <td class="type">{ua.get('match_status', '')}</td>
            <td class="trace">{ua.get('table_count', 1)}</td>
            <td class="trace">{tables}</td>
            <td class="bool">{str(ua.get('is_section_header', False)).lower()}</td>
        </tr>''')
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['activities']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Unified Activities</span>
            <span class="comp-desc">{len(activities)} activities</span>
        </div>
        <div class="comp-body">
            <table class="comp-table">
                <thead><tr>
                    <th>xact_id</th><th>activity_name (variations)</th><th>parent</th><th>match</th><th>#</th><th>tables</th><th>header</th>
                </tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </div>'''


def gen_annotations_component(data: dict) -> str:
    """Generate Unified Annotations component."""
    annotations = data.get('unified_annotations', [])
    meta = data.get('consolidation_metadata', {})
    annot_stats = meta.get('annotation_stats', {})
    
    if not annotations:
        return ''
    
    # Group annotations by type
    by_type = defaultdict(list)
    for ua in annotations:
        by_type[ua.get('annotation_type', 'footnote')].append(ua)
    
    # Build activity lookup for displaying referenced activity names
    act_lookup = {}
    for ua in data.get('unified_activities', []):
        act_lookup[ua.get('xact_id', '')] = ua.get('activity_name', '')
    
    # Build column lookup for displaying referenced column labels
    col_lookup = {}
    for segment, cols in data.get('timeline_segments', {}).items():
        for col in cols:
            xcol_id = col.get('xcol_id', '')
            label = extract_column_identifier(col)
            if not label:
                label = col.get('composite_label', '')[:20]
            col_lookup[xcol_id] = label
    
    sections = []
    type_order = ['footnote', 'abbreviation', 'legend', 'source_note', 'continuation_note']
    type_colors = {
        'footnote': '#5a6268',
        'abbreviation': '#2E75B6',
        'legend': '#538135',
        'source_note': '#BF8F00',
        'continuation_note': '#C65911'
    }
    
    for atype in type_order:
        type_annots = by_type.get(atype, [])
        if not type_annots:
            continue
        
        rows = []
        for ua in type_annots:
            xannot_id = ua.get('xannot_id', '')
            display_markers = ua.get('display_markers', '')
            occ_count = ua.get('occurrence_count', 1)
            text = ua.get('annotation_text', '')
            
            # Truncate long text for display
            text_display = text if len(text) <= 120 else text[:117] + '...'
            
            # Determine scope and build references display
            ref_xacts = ua.get('referenced_xacts', [])
            ref_xcols = ua.get('referenced_xcols', [])
            cell_refs = ua.get('cell_references', [])
            
            scope_parts = []
            
            if ref_xacts:
                act_names = [act_lookup.get(xact, xact) for xact in ref_xacts[:3]]
                act_display = ' | '.join(act_names)
                if len(ref_xacts) > 3:
                    act_display += f' (+{len(ref_xacts) - 3})'
                scope_parts.append(f'<span class="scope-acts" title="Activities">{esc(act_display)}</span>')
            
            if ref_xcols and not ref_xacts:
                # Property-level: show column labels (timeline scope)
                col_labels = [col_lookup.get(xcol, xcol) for xcol in ref_xcols[:5]]
                col_display = ' | '.join(col_labels)
                if len(ref_xcols) > 5:
                    col_display += f' (+{len(ref_xcols) - 5})'
                scope_parts.append(f'<span class="scope-cols" title="Timeline columns: {len(ref_xcols)} total">{esc(col_display)}</span>')
            
            if cell_refs:
                scope_parts.append(f'<span class="scope-cells" title="Specific cells">{len(cell_refs)} cells</span>')
            
            if not scope_parts:
                refs_display = '<span class="scope-table" title="Table-level">table</span>'
            else:
                refs_display = ' '.join(scope_parts)
            
            # Highlight: green for multi-table, light purple for property-level
            if occ_count > 1:
                bg = '#e8f4e8'  # green tint
            elif ref_xcols and not ref_xacts:
                bg = '#f3e8f8'  # purple tint - property/timeline annotation
            else:
                bg = '#fff'
            
            rows.append(f'''<tr style="background: {bg};">
                <td class="id">{xannot_id}</td>
                <td class="trace">{esc(display_markers)}</td>
                <td class="trace">{occ_count}</td>
                <td class="text-full" title="{esc(text)}">{esc(text_display)}</td>
                <td class="trace">{refs_display}</td>
            </tr>''')
        
        color = type_colors.get(atype, '#666')
        sections.append(f'''
            <div class="annot-section">
                <div class="annot-type-header" style="background: {color};">{atype.replace('_', ' ').title()} ({len(type_annots)})</div>
                <table class="comp-table">
                    <thead><tr>
                        <th>xannot_id</th><th>markers</th><th>#</th><th>text</th><th>scope</th>
                    </tr></thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
        ''')
    
    # Stats summary
    src_count = annot_stats.get('source_annotation_count', len(annotations))
    unified_count = annot_stats.get('unified_annotation_count', len(annotations))
    dedup_pct = annot_stats.get('deduplication_percent', 0)
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: #6c757d;" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Unified Annotations</span>
            <span class="comp-desc">{unified_count} annotations ({dedup_pct}% dedup from {src_count})</span>
        </div>
        <div class="comp-body">
            {''.join(sections)}
        </div>
    </div>'''


# =============================================================================
# Schedule Grid
# =============================================================================

FROZEN_COL1_WIDTH = 340
FROZEN_COL2_WIDTH = 60


def extract_column_identifier(column: dict) -> str:
    """Extract the property value that uniquely identifies this column."""
    pvs = column.get('property_values', [])
    if not pvs:
        return ''
    for ptype in ['visit', 'cycle', 'study_day']:
        for pv in pvs:
            if pv.get('property_type') == ptype and pv.get('value'):
                return pv.get('value')
    for pv in sorted(pvs, key=lambda x: x.get('level') or 99):
        val = pv.get('value', '')
        ptype = pv.get('property_type', '')
        if ptype == 'epoch' and not val:
            continue
        if val:
            return val
    return ''


def get_cell_population_info(data: dict) -> tuple:
    """Build lookups for population comparison."""
    segments = data.get('timeline_segments', {})
    track_cols = segments.get('track', [])
    matrix = data.get('schedule_matrix', [])
    
    if not track_cols:
        return {}, {}
    
    col_info = {}
    col_tp_map = {}
    for c in track_cols:
        col_id = extract_column_identifier(c)
        track = c.get('population_track', '')
        col_info[c['xcol_id']] = (col_id, track)
        col_tp_map[c['xcol_id']] = col_id
    
    cell_pops: Dict[tuple, Dict[str, str]] = defaultdict(dict)
    
    for m in matrix:
        xcol = m.get('xcol_id', '')
        if xcol in col_info:
            col_id, track = col_info[xcol]
            xact = m.get('xact_id', '')
            value = m.get('consolidated_value', '')
            if value and track:
                cell_pops[(xact, col_id)][track] = value
    
    return dict(cell_pops), col_tp_map


def gen_schedule_grid(data: dict, segment: str, columns: List[dict], pop_colors: PopulationColorMapper) -> str:
    """Generate schedule grid for a segment."""
    if not columns:
        return ""
    
    activities = data.get('unified_activities', [])
    matrix = {(m['xact_id'], m['xcol_id']): m['consolidated_value'] 
              for m in data.get('schedule_matrix', [])}
    
    # For track/domain/subsidiary segments, derive property hierarchy from columns
    # These segments may have different structure than main timeline
    if segment in ('track', 'domain', 'subsidiary'):
        props_from_cols = {}
        for col in columns:
            for pv in col.get('property_values', []):
                level = pv.get('level')
                prop_type = pv.get('property_type', '')
                # Key: int for hierarchical, str for qualifiers (level=None)
                if level is not None:
                    key = level
                else:
                    key = f"q_{prop_type}"
                
                if key not in props_from_cols:
                    props_from_cols[key] = {
                        'hierarchical_level': level,
                        'property_name': pv.get('property_name', ''),
                        'property_type': prop_type
                    }
        
        # Sort: hierarchical (int keys) first, qualifiers (str keys) after
        hier_keys = sorted([k for k in props_from_cols if isinstance(k, int)])
        qual_keys = sorted([k for k in props_from_cols if isinstance(k, str)])
        props = [props_from_cols[k] for k in hier_keys + qual_keys]
    else:
        props = data.get('property_hierarchy', [])
    
    cell_pops, col_tp_map = get_cell_population_info(data) if segment == 'track' else ({}, {})
    
    all_tracks = set()
    if segment == 'track':
        all_tracks = {c.get('population_track', '') for c in columns if c.get('population_track')}
    
    rows = []
    
    if segment == 'main':
        title = f"Main Schedule ({len(columns)} columns)"
        title_bg = COLORS['header']
    elif segment == 'domain':
        title = f"Domain Schedule ({len(columns)} columns)"
        title_bg = '#548235'
    elif segment == 'track':
        tracks = sorted(all_tracks)
        title = f"Track Timelines: {', '.join(tracks)} ({len(columns)} columns)"
        title_bg = '#7030A0'
    elif segment == 'subsidiary':
        title = f"Subsidiary Schedule ({len(columns)} columns)"
        title_bg = '#17a2b8'
    
    # Detect boundaries between tables/tracks for vertical dividers
    boundaries = set()
    prev_key = None
    for i, col in enumerate(columns):
        if segment == 'track':
            key = col.get('population_track', '')
        else:
            src = col.get('source_columns', [{}])[0]
            key = src.get('table_num', '')
        if prev_key is not None and key != prev_key:
            boundaries.add(i)
        prev_key = key
    
    def border_class(idx):
        return ' table-border' if idx in boundaries else ''
    
    rows.append(f'<tr><th class="frozen-col1 activity-header">Activity</th><th class="frozen-col2">In</th>')
    for i, col in enumerate(columns):
        src = col.get('source_columns', [{}])[0]
        tnum = src.get('table_num', '')
        rows.append(f'<th class="{border_class(i).strip()}" style="background: {COLORS["header"]}; color: white; font-size: 9px;">T{tnum}</th>')
    rows.append('</tr>')
    
    if segment == 'track':
        rows.append('<tr><th class="frozen-col1"></th><th class="frozen-col2"></th>')
        for i, col in enumerate(columns):
            track = col.get('population_track', '')
            bg = pop_colors.get_header_color(track)
            rows.append(f'<th class="{border_class(i).strip()}" style="background: {bg}; color: white; font-size: 8px; white-space: normal; word-wrap: break-word; max-width: 80px;">{esc(track)}</th>')
        rows.append('</tr>')
    
    # Separate hierarchical properties from qualifiers
    hierarchical_props = [p for p in props if p.get('hierarchical_level') is not None]
    qualifier_props = [p for p in props if p.get('hierarchical_level') is None]
    
    # Render hierarchical properties
    for prop in hierarchical_props:
        level = prop.get('hierarchical_level')
        bg = get_level_color(level)
        text_color = get_level_text_color(level)
        prop_name = prop.get('property_name', '')
        prop_type = prop.get('property_type', '')
        
        rows.append(f'<tr><th class="frozen-col1" style="background: {bg}; color: {text_color}; text-align: left; font-size: 9px;">{esc(prop_name)}<br/><span style="font-size: 8px; opacity: 0.8;">[{prop_type}] L{level}</span></th>')
        rows.append(f'<th class="frozen-col2" style="background: {bg};"></th>')
        
        for i, col in enumerate(columns):
            value = ""
            for pv in col.get('property_values', []):
                if pv.get('level') == level:
                    value = pv.get('value', '')
                    break
            rows.append(f'<td class="{border_class(i).strip()}" style="background: {bg}; color: {text_color}; text-align: center; font-size: 9px;">{esc(value)}</td>')
        rows.append('</tr>')
    
    # Render qualifier properties with neutral styling
    for prop in qualifier_props:
        prop_name = prop.get('property_name', '')
        prop_type = prop.get('property_type', '')
        bg = COLORS['qualifier_bg']
        text_color = COLORS['qualifier_text']
        
        rows.append(f'<tr><th class="frozen-col1" style="background: {bg}; color: {text_color}; text-align: left; font-size: 9px;">{esc(prop_name)}<br/><span style="font-size: 8px; opacity: 0.8;">[{prop_type}]</span></th>')
        rows.append(f'<th class="frozen-col2" style="background: {bg};"></th>')
        
        for i, col in enumerate(columns):
            value = ""
            for pv in col.get('property_values', []):
                if pv.get('property_type') == prop_type and pv.get('level') is None:
                    value = pv.get('value', '')
                    break
            rows.append(f'<td class="{border_class(i).strip()}" style="background: {bg}; color: {text_color}; text-align: center; font-size: 9px;">{esc(value)}</td>')
        rows.append('</tr>')
    
    # Get table numbers that contribute columns to this segment
    segment_tables = {col.get('source_columns', [{}])[0].get('table_num') 
                      for col in columns}
    
    for ua in activities:
        xact_id = ua['xact_id']
        
        has_data = any(matrix.get((xact_id, col['xcol_id']), '') for col in columns)
        from_segment_table = any(sr['table_num'] in segment_tables 
                                 for sr in ua.get('source_refs', []))
        if not has_data and not ua.get('is_section_header', False) and not from_segment_table:
            continue
        
        match_bg = get_match_color(ua.get('match_status', 'new'), ua.get('table_count', 1))
        is_header = ua.get('is_section_header', False)
        
        name_cls = "section-header" if is_header else ""
        if ua.get('parent_name'):
            name_cls += " child"
        
        tables = ','.join(f"T{sr['table_num']}" for sr in ua.get('source_refs', []))
        
        rows.append(f'<tr><td class="frozen-col1 activity-name {name_cls}" style="background: {match_bg};" title="{esc(ua.get("qualified_key", ""))}">{esc(ua.get("activity_name", ""))}</td>')
        rows.append(f'<td class="frozen-col2" style="background: {match_bg}; font-size: 8px;">{tables}</td>')
        
        for i, col in enumerate(columns):
            xcol_id = col['xcol_id']
            value = matrix.get((xact_id, xcol_id), '')
            bc = border_class(i)
            
            if value:
                if segment == 'track' and len(all_tracks) > 1:
                    col_id = col_tp_map.get(xcol_id, '')
                    track = col.get('population_track', '')
                    pop_data = cell_pops.get((xact_id, col_id), {})
                    tracks_with_data = set(pop_data.keys())
                    
                    if len(tracks_with_data) >= len(all_tracks):
                        cell_bg = COLORS['cell_common']
                        text_color = '#1F4788'
                    else:
                        cell_bg = pop_colors.get_cell_color(track)
                        text_color = pop_colors.get_text_color(track)
                else:
                    cell_bg = COLORS['cell_data']
                    text_color = COLORS['header']
                
                rows.append(f'<td class="{bc.strip()}" style="background: {cell_bg}; color: {text_color}; font-weight: bold; text-align: center;">{esc(value)}</td>')
            else:
                rows.append(f'<td class="{bc.strip()}"></td>')
        rows.append('</tr>')
    
    return f'''
    <div class="section collapsible-section">
        <div class="section-title" style="background: {title_bg};" onclick="toggleGrid(this)">
            <span class="toggle-icon">▼</span> {title}
        </div>
        <div class="grid-container">
            <table class="grid-table">{''.join(rows)}</table>
        </div>
    </div>'''


# =============================================================================
# Full HTML Generator
# =============================================================================

def generate_consolidated_html(data: dict, nav=None) -> str:
    """Generate complete consolidated HTML."""
    protocol_id = data.get('protocol_id', 'Unknown')
    meta = data.get('consolidation_metadata', {})
    
    num_tables = len(meta.get('source_tables', []))
    num_activities = meta.get('unified_activity_count', 0)
    compression = meta.get('compression_percent', 0)
    
    segments = data.get('timeline_segments', {})
    total_cols = sum(len(cols) for cols in segments.values())
    
    # Initialize PopulationColorMapper from source_tables track_labels AND track columns
    # This ensures consistent colors across Source Tables display and schedule grids
    pop_colors = PopulationColorMapper()
    
    # Register tracks from source_tables first (so they get colors in display order)
    for t in meta.get('source_tables', []):
        track = t.get('track_label', '')
        if track:
            pop_colors.get_colors(track)
    
    # Also register from track columns (may have additional tracks)
    track_cols = segments.get('track', [])
    for col in track_cols:
        track = col.get('population_track', '')
        if track:
            pop_colors.get_colors(track)
    
    css = f"""
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5; padding: 20px; font-size: 11px;
            max-width: 1800px; margin: 0 auto;
        }}
        
        .navigation {{
            background: white;
            border-radius: 8px;
            padding: 10px 20px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .nav-breadcrumb {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }}
        .nav-link {{
            color: #1F4788;
            text-decoration: none;
        }}
        .nav-link:hover {{
            text-decoration: underline;
        }}
        .nav-sep {{
            color: #999;
        }}
        .nav-current {{
            font-weight: 600;
            color: #333;
        }}
        .nav-tables {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .nav-tables-label {{
            font-size: 11px;
            color: #666;
        }}
        .nav-table-list {{
            display: flex;
            gap: 4px;
        }}
        .nav-table-btn {{
            padding: 4px 8px;
            background: #f0f0f0;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            font-size: 11px;
        }}
        .nav-table-btn:hover {{
            background: #e0e0e0;
        }}
        
        .header {{
            background: linear-gradient(135deg, {COLORS['header']} 0%, #2E5EA8 100%);
            color: white; padding: 25px 30px; border-radius: 8px; margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 22px; margin-bottom: 8px; }}
        .header .sub {{ font-size: 12px; opacity: 0.9; margin-bottom: 4px; }}
        .header .meta {{ font-size: 11px; opacity: 0.8; }}
        
        .toolbar {{
            background: white; border-radius: 8px; padding: 10px 20px;
            margin-bottom: 15px; display: flex; gap: 10px;
        }}
        .toolbar button {{
            padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px;
            background: #f5f5f5; cursor: pointer; font-size: 11px;
        }}
        .toolbar button:hover {{ background: #e0e0e0; }}
        
        .comp {{
            background: white; border-radius: 8px; margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;
        }}
        .comp-header {{
            color: white; padding: 12px 20px; display: flex;
            justify-content: space-between; align-items: center;
            cursor: pointer; user-select: none;
        }}
        .comp-header:hover {{ filter: brightness(1.1); }}
        .comp-title {{ font-weight: bold; font-size: 14px; }}
        .comp-desc {{ font-size: 11px; opacity: 0.9; }}
        .toggle-icon {{ display: inline-block; transition: transform 0.2s; margin-right: 8px; }}
        .comp.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
        .comp-body {{ overflow: hidden; transition: max-height 0.3s; padding: 0; }}
        .comp.collapsed .comp-body {{ max-height: 0 !important; }}
        .comp-note {{ padding: 12px 15px; color: #444; font-size: 11px; border-bottom: 1px solid #eee; background: #f9f9f9; }}
        
        .comp-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .comp-table th {{
            background: #f5f5f5; padding: 8px 10px; text-align: left;
            font-weight: 600; border-bottom: 2px solid #ddd; white-space: nowrap;
        }}
        .comp-table td {{
            padding: 6px 10px; border-bottom: 1px solid #eee;
            vertical-align: top; word-wrap: break-word;
        }}
        .comp-table tr:hover {{ background: #fafafa; }}
        
        .prop-comparison th.table-col {{ text-align: center; min-width: 320px; }}
        .prop-comparison .track-small {{ font-size: 9px; font-weight: normal; color: #666; }}
        .prop-comparison .level-cell {{ font-weight: bold; text-align: center; width: 60px; font-size: 11px; }}
        .prop-comparison .prop-data {{ text-align: left; vertical-align: top; padding: 10px 12px !important; }}
        .prop-comparison .prop-empty {{ text-align: center; color: #ccc; background: #fafafa; font-size: 11px; }}
        .prop-cell-content {{ }}
        .prop-cell-content .prop-name {{ font-weight: bold; font-size: 11px; margin-bottom: 2px; }}
        .prop-cell-content .prop-type {{ font-size: 10px; opacity: 0.85; margin-bottom: 6px; }}
        .prop-cell-content .prop-comment {{ font-size: 10px; opacity: 0.9; font-style: normal; line-height: 1.4; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 6px; margin-top: 4px; }}
        
        .title-full {{ max-width: 600px; }}
        .purpose-text {{ font-size: 9px; color: #666; font-style: italic; }}
        
        .conclusion-col {{ min-width: 120px; text-align: center; }}
        .conclusion-cell {{ text-align: center; font-size: 11px; background: #fafafa; padding: 10px !important; }}
        .conc-match {{ color: #28a745; font-weight: bold; }}
        .conc-similar {{ color: #17a2b8; font-weight: bold; }}
        .conc-differ {{ color: #dc3545; font-weight: bold; }}
        .conc-partial {{ color: #fd7e14; font-weight: bold; }}
        .conc-empty {{ color: #ccc; }}
        
        .id {{ font-family: 'SF Mono', Monaco, monospace; font-size: 10px; color: {COLORS['header']}; font-weight: bold; }}
        .field {{ font-weight: 600; color: #333; white-space: nowrap; }}
        .type {{ font-size: 10px; color: #666; }}
        .trace {{ color: #999; font-size: 10px; }}
        .bool {{ font-size: 10px; }}
        .text-full {{ max-width: 400px; }}
        .variations {{ font-size: 9px; color: #666; font-style: italic; }}
        .track-label {{ padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: 500; }}
        .data.null {{ color: #999; font-style: italic; }}
        .data.bool {{ color: #0066cc; }}
        
        .annot-section {{ margin-bottom: 15px; }}
        .annot-type-header {{
            color: white; padding: 8px 15px; font-size: 12px; font-weight: bold;
            border-radius: 4px 4px 0 0;
        }}
        .annot-section .comp-table {{ border-radius: 0 0 4px 4px; }}
        
        .scope-acts {{ color: {COLORS['activities']}; }}
        .scope-cols {{ color: #17a2b8; font-style: italic; }}
        .scope-cells {{ color: #538135; }}
        .scope-table {{ color: #999; font-style: italic; }}
        
        .section {{
            background: white; border-radius: 8px; margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;
        }}
        .section-title {{
            color: white; padding: 12px 20px; font-size: 13px; font-weight: bold;
            cursor: pointer; user-select: none;
        }}
        .section-title:hover {{ filter: brightness(1.1); }}
        .section-title .toggle-icon {{ 
            display: inline-block; transition: transform 0.2s; margin-right: 8px; 
        }}
        .collapsible-section.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
        .collapsible-section.collapsed .grid-container {{ display: none; }}
        .grid-container {{ overflow-x: auto; padding: 10px; }}
        
        .table-border {{ border-left: 3px solid #333 !important; }}
        
        .grid-table {{ border-collapse: separate; border-spacing: 0; font-size: 10px; }}
        .grid-table th, .grid-table td {{ border: 1px solid #ddd; padding: 3px 5px; }}
        .grid-table th {{ background: #f0f0f0; font-weight: bold; font-size: 9px; }}
        .grid-table th.activity-header {{ text-align: left; }}
        
        .frozen-col1 {{
            position: sticky;
            left: 0;
            z-index: 2;
            min-width: {FROZEN_COL1_WIDTH}px;
            max-width: {FROZEN_COL1_WIDTH}px;
            background: #f0f0f0;
            border-right: 2px solid #999 !important;
        }}
        .frozen-col2 {{
            position: sticky;
            left: {FROZEN_COL1_WIDTH}px;
            z-index: 2;
            min-width: {FROZEN_COL2_WIDTH}px;
            max-width: {FROZEN_COL2_WIDTH}px;
            background: #f0f0f0;
            border-right: 2px solid #999 !important;
            text-align: center;
        }}
        .grid-table th.frozen-col1,
        .grid-table th.frozen-col2 {{
            z-index: 3;
        }}
        .frozen-col2::after {{
            content: '';
            position: absolute;
            top: 0;
            right: -6px;
            bottom: 0;
            width: 6px;
            background: linear-gradient(to right, rgba(0,0,0,0.1), transparent);
            pointer-events: none;
        }}
        
        .activity-name {{ text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .activity-name.section-header {{ font-weight: bold; }}
        .activity-name.child {{ padding-left: 15px; }}
        
        .legend {{
            background: white; border-radius: 8px; padding: 12px 20px;
            margin-bottom: 20px; display: flex; gap: 15px; flex-wrap: wrap; font-size: 10px;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .legend-color {{ width: 16px; height: 12px; border-radius: 2px; border: 1px solid #ddd; }}
        .legend-section {{ font-weight: bold; color: #666; margin-left: 10px; }}
    """
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{protocol_id} - Consolidated Schedule</title>
    <style>{css}</style>
</head>
<body>
    {gen_navigation(nav)}
    <div class="header">
        <h1>{protocol_id} - Consolidated Schedule of Activities</h1>
        <div class="sub">study-schedule-consolidated v1.0 | Layer 3</div>
        <div class="meta">{num_tables} tables | {num_activities} activities ({compression}% compression) | {total_cols} columns</div>
    </div>
    
    <div class="toolbar">
        <button onclick="expandAll()">▼ Expand All</button>
        <button onclick="collapseAll()">▶ Collapse All</button>
    </div>
    
    <div class="legend">
        <span class="legend-section">Activities:</span>
        <div class="legend-item"><div class="legend-color" style="background:{COLORS['match_exact']};"></div>Multi-table exact</div>
        <div class="legend-item"><div class="legend-color" style="background:{COLORS['match_fuzzy']};"></div>Multi-table fuzzy</div>
        <div class="legend-item"><div class="legend-color" style="background:{COLORS['match_cross']};"></div>Cross-parent</div>
        <div class="legend-item"><div class="legend-color" style="background:{COLORS['match_single']};"></div>Single table</div>
        <span class="legend-section">|</span>
        <span class="legend-section">Cells:</span>
        <div class="legend-item"><div class="legend-color" style="background:{COLORS['cell_common']};"></div>Common</div>
        {" ".join(f'<div class="legend-item"><div class="legend-color" style="background:{cell_col}; border-color:{hdr_col};"></div>{esc(track[:20])} only</div>' for track, hdr_col, cell_col in pop_colors.get_track_list())}
    </div>
    
    {gen_metadata_component(data)}
    {gen_tables_component(data, pop_colors)}
    {gen_property_comparison_component(data)}
    {gen_activities_component(data)}
    {gen_annotations_component(data)}
'''
    
    for segment in ['main', 'domain', 'track', 'subsidiary']:
        cols = segments.get(segment, [])
        if cols:
            html += gen_schedule_grid(data, segment, cols, pop_colors)
    
    html += '''
    <script>
        function toggleSection(header) {
            const comp = header.closest('.comp');
            comp.classList.toggle('collapsed');
        }
        function toggleGrid(title) {
            const section = title.closest('.collapsible-section');
            section.classList.toggle('collapsed');
        }
        function expandAll() {
            document.querySelectorAll('.comp, .collapsible-section').forEach(c => c.classList.remove('collapsed'));
        }
        function collapseAll() {
            document.querySelectorAll('.comp, .collapsible-section').forEach(c => c.classList.add('collapsed'));
        }
        // Start with component sections collapsed, grids expanded
        document.querySelectorAll('.comp').forEach(c => c.classList.add('collapsed'));
    </script>
</body>
</html>'''
    
    return html


# =============================================================================
# Pipeline Step Class
# =============================================================================

class VisualizeStep(PipelineStepBase):
    """Generate HTML visualization from consolidated JSON."""
    
    step_name = "visualize"
    
    def execute(self, data: dict) -> dict:
        """Execute visualization for consolidated file.
        
        Args:
            data: Must contain 'source' with protocol_id, collection
                  Optionally 'consolidate' with output_file from consolidate step
        """
        source = data.get("source", {})
        protocol_id = source.get("protocol_id")
        collection = source.get("collection")
        
        if not protocol_id or not collection:
            self._log_error("Missing protocol_id or collection in source")
            return {"output_file": None}
        
        # Find consolidated file
        consolidated_dir = config.get_consolidated_dir(protocol_id, collection)
        consolidated_file = consolidated_dir / f"{protocol_id}_consolidated.json"
        
        if not consolidated_file.exists():
            self._log_error("No consolidated file found", {"expected": str(consolidated_file)})
            return {"output_file": None}
        
        try:
            with open(consolidated_file) as f:
                consolidated_data = json.load(f)
            
            # Build navigation context
            all_tables = []
            resolved_files = config.find_resolved_files(protocol_id, collection)
            for rf in resolved_files:
                try:
                    with open(rf) as f:
                        rd = json.load(f)
                    tnum = rd.get('table_metadata', {}).get('table_number', 0)
                    html_name = rf.name.replace('_resolved.json', '_resolved.html')
                    all_tables.append((tnum, html_name))
                except Exception:
                    pass
            all_tables.sort(key=lambda x: x[0])
            
            nav = NavContext(
                protocol_id=protocol_id,
                collection=collection,
                all_tables=all_tables
            )
            
            html = generate_consolidated_html(consolidated_data, nav)
            
            output_file = consolidated_dir / f"{protocol_id}_consolidated.html"
            output_file.write_text(html)
            
            self._analytics.increment("files_visualized")
            
            return {
                "input_file": str(consolidated_file),
                "output_file": str(output_file),
                "status": "success"
            }
        
        except Exception as e:
            self._log_error(f"Visualization failed: {e}")
            return {"output_file": None, "status": "failed", "error": str(e)}
