"""
Resolve Step

Transforms soa-table-extraction JSON to soa-table-resolved JSON.

All transformations are algorithmic - no interpretation required:
- row_position -> stable IDs (prop-001, act-015, etc.)
- indentation_level -> parent_activity_id, child_activity_ids
- hierarchical_level -> parent_property_id, child_property_ids  
- schedule_grid by column -> schedule_columns[] with composite labels
- annotation_markers strings -> linked_annotation_ids[] bidirectional
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .base import PipelineStepBase
from .errors import Errors
from .analytics import AnalyticsBase
from . import config


# =============================================================================
# Constants
# =============================================================================

# Property types commonly seen as timeline hierarchy members.
# Used for validation warnings only — hierarchical_level from extraction
# is the authoritative signal for hierarchy membership.
TIMELINE_PROPERTY_TYPES = {'visit', 'week', 'cycle', 'day', 'period', 'epoch', 'phase',
                           'study_day', 'timepoint'}


# =============================================================================
# ID Generation
# =============================================================================

def make_table_id(table_number: int) -> str:
    return f"table-{table_number:03d}"


def make_property_id(index: int) -> str:
    return f"prop-{index:03d}"


def make_column_id(column_position: int) -> str:
    return f"col-{column_position:03d}"


def make_activity_id(index: int) -> str:
    return f"act-{index:03d}"


def make_annotation_id(index: int) -> str:
    return f"annot-{index:03d}"


# =============================================================================
# Merged Cell Distribution
# =============================================================================

def distribute_merged_cell_values(schedule_grid: list[dict]) -> list[dict]:
    """Distribute values from merged cell anchors to all cells in the merge range.
    
    Extraction captures merged cells with value only in anchor cell and
    merged_cell_range in all cells. This distributes the anchor value.
    """
    # Group cells by merged_cell_range
    merge_groups: dict[str, list[dict]] = {}
    for cell in schedule_grid:
        merge_range = cell.get("merged_cell_range", "")
        if merge_range:
            merge_groups.setdefault(merge_range, []).append(cell)
    
    # For each merge group, find anchor (has value) and distribute
    for merge_range, cells in merge_groups.items():
        anchor_value = ""
        for cell in cells:
            if cell.get("cell_value"):
                anchor_value = cell["cell_value"]
                break
        if anchor_value:
            for cell in cells:
                if not cell.get("cell_value"):
                    cell["cell_value"] = anchor_value
    
    return schedule_grid


# =============================================================================
# Hierarchy Derivation
# =============================================================================

def derive_activity_hierarchy(activities: list[dict]) -> dict[str, dict]:
    """Derive parent-child relationships from indentation_level."""
    indexed = []
    for i, act in enumerate(activities):
        act_id = make_activity_id(i + 1)
        indent = act.get("activity_name_source", {}).get("indentation_level", 0)
        indexed.append({"id": act_id, "index": i, "indentation_level": indent})
    
    hierarchy = {}
    for i, item in enumerate(indexed):
        parent_id = None
        for j in range(i - 1, -1, -1):
            if indexed[j]["indentation_level"] < item["indentation_level"]:
                parent_id = indexed[j]["id"]
                break
        hierarchy[item["id"]] = {
            "parent_activity_id": parent_id,
            "child_activity_ids": [],
            "hierarchy_level": item["indentation_level"]
        }
    
    for act_id, data in hierarchy.items():
        parent_id = data["parent_activity_id"]
        if parent_id and parent_id in hierarchy:
            hierarchy[parent_id]["child_activity_ids"].append(act_id)
    
    return hierarchy


def derive_property_hierarchy(properties: list[dict]) -> dict[str, dict]:
    """Derive parent-child relationships from hierarchical_level."""
    indexed = []
    for i, prop in enumerate(properties):
        prop_id = make_property_id(i + 1)
        level = prop.get("hierarchical_level")
        indexed.append({"id": prop_id, "index": i, "hierarchical_level": level})
    
    hierarchy = {}
    for i, item in enumerate(indexed):
        parent_id = None
        current_level = item["hierarchical_level"]
        if current_level and current_level > 1:
            for j in range(i - 1, -1, -1):
                if indexed[j]["hierarchical_level"] == current_level - 1:
                    parent_id = indexed[j]["id"]
                    break
        hierarchy[item["id"]] = {
            "parent_property_id": parent_id,
            "child_property_ids": [],
            "hierarchical_level": current_level
        }
    
    for prop_id, data in hierarchy.items():
        parent_id = data["parent_property_id"]
        if parent_id and parent_id in hierarchy:
            hierarchy[parent_id]["child_property_ids"].append(prop_id)
    
    return hierarchy


# =============================================================================
# Column Construction
# =============================================================================

def build_schedule_columns(
    schedule_grid: list[dict],
    schedule_properties: list[dict],
    table_id: str
) -> list[dict]:
    """Build explicit column objects from grid values."""
    columns_data: dict[int, list[dict]] = {}
    for cell in schedule_grid:
        col_pos = cell["column_position"]
        if col_pos not in columns_data:
            columns_data[col_pos] = []
        columns_data[col_pos].append(cell)
    
    prop_by_row = {}
    for i, prop in enumerate(schedule_properties):
        prop_id = make_property_id(i + 1)
        prop_by_row[prop["row_position"]] = {
            "property_id": prop_id,
            "hierarchical_level": prop.get("hierarchical_level")
        }
    
    columns = []
    for col_pos in sorted(columns_data.keys()):
        cells = columns_data[col_pos]
        col_id = make_column_id(col_pos)
        is_label = col_pos == 1
        
        column_values = []
        for cell in cells:
            row_pos = cell["row_position"]
            if row_pos in prop_by_row:
                prop_info = prop_by_row[row_pos]
                column_values.append({
                    "property_id": prop_info["property_id"],
                    "value": cell.get("cell_value", ""),
                    "is_merged": cell.get("is_merged_cell", False),
                    "annotation_markers": cell.get("annotation_markers", "")
                })
        
        label_parts = [cv["value"] for cv in column_values if cv["value"]]
        composite_label = " / ".join(label_parts) if label_parts else ""
        
        columns.append({
            "column_id": col_id,
            "table_id": table_id,
            "column_position": col_pos,
            "is_label_column": is_label,
            "column_values": column_values,
            "composite_label": composite_label
        })
    
    return columns


# =============================================================================
# Annotation Cross-Referencing
# =============================================================================

def build_annotation_crossrefs(
    annotations: list[dict],
    schedule_properties: list[dict],
    schedule_grid: list[dict],
    activities: list[dict],
    activity_schedule: list[dict],
    table_id: str
) -> tuple[list[dict], dict, dict, dict, dict]:
    """Build bidirectional annotation cross-references."""
    prop_by_row = {
        prop["row_position"]: make_property_id(i + 1)
        for i, prop in enumerate(schedule_properties)
    }
    act_by_row = {
        act["row_position"]: make_activity_id(i + 1)
        for i, act in enumerate(activities)
    }
    
    marker_to_props: dict[str, list[str]] = {}
    marker_to_acts: dict[str, list[str]] = {}
    marker_to_cells: dict[str, list[tuple[str, str]]] = {}
    
    for i, prop in enumerate(schedule_properties):
        markers = prop.get("annotation_markers", "")
        if markers:
            prop_id = make_property_id(i + 1)
            for m in markers.split(","):
                m = m.strip()
                if m:
                    marker_to_props.setdefault(m, []).append(prop_id)
    
    for i, act in enumerate(activities):
        markers = act.get("annotation_markers", "")
        if markers:
            act_id = make_activity_id(i + 1)
            for m in markers.split(","):
                m = m.strip()
                if m:
                    marker_to_acts.setdefault(m, []).append(act_id)
    
    for cell in activity_schedule:
        markers = cell.get("annotation_markers", "")
        if markers:
            act_id = act_by_row.get(cell["row_position"])
            col_id = make_column_id(cell["column_position"])
            if act_id:
                for m in markers.split(","):
                    m = m.strip()
                    if m:
                        marker_to_cells.setdefault(m, []).append((act_id, col_id))
    
    # Scan schedule_grid for column-level markers (header cells)
    marker_to_cols: dict[str, list[str]] = {}
    for cell in schedule_grid:
        markers = cell.get("annotation_markers", "")
        if markers:
            col_id = make_column_id(cell["column_position"])
            for m in markers.split(","):
                m = m.strip()
                if m and col_id not in marker_to_cols.get(m, []):
                    marker_to_cols.setdefault(m, []).append(col_id)
    
    resolved_annotations = []
    property_annotations: dict[str, list[str]] = {}
    column_annotations: dict[str, list[str]] = {}
    activity_annotations: dict[str, list[str]] = {}
    cell_annotations: dict[tuple[str, str], list[str]] = {}
    
    for i, annot in enumerate(annotations):
        annot_id = make_annotation_id(i + 1)
        marker = annot["annotation_marker"]
        
        referenced = {
            "property_ids": marker_to_props.get(marker, []),
            "column_ids": marker_to_cols.get(marker, []),
            "activity_ids": marker_to_acts.get(marker, []),
            "cell_references": [
                {"activity_id": a, "column_id": c}
                for a, c in marker_to_cells.get(marker, [])
            ]
        }
        
        has_props = bool(referenced["property_ids"])
        has_cols = bool(referenced["column_ids"])
        has_acts = bool(referenced["activity_ids"])
        has_cells = bool(referenced["cell_references"])
        count = sum([has_props, has_cols, has_acts, has_cells])
        if count == 0:
            scope = "table"
        elif count > 1:
            scope = "multiple"
        elif has_acts:
            scope = "activity"
        elif has_cells:
            scope = "cell"
        else:
            scope = "column"
        
        resolved_annotations.append({
            "annotation_id": annot_id,
            "table_id": table_id,
            "annotation_marker": marker,
            "annotation_type": annot["annotation_type"],
            "annotation_text": annot["annotation_text"],
            "annotation_scope": scope,
            "referenced_elements": referenced,
            "marker_locations": annot.get("marker_locations", [])
        })
        
        for prop_id in referenced["property_ids"]:
            property_annotations.setdefault(prop_id, []).append(annot_id)
        for col_id in referenced["column_ids"]:
            column_annotations.setdefault(col_id, []).append(annot_id)
        for act_id in referenced["activity_ids"]:
            activity_annotations.setdefault(act_id, []).append(annot_id)
        for cell_ref in referenced["cell_references"]:
            key = (cell_ref["activity_id"], cell_ref["column_id"])
            cell_annotations.setdefault(key, []).append(annot_id)
    
    return resolved_annotations, property_annotations, column_annotations, activity_annotations, cell_annotations


# =============================================================================
# Validation
# =============================================================================

@dataclass
class ValidationResult:
    structure_valid: bool = True
    hierarchy_valid: bool = True
    annotations_valid: bool = True
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
            return "resolved_with_warnings"
        else:
            return "resolved"


def validate_extraction(data: dict) -> ValidationResult:
    """Validate extraction data before resolution."""
    result = ValidationResult()
    
    required = [
        "schedule_properties",
        "schedule_grid",
        "activities",
        "activity_schedule",
        "annotations"
    ]
    for arr_name in required:
        if arr_name not in data:
            result.errors.append(f"Missing required array: {arr_name}")
            result.structure_valid = False
    
    if not result.structure_valid:
        return result
    
    for i, prop in enumerate(data["schedule_properties"]):
        if not prop.get("property_comment"):
            result.warnings.append(
                f"Property row {prop.get('row_position', i)}: empty property_comment"
            )
    
    # Check for hierarchy level gaps (e.g., L1, L2, null, null)
    props = data["schedule_properties"]
    max_hier_level = 0
    for prop in props:
        level = prop.get("hierarchical_level")
        if level is not None:
            max_hier_level = max(max_hier_level, level)
    if max_hier_level > 0:
        for i, prop in enumerate(props):
            level = prop.get("hierarchical_level")
            prop_name = prop.get("property_name", f"row {prop.get('row_position', i)}")
            prop_type = prop.get("property_type", "other")
            # Warn if a property sits between hierarchical properties but has no level
            if level is None and i > 0 and i < len(props) - 1:
                prev_level = props[i - 1].get("hierarchical_level")
                next_level = props[i + 1].get("hierarchical_level")
                if prev_level is not None and next_level is not None:
                    result.warnings.append(
                        f"Property '{prop_name}' (type={prop_type}) has no "
                        f"hierarchical_level but sits between L{prev_level} and "
                        f"L{next_level} — may be a missing level assignment"
                    )
    
    defined_markers = {a["annotation_marker"] for a in data["annotations"]}
    used_markers = set()
    
    for prop in data["schedule_properties"]:
        for m in prop.get("annotation_markers", "").split(","):
            if m.strip():
                used_markers.add(m.strip())
    
    for act in data["activities"]:
        for m in act.get("annotation_markers", "").split(","):
            if m.strip():
                used_markers.add(m.strip())
    
    for cell in data["activity_schedule"]:
        for m in cell.get("annotation_markers", "").split(","):
            if m.strip():
                used_markers.add(m.strip())
    
    undefined = used_markers - defined_markers
    if undefined:
        result.warnings.append(f"Markers used but not defined: {undefined}")
    

    # Check annotations for empty marker_locations
    for i, annot in enumerate(data["annotations"]):
        marker = annot.get("annotation_marker", "")
        locations = annot.get("marker_locations", [])
        if not locations:
            annot_type = annot.get("annotation_type", "?")
            text_preview = annot.get("annotation_text", "")[:50]
            result.warnings.append(
                f"Annotation '{marker}' ({annot_type}) has no marker_locations "
                f"\u2014 will become orphan: {text_preview}..."
            )
            result.annotations_valid = False

    return result


# =============================================================================
# Cell Value Classification
# =============================================================================

def classify_cell_value(value: str) -> str:
    """Classify the type of cell value."""
    if not value or not value.strip():
        return "empty"
    v = value.strip().upper()
    if v in ["X", "✓", "✔", "•", "◆"]:
        return "marker"
    if v in ["→", "...", "…"]:
        return "continuation"
    if any(kw in v for kw in ["DAILY", "WEEKLY", "PRN"]):
        return "frequency"
    if any(p in v for p in ["DAY", "WEEK", "HOUR"]):
        return "timing_text"
    if any(kw in v for kw in ["IF", "OPTIONAL"]):
        return "conditional"
    return "other"


# =============================================================================
# Core Resolution Function
# =============================================================================

def resolve_extraction(extraction: dict, input_filename: str) -> dict:
    """Transform extraction JSON to resolved JSON.
    
    Args:
        extraction: Parsed extraction JSON data
        input_filename: Name of source file (for provenance)
        
    Returns:
        Resolved JSON data structure
        
    Raises:
        ValueError: If validation fails with errors
    """
    validation = validate_extraction(extraction)
    if not validation.is_valid:
        raise ValueError(f"Validation failed: {validation.errors}")
    
    table_meta = extraction["table_metadata"]
    table_number = table_meta["table_number"]
    table_id = make_table_id(table_number)
    
    schedule_properties = extraction["schedule_properties"]
    schedule_grid = distribute_merged_cell_values(extraction["schedule_grid"])
    activities = extraction["activities"]
    activity_schedule = extraction["activity_schedule"]
    annotations = extraction["annotations"]
    
    prop_hierarchy = derive_property_hierarchy(schedule_properties)
    act_hierarchy = derive_activity_hierarchy(activities)
    
    schedule_columns = build_schedule_columns(
        schedule_grid, schedule_properties, table_id
    )
    
    resolved_annotations, prop_annots, col_annots, act_annots, cell_annots = (
        build_annotation_crossrefs(
            annotations, schedule_properties, schedule_grid, activities, activity_schedule, table_id
        )
    )
    
    # Post-resolution: warn about annotations with no referenced elements
    orphan_count = 0
    for ra in resolved_annotations:
        refs = ra["referenced_elements"]
        has_any = (
            refs.get("property_ids")
            or refs.get("column_ids")
            or refs.get("activity_ids")
            or refs.get("cell_references")
        )
        if not has_any:
            orphan_count += 1
            marker = ra["annotation_marker"]
            text_preview = ra["annotation_text"][:50]
            validation.warnings.append(
                f"Resolved annotation {ra['annotation_id']} ('{marker}') has no "
                f"referenced elements \u2014 orphan: {text_preview}..."
            )
    if orphan_count:
        validation.warnings.append(
            f"Annotation summary: {orphan_count} of {len(resolved_annotations)} "
            f"annotations have no referenced elements (will be orphans in consolidation)"
        )

    # Add linked_annotation_ids to schedule_columns
    for col in schedule_columns:
        col["linked_annotation_ids"] = col_annots.get(col["column_id"], [])
    
    resolved_properties = []
    for i, prop in enumerate(schedule_properties):
        prop_id = make_property_id(i + 1)
        hier = prop_hierarchy[prop_id]
        
        # Trust hierarchical_level from extraction as the authoritative signal.
        # If extraction assigned a level, this property is part of the hierarchy
        # regardless of property_type (covers study_day, timepoint, window, etc.).
        # Properties without a level are column qualifiers.
        hierarchical_level = prop.get("hierarchical_level")
        if hierarchical_level is not None:
            parent_property_id = hier["parent_property_id"]
            child_property_ids = hier["child_property_ids"]
        else:
            parent_property_id = None
            child_property_ids = []
        
        resolved_properties.append({
            "property_id": prop_id,
            "table_id": table_id,
            "row_position": prop["row_position"],
            "property_name": prop["property_name"],
            "property_name_source": prop.get("property_name_source"),
            "property_type": prop.get("property_type", "other"),
            "property_comment": prop.get("property_comment", ""),
            "hierarchical_level": hierarchical_level,
            "parent_property_id": parent_property_id,
            "child_property_ids": child_property_ids,
            "annotation_markers": prop.get("annotation_markers", ""),
            "linked_annotation_ids": prop_annots.get(prop_id, [])
        })
    
    resolved_activities = []
    for i, act in enumerate(activities):
        act_id = make_activity_id(i + 1)
        hier = act_hierarchy[act_id]
        source = act.get("activity_name_source", {})
        
        has_schedule_data = any(
            cell["row_position"] == act["row_position"]
            and cell.get("cell_value", "").strip()
            for cell in activity_schedule
        )
        is_section_header = (
            hier["hierarchy_level"] == 0
            and len(hier["child_activity_ids"]) > 0
            and not has_schedule_data
        )
        
        resolved_activities.append({
            "activity_id": act_id,
            "table_id": table_id,
            "row_position": act["row_position"],
            "activity_name": act["activity_name"],
            "activity_name_source": source,
            "hierarchy_level": hier["hierarchy_level"],
            "is_section_header": is_section_header,
            "parent_activity_id": hier["parent_activity_id"],
            "child_activity_ids": hier["child_activity_ids"],
            "has_schedule_data": has_schedule_data,
            "annotation_markers": act.get("annotation_markers", ""),
            "linked_annotation_ids": act_annots.get(act_id, [])
        })
    
    act_by_row = {
        act["row_position"]: make_activity_id(i + 1)
        for i, act in enumerate(activities)
    }
    resolved_schedule = []
    for cell in activity_schedule:
        act_id = act_by_row.get(cell["row_position"])
        if not act_id:
            continue
        col_id = make_column_id(cell["column_position"])
        cell_value = cell.get("cell_value", "")
        resolved_schedule.append({
            "activity_id": act_id,
            "column_id": col_id,
            "row_position": cell["row_position"],
            "column_position": cell["column_position"],
            "cell_value": cell_value,
            "cell_value_type": classify_cell_value(cell_value),
            "source_range": cell.get("source_range", ""),
            "annotation_markers": cell.get("annotation_markers", ""),
            "linked_annotation_ids": cell_annots.get((act_id, col_id), [])
        })
    
    resolved_table_meta = {
        "table_id": table_id,
        "table_number": table_number,
        "table_type": table_meta.get("table_type", "main_soa"),
        "table_title": table_meta.get("table_title", ""),
        "table_purpose": table_meta.get("table_purpose", ""),
        "page_start": table_meta["page_start"],
        "page_end": table_meta["page_end"],
        "track_label": table_meta.get("track_label"),
        "column_count": len(schedule_columns),
        "row_count": max(
            [p["row_position"] for p in schedule_properties] +
            [a["row_position"] for a in activities] +
            [0]
        ),
        "header_row_count": len(schedule_properties),
        "activity_row_count": len(activities),
        "notes": table_meta.get("notes", "")
    }
    
    resolution_metadata = {
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "resolver": "soa2usdm.steps.resolve v1.0",
        "source_extraction": {
            "schema_name": extraction.get("schema_name", "soa-table-extraction"),
            "schema_version": extraction.get("schema_version", "1.0"),
            "extraction_file": input_filename,
            "extraction_status": extraction.get(
                "extraction_metadata", {}
            ).get("extraction_status", "unknown")
        },
        "validation_results": {
            "structure_valid": validation.structure_valid,
            "hierarchy_valid": validation.hierarchy_valid,
            "annotations_valid": validation.annotations_valid,
            "validation_warnings": validation.warnings,
            "validation_errors": validation.errors
        },
        "resolution_status": validation.status,
        "ready_for_integration": validation.is_valid,
        "resolution_notes": ""
    }
    
    return {
        "schema_name": "soa-table-resolved",
        "schema_version": "1.0",
        "resolution_metadata": resolution_metadata,
        "extraction_metadata": extraction.get("extraction_metadata", {}),
        "table_metadata": resolved_table_meta,
        "schedule_properties": resolved_properties,
        "schedule_columns": schedule_columns,
        "activities": resolved_activities,
        "activity_schedule": resolved_schedule,
        "annotations": resolved_annotations
    }


# =============================================================================
# Pipeline Step Class
# =============================================================================

class ResolveStep(PipelineStepBase):
    """Resolve all extraction files for a protocol."""
    
    step_name = "resolve"
    
    def execute(self, data: dict) -> dict:
        """Execute resolution for all extraction files.
        
        Args:
            data: Must contain 'source' with protocol_id, collection, paths
            
        Returns:
            Dict with input_files, output_files, and per-file results
        """
        source = data.get("source", {})
        protocol_id = source.get("protocol_id")
        collection = source.get("collection")
        
        if not protocol_id or not collection:
            self._log_error("Missing protocol_id or collection in source")
            return {"input_files": [], "output_files": [], "results": []}
        
        # Find extraction files
        extraction_files = config.find_extraction_files(protocol_id, collection)
        
        if not extraction_files:
            self._log_error(
                "No extraction files found",
                {"protocol_id": protocol_id, "collection": collection}
            )
            return {"input_files": [], "output_files": [], "results": []}
        
        self._analytics.record("extraction_files_found", len(extraction_files))
        
        # Process each file
        resolved_dir = config.get_resolved_dir(protocol_id, collection)
        resolved_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        output_files = []
        
        for extraction_file in extraction_files:
            output_filename = config.extraction_to_resolved_filename(extraction_file.name)
            output_path = resolved_dir / output_filename
            
            result = self._resolve_file(extraction_file, output_path)
            results.append(result)
            
            if result["status"] != "failed":
                output_files.append(output_path)
                self._analytics.increment("files_resolved")
            else:
                self._analytics.increment("files_failed")
        
        return {
            "input_files": [str(f) for f in extraction_files],
            "output_files": [str(f) for f in output_files],
            "output_dir": str(resolved_dir),
            "results": results
        }
    
    def _resolve_file(self, input_path: Path, output_path: Path) -> dict:
        """Resolve a single extraction file."""
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                extraction_data = json.load(f)
            
            resolved_data = resolve_extraction(extraction_data, input_path.name)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(resolved_data, f, indent=2, ensure_ascii=False)
            
            return {
                "input": input_path.name,
                "output": output_path.name,
                "status": resolved_data["resolution_metadata"]["resolution_status"],
                "activities": len(resolved_data["activities"]),
                "columns": len(resolved_data["schedule_columns"]),
                "warnings": resolved_data["resolution_metadata"]["validation_results"]["validation_warnings"]
            }
        
        except Exception as e:
            self._log_error(str(e), {"file": input_path.name})
            return {
                "input": input_path.name,
                "output": None,
                "status": "failed",
                "error": str(e)
            }
