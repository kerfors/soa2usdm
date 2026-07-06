"""
Visualize Resolved Step

Generates HTML visualization from resolved JSON files (Layer 2, per-table).

Features:
- Extraction and Resolution metadata display
- Table metadata with classification
- Property hierarchy with types and comments
- Schedule grid with cell value types
- Activity hierarchy with parent-child relationships
- Annotations with cross-references and scope
"""

import json
import html as html_lib
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass

from .base import PipelineStepBase
from . import config


# =============================================================================
# Color Scheme
# =============================================================================

LEVEL_COLORS = ['#375623', '#548235', '#70AD47', '#A9D08E', '#C6E0B4', '#E2EFDA']

COLORS = {
    'header': '#1F4788',
    'extraction': '#5B9BD5',
    'resolution': '#2E75B6',
    'table_meta': '#7030A0',
    'properties': '#70AD47',
    'activities': '#C65911',
    'schedule': '#1F4788',
    'annotations': '#6c757d',
    'cell_marker': '#BDD7EE',
    'cell_timing': '#E2EFDA',
    'cell_frequency': '#FFF2CC',
    'cell_continuation': '#FCE4D6',
    'cell_conditional': '#E1BEE7',
    'cell_empty': '#FFFFFF',
    'cell_other': '#F5F5F5',
    'section_header': '#FBE5D6',
    'has_children': '#E8F4E8',
    'leaf_activity': '#FFFFFF',
    'status_ok': '#28a745',
    'status_warn': '#fd7e14',
    'status_fail': '#dc3545',
    'qualifier_bg': '#f5f5f5',
    'qualifier_text': '#666',
}

CELL_TYPE_COLORS = {
    'marker': COLORS['cell_marker'],
    'timing_text': COLORS['cell_timing'],
    'frequency': COLORS['cell_frequency'],
    'continuation': COLORS['cell_continuation'],
    'conditional': COLORS['cell_conditional'],
    'empty': COLORS['cell_empty'],
    'other': COLORS['cell_other'],
}

TABLE_TYPE_COLORS = {
    'main_soa': '#1F4788',
    'continuation': '#5B9BD5',
    'subsidiary': '#17a2b8',
    'domain': '#548235',
    'track': '#7030A0',
    'reference': '#6c757d',
}


def get_level_color(level: int) -> str:
    idx = min(level - 1, len(LEVEL_COLORS) - 1)
    return LEVEL_COLORS[max(0, idx)]


def get_level_text_color(level: int) -> str:
    return 'white' if level <= 2 else '#333'


def get_status_color(status: str) -> str:
    if 'fail' in status.lower():
        return COLORS['status_fail']
    if 'warn' in status.lower():
        return COLORS['status_warn']
    return COLORS['status_ok']


# =============================================================================
# Navigation
# =============================================================================

@dataclass
class NavContext:
    """Navigation context for HTML pages."""
    protocol_id: str
    collection: str
    current_table_num: int
    all_tables: list  # List of (table_num, html_filename)
    has_consolidated: bool
    
    def get_prev_table(self) -> Optional[tuple]:
        """Get (table_num, html_filename) for previous table."""
        for i, (tnum, fname) in enumerate(self.all_tables):
            if tnum == self.current_table_num and i > 0:
                return self.all_tables[i - 1]
        return None
    
    def get_next_table(self) -> Optional[tuple]:
        """Get (table_num, html_filename) for next table."""
        for i, (tnum, fname) in enumerate(self.all_tables):
            if tnum == self.current_table_num and i < len(self.all_tables) - 1:
                return self.all_tables[i + 1]
        return None


def gen_navigation(nav: Optional[NavContext], is_consolidated: bool = False) -> str:
    """Generate navigation bar HTML."""
    if nav is None:
        return ''
    
    # Breadcrumb: Collection > Protocol > Table
    # Path from resolved/ is ../../index.html for collection index
    parts = [f'<a href="../../../index.html" class="nav-link">{nav.collection}</a>']
    parts.append('<span class="nav-sep">›</span>')
    parts.append(f'<span class="nav-current">{nav.protocol_id}</span>')
    
    if not is_consolidated:
        parts.append('<span class="nav-sep">›</span>')
        parts.append(f'<span class="nav-current">Table {nav.current_table_num}</span>')
    
    breadcrumb = ''.join(parts)
    
    # Table navigation (for resolved pages with multiple tables)
    table_nav = ''
    if not is_consolidated and len(nav.all_tables) > 1:
        prev_table = nav.get_prev_table()
        next_table = nav.get_next_table()
        
        prev_link = f'<a href="{prev_table[1]}" class="nav-btn">◀ T{prev_table[0]}</a>' if prev_table else '<span class="nav-btn disabled">◀</span>'
        next_link = f'<a href="{next_table[1]}" class="nav-btn">T{next_table[0]} ▶</a>' if next_table else '<span class="nav-btn disabled">▶</span>'
        
        # Table selector buttons
        table_btns = []
        for tnum, fname in nav.all_tables:
            cls = ' current' if tnum == nav.current_table_num else ''
            table_btns.append(f'<a href="{fname}" class="nav-table-btn{cls}">T{tnum}</a>')
        
        table_nav = f'''
        <div class="nav-tables">
            {prev_link}
            <span class="nav-table-list">{' '.join(table_btns)}</span>
            {next_link}
        </div>'''
    
    # Action links
    action_links = ''
    if not is_consolidated and nav.has_consolidated:
        action_links = f'<a href="../consolidated/{nav.protocol_id}_consolidated.html" class="nav-action">Consolidated View →</a>'
    
    return f'''
    <nav class="navigation">
        <div class="nav-breadcrumb">{breadcrumb}</div>
        {table_nav}
        <div class="nav-actions">{action_links}</div>
    </nav>'''


# =============================================================================
# HTML Utilities
# =============================================================================

def esc(text) -> str:
    return html_lib.escape(str(text)) if text else ""


def format_value(value, cls: str = 'data') -> str:
    if value is None:
        return f'<span class="{cls} null">null</span>'
    elif isinstance(value, bool):
        return f'<span class="{cls} bool">{str(value).lower()}</span>'
    elif isinstance(value, (int, float)):
        return f'<span class="{cls}">{value}</span>'
    elif isinstance(value, str):
        return f'<span class="{cls}">{esc(value)}</span>'
    elif isinstance(value, list):
        if len(value) == 0:
            return f'<span class="{cls} arr">[]</span>'
        return f'<span class="{cls} arr">[{len(value)} items]</span>'
    elif isinstance(value, dict):
        return f'<span class="{cls} obj">{{...}}</span>'
    return f'<span class="{cls}">{esc(str(value))}</span>'


def format_list(items: list, max_show: int = 5) -> str:
    if not items:
        return '<span class="trace">—</span>'
    shown = items[:max_show]
    result = ', '.join(esc(str(i)) for i in shown)
    if len(items) > max_show:
        result += f' <span class="trace">(+{len(items) - max_show} more)</span>'
    return result


# =============================================================================
# Component Generators
# =============================================================================

def gen_extraction_metadata(data: dict) -> str:
    """Generate Extraction Metadata component."""
    meta = data.get('extraction_metadata', {})
    
    rows = []
    
    # Basic extraction info
    for field in ['extracted_at', 'extractor', 'extraction_status']:
        if field in meta:
            rows.append(f'<tr><td class="field">{field}</td><td>{format_value(meta[field])}</td></tr>')
    
    # Source document
    source_doc = meta.get('source_document', {})
    if source_doc:
        doc_info = []
        if source_doc.get('filename'):
            doc_info.append(source_doc['filename'])
        if source_doc.get('document_type'):
            doc_info.append(f"[{source_doc['document_type']}]")
        if source_doc.get('document_version'):
            doc_info.append(f"v{source_doc['document_version']}")
        if doc_info:
            rows.append(f'<tr><td class="field">source_document</td><td>{esc(" ".join(doc_info))}</td></tr>')
    
    # Verification
    verification = meta.get('verification', {})
    if verification:
        if verification.get('excel_verified'):
            verify_info = f"✓ Verified"
            if verification.get('verified_by'):
                verify_info += f" by {verification['verified_by']}"
            if verification.get('verified_at'):
                verify_info += f" at {verification['verified_at'][:10]}"
            rows.append(f'<tr><td class="field">verification</td><td><span class="status-ok">{esc(verify_info)}</span></td></tr>')
        if verification.get('excel_file'):
            rows.append(f'<tr><td class="field">excel_file</td><td class="trace">{esc(verification["excel_file"])}</td></tr>')
        if verification.get('verification_notes'):
            rows.append(f'<tr><td class="field">verification_notes</td><td>{esc(verification["verification_notes"])}</td></tr>')
    
    # Extraction notes
    if meta.get('extraction_notes'):
        rows.append(f'<tr><td class="field">extraction_notes</td><td>{esc(meta["extraction_notes"])}</td></tr>')
    
    status = meta.get('extraction_status', 'unknown')
    status_color = get_status_color(status)
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['extraction']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Extraction Metadata</span>
            <span class="comp-desc" style="background: {status_color}; padding: 2px 8px; border-radius: 3px;">{status}</span>
        </div>
        <div class="comp-body">
            <table class="comp-table"><tbody>{''.join(rows)}</tbody></table>
        </div>
    </div>'''


def gen_resolution_metadata(data: dict) -> str:
    """Generate Resolution Metadata component."""
    meta = data.get('resolution_metadata', {})
    
    rows = []
    
    # Basic resolution info
    for field in ['resolved_at', 'resolver']:
        if field in meta:
            rows.append(f'<tr><td class="field">{field}</td><td>{format_value(meta[field])}</td></tr>')
    
    # Source extraction reference
    source_ext = meta.get('source_extraction', {})
    if source_ext:
        ext_info = []
        if source_ext.get('extraction_file'):
            ext_info.append(source_ext['extraction_file'])
        if source_ext.get('schema_version'):
            ext_info.append(f"schema v{source_ext['schema_version']}")
        if ext_info:
            rows.append(f'<tr><td class="field">source_extraction</td><td class="trace">{esc(" | ".join(ext_info))}</td></tr>')
    
    # Validation results
    validation = meta.get('validation_results', {})
    if validation:
        checks = []
        for check in ['structure_valid', 'hierarchy_valid', 'annotations_valid']:
            val = validation.get(check)
            if val is not None:
                icon = '✓' if val else '✗'
                color = 'status-ok' if val else 'status-fail'
                checks.append(f'<span class="{color}">{icon} {check.replace("_valid", "")}</span>')
        if checks:
            rows.append(f'<tr><td class="field">validation</td><td>{" &nbsp; ".join(checks)}</td></tr>')
        
        warnings = validation.get('validation_warnings', [])
        if warnings:
            warn_html = '<br/>'.join(f'⚠ {esc(w)}' for w in warnings)
            rows.append(f'<tr><td class="field">warnings</td><td class="status-warn">{warn_html}</td></tr>')
        
        errors = validation.get('validation_errors', [])
        if errors:
            err_html = '<br/>'.join(f'✗ {esc(e)}' for e in errors)
            rows.append(f'<tr><td class="field">errors</td><td class="status-fail">{err_html}</td></tr>')
    
    # Resolution status
    for field in ['resolution_status', 'ready_for_integration']:
        if field in meta:
            rows.append(f'<tr><td class="field">{field}</td><td>{format_value(meta[field])}</td></tr>')
    
    if meta.get('resolution_notes'):
        rows.append(f'<tr><td class="field">resolution_notes</td><td>{esc(meta["resolution_notes"])}</td></tr>')
    
    status = meta.get('resolution_status', 'unknown')
    status_color = get_status_color(status)
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['resolution']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Resolution Metadata</span>
            <span class="comp-desc" style="background: {status_color}; padding: 2px 8px; border-radius: 3px;">{status}</span>
        </div>
        <div class="comp-body">
            <table class="comp-table"><tbody>{''.join(rows)}</tbody></table>
        </div>
    </div>'''


def gen_table_metadata(data: dict) -> str:
    """Generate Table Metadata component."""
    meta = data.get('table_metadata', {})
    
    table_type = meta.get('table_type', 'unknown')
    type_color = TABLE_TYPE_COLORS.get(table_type, '#666')
    
    rows = []
    
    # Identity
    rows.append(f'<tr><td class="field">table_id</td><td class="id">{esc(meta.get("table_id", ""))}</td></tr>')
    rows.append(f'<tr><td class="field">table_number</td><td>{meta.get("table_number", "")}</td></tr>')
    rows.append(f'<tr><td class="field">table_type</td><td><span class="type-badge" style="background: {type_color};">{table_type}</span></td></tr>')
    
    if meta.get('track_label'):
        rows.append(f'<tr><td class="field">track_label</td><td><span class="track-label">{esc(meta["track_label"])}</span></td></tr>')
    
    # Title and purpose
    if meta.get('table_title'):
        rows.append(f'<tr><td class="field">table_title</td><td>{esc(meta["table_title"])}</td></tr>')
    if meta.get('table_purpose'):
        rows.append(f'<tr><td class="field">table_purpose</td><td>{esc(meta["table_purpose"])}</td></tr>')
    
    # Pages
    page_range = f"{meta.get('page_start', '?')} – {meta.get('page_end', '?')}"
    rows.append(f'<tr><td class="field">pages</td><td>{page_range}</td></tr>')
    
    # Continuation
    if meta.get('continuation_of'):
        rows.append(f'<tr><td class="field">continuation_of</td><td class="id">{esc(meta["continuation_of"])}</td></tr>')
    
    # Counts
    counts = []
    for field, label in [('column_count', 'cols'), ('row_count', 'rows'), 
                         ('header_row_count', 'header'), ('activity_row_count', 'activity')]:
        if meta.get(field):
            counts.append(f'{meta[field]} {label}')
    if counts:
        rows.append(f'<tr><td class="field">dimensions</td><td class="trace">{" | ".join(counts)}</td></tr>')
    
    if meta.get('notes'):
        rows.append(f'<tr><td class="field">notes</td><td>{esc(meta["notes"])}</td></tr>')
    
    title_display = meta.get('table_title', f"Table {meta.get('table_number', '?')}")
    if len(title_display) > 50:
        title_display = title_display[:47] + '...'
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['table_meta']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Table Metadata</span>
            <span class="comp-desc">{esc(title_display)}</span>
        </div>
        <div class="comp-body">
            <table class="comp-table"><tbody>{''.join(rows)}</tbody></table>
        </div>
    </div>'''


def gen_property_hierarchy(data: dict) -> str:
    """Generate Property Hierarchy component with separate sections for hierarchy and qualifiers."""
    properties = data.get('schedule_properties', [])
    
    if not properties:
        return ''
    
    # Split into hierarchical (timeline) and qualifier (non-hierarchical) properties
    hierarchical_props = [p for p in properties if p.get('hierarchical_level') is not None]
    qualifier_props = [p for p in properties if p.get('hierarchical_level') is None]
    
    def render_property_row(prop, is_qualifier=False):
        """Render a single property row."""
        level = prop.get('hierarchical_level')
        
        if is_qualifier:
            # Neutral styling for qualifiers - no level badge
            level_cell = '<td class="level-cell" style="background: #f5f5f5; color: #666;">—</td>'
        else:
            bg = get_level_color(level)
            text_color = get_level_text_color(level)
            level_cell = f'<td class="level-cell" style="background: {bg}; color: {text_color};">L{level}</td>'
        
        prop_id = prop.get('property_id', '')
        prop_name = prop.get('property_name', '')
        prop_type = prop.get('property_type', 'other')
        prop_comment = prop.get('property_comment', '')
        
        # Source info
        source = prop.get('property_name_source', {})
        synthesized = source.get('synthesized', False) if source else False
        source_indicator = '<span class="synth-badge" title="Synthesized: name inferred from row data (source label cell was empty)">S</span>' if synthesized else ''
        
        # Parent/children
        parent = prop.get('parent_property_id', '')
        children = prop.get('child_property_ids', [])
        hierarchy_info = []
        if parent:
            hierarchy_info.append(f'↑{parent}')
        if children:
            hierarchy_info.append(f'↓{len(children)}')
        hierarchy_display = ' '.join(hierarchy_info) if hierarchy_info else '—'
        
        # Annotations
        markers = prop.get('annotation_markers', '')
        linked = prop.get('linked_annotation_ids', [])
        annot_display = ''
        if markers:
            annot_display = f'<span class="marker">{esc(markers)}</span>'
        if linked:
            annot_display += f' → {format_list(linked, 3)}'
        
        return f'''<tr>
            <td class="id">{prop_id}</td>
            {level_cell}
            <td>{esc(prop_name)} {source_indicator}</td>
            <td class="type">{prop_type}</td>
            <td class="comment">{esc(prop_comment)}</td>
            <td class="trace">{hierarchy_display}</td>
            <td class="trace">{annot_display if annot_display else '—'}</td>
        </tr>'''
    
    # Build rows
    rows = []
    
    # Hierarchical properties first
    for prop in hierarchical_props:
        rows.append(render_property_row(prop, is_qualifier=False))
    
    # Add section divider if both types exist
    if hierarchical_props and qualifier_props:
        rows.append('<tr class="section-divider"><td colspan="7" style="background: #e9ecef; padding: 4px 10px; font-size: 10px; font-weight: 600; color: #666;">Column Qualifiers</td></tr>')
    
    # Qualifier properties
    for prop in qualifier_props:
        rows.append(render_property_row(prop, is_qualifier=True))
    
    # Build description
    desc_parts = []
    if hierarchical_props:
        desc_parts.append(f"{len(hierarchical_props)} hierarchical")
    if qualifier_props:
        desc_parts.append(f"{len(qualifier_props)} qualifier")
    desc = ", ".join(desc_parts) if desc_parts else f"{len(properties)} properties"
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['properties']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Property Hierarchy</span>
            <span class="comp-desc">{desc}</span>
        </div>
        <div class="comp-body">
            <table class="comp-table">
                <thead><tr>
                    <th>ID</th><th>Level</th><th>Name</th><th>Type</th><th>Comment</th><th>Hierarchy</th><th>Annotations</th>
                </tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
            <p class="comp-note"><span class="synth-badge">S</span> = Synthesized (name inferred from row data, source label cell was empty)</p>
        </div>
    </div>'''


def gen_activities_component(data: dict) -> str:
    """Generate Activities component."""
    activities = data.get('activities', [])
    
    if not activities:
        return ''
    
    # Build lookup for parent names
    act_lookup = {a['activity_id']: a['activity_name'] for a in activities}
    
    rows = []
    for act in activities:
        act_id = act.get('activity_id', '')
        act_name = act.get('activity_name', '')
        level = act.get('hierarchy_level', 0)
        is_header = act.get('is_section_header', False)
        has_children = bool(act.get('child_activity_ids'))
        
        # Row styling - section headers orange, parents green, leaves white
        if is_header:
            bg = COLORS['section_header']
        elif has_children:
            bg = COLORS['has_children']
        else:
            bg = COLORS['leaf_activity']
        
        # Indentation for display
        indent = '&nbsp;&nbsp;' * level
        name_class = 'section-header' if is_header else ''
        
        # Parent info - show parent name (truncated)
        parent_id = act.get('parent_activity_id', '')
        if parent_id:
            parent_name = act_lookup.get(parent_id, parent_id)
            parent_display = f'<span class="trace">{esc(parent_name[:30])}</span>'
        else:
            parent_display = '—'
        
        # Annotations
        markers = act.get('annotation_markers', '')
        linked = act.get('linked_annotation_ids', [])
        annot_display = ''
        if markers:
            annot_display = f'<span class="marker">{esc(markers)}</span>'
        if linked:
            annot_display += f' → {format_list(linked, 3)}'
        
        rows.append(f'''<tr style="background: {bg};">
            <td class="id">{act_id}</td>
            <td class="level-num">{level}</td>
            <td class="activity-name {name_class}">{indent}{esc(act_name)}</td>
            <td>{parent_display}</td>
            <td class="trace">{annot_display if annot_display else '—'}</td>
        </tr>''')
    
    section_count = sum(1 for a in activities if a.get('is_section_header'))
    leaf_count = sum(1 for a in activities if not a.get('child_activity_ids'))
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['activities']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Activities</span>
            <span class="comp-desc">{len(activities)} total ({section_count} headers, {leaf_count} leaf)</span>
        </div>
        <div class="comp-body">
            <table class="comp-table">
                <thead><tr>
                    <th>ID</th><th>Lvl</th><th>Activity Name</th><th>Parent</th><th>Annotations</th>
                </tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </div>'''


def gen_annotations_component(data: dict) -> str:
    """Generate Annotations component."""
    annotations = data.get('annotations', [])
    
    if not annotations:
        return ''
    
    # Group by type
    by_type = defaultdict(list)
    for ann in annotations:
        by_type[ann.get('annotation_type', 'footnote')].append(ann)
    
    type_colors = {
        'footnote': '#5a6268',
        'abbreviation': '#2E75B6',
        'legend': '#538135',
        'source_note': '#BF8F00',
        'continuation_note': '#C65911'
    }
    
    sections = []
    type_order = ['footnote', 'abbreviation', 'legend', 'source_note', 'continuation_note']
    
    for atype in type_order:
        type_annots = by_type.get(atype, [])
        if not type_annots:
            continue
        
        rows = []
        for ann in type_annots:
            annot_id = ann.get('annotation_id', '')
            marker = ann.get('annotation_marker', '')
            scope = ann.get('annotation_scope', 'table')
            text = ann.get('annotation_text', '')
            
            # Truncate long text
            text_display = text if len(text) <= 100 else text[:97] + '...'
            
            # Referenced elements
            refs = ann.get('referenced_elements', {})
            ref_parts = []
            if refs.get('property_ids'):
                ref_parts.append(f"props: {format_list(refs['property_ids'], 3)}")
            if refs.get('column_ids'):
                ref_parts.append(f"cols: {format_list(refs['column_ids'], 3)}")
            if refs.get('activity_ids'):
                ref_parts.append(f"acts: {format_list(refs['activity_ids'], 3)}")
            if refs.get('cell_references'):
                ref_parts.append(f"cells: {len(refs['cell_references'])}")
            refs_display = ' | '.join(ref_parts) if ref_parts else '—'
            
            # Marker locations count
            locations = ann.get('marker_locations', [])
            loc_display = f'{len(locations)} locations' if locations else '—'
            
            rows.append(f'''<tr>
                <td class="id">{annot_id}</td>
                <td class="marker-cell"><span class="marker">{esc(marker)}</span></td>
                <td class="type">{scope}</td>
                <td class="text-full" title="{esc(text)}">{esc(text_display)}</td>
                <td class="trace">{refs_display}</td>
                <td class="trace">{loc_display}</td>
            </tr>''')
        
        color = type_colors.get(atype, '#666')
        sections.append(f'''
            <div class="annot-section">
                <div class="annot-type-header" style="background: {color};">{atype.replace('_', ' ').title()} ({len(type_annots)})</div>
                <table class="comp-table">
                    <thead><tr>
                        <th>ID</th><th>Marker</th><th>Scope</th><th>Text</th><th>References</th><th>Locations</th>
                    </tr></thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
        ''')
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['annotations']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Annotations</span>
            <span class="comp-desc">{len(annotations)} annotations</span>
        </div>
        <div class="comp-body">
            {''.join(sections)}
        </div>
    </div>'''


# =============================================================================
# Schedule Grid
# =============================================================================

FROZEN_COL_WIDTH = 280


def gen_schedule_grid(data: dict) -> str:
    """Generate Schedule Grid component."""
    columns = data.get('schedule_columns', [])
    activities = data.get('activities', [])
    schedule = data.get('activity_schedule', [])
    properties = data.get('schedule_properties', [])
    
    if not columns or not activities:
        return ''
    
    # Filter to data columns only
    data_cols = [c for c in columns if not c.get('is_label_column', False)]
    
    if not data_cols:
        return ''
    
    # Build schedule lookup
    cell_lookup = {}
    for cell in schedule:
        key = (cell.get('activity_id'), cell.get('column_id'))
        cell_lookup[key] = cell
    
    rows = []
    
    # Header row: column IDs
    rows.append('<tr><th class="frozen-col activity-header">Activity</th>')
    for col in data_cols:
        col_id = col.get('column_id', '')
        rows.append(f'<th class="col-header" title="{esc(col.get("composite_label", ""))}">{col_id}</th>')
    rows.append('</tr>')
    
    # Property value rows
    for prop in properties:
        level = prop.get('hierarchical_level')
        prop_name = prop.get('property_name', '')
        prop_id = prop.get('property_id', '')
        
        # Styling: hierarchical properties get green levels, qualifiers get neutral
        if level is not None:
            bg = get_level_color(level)
            text_color = get_level_text_color(level)
        else:
            bg = COLORS['qualifier_bg']
            text_color = COLORS['qualifier_text']
        
        rows.append(f'<tr><td class="frozen-col prop-row" style="background: {bg}; color: {text_color};">{esc(prop_name)}<br/><span class="prop-id">{prop_id}</span></td>')
        
        for col in data_cols:
            # Find value for this property in this column
            col_values = col.get('column_values', [])
            value = ''
            for cv in col_values:
                if cv.get('property_id') == prop_id:
                    value = cv.get('value', '')
                    break
            
            rows.append(f'<td class="prop-cell" style="background: {bg}; color: {text_color};">{esc(value)}</td>')
        rows.append('</tr>')
    
    # Activity rows
    for act in activities:
        act_id = act.get('activity_id', '')
        act_name = act.get('activity_name', '')
        level = act.get('hierarchy_level', 0)
        is_header = act.get('is_section_header', False)
        
        # Row styling
        if is_header:
            row_bg = COLORS['section_header']
        else:
            row_bg = '#fff'
        
        indent = '&nbsp;&nbsp;' * level
        name_class = 'section-header' if is_header else ''
        
        rows.append(f'<tr><td class="frozen-col activity-cell {name_class}" style="background: {row_bg};">{indent}{esc(act_name)}<br/><span class="act-id">{act_id}</span></td>')
        
        for col in data_cols:
            col_id = col.get('column_id', '')
            cell = cell_lookup.get((act_id, col_id))
            
            if cell and cell.get('cell_value'):
                value = cell.get('cell_value', '')
                value_type = cell.get('cell_value_type', 'other')
                cell_bg = CELL_TYPE_COLORS.get(value_type, COLORS['cell_other'])
                
                # Check for annotations
                markers = cell.get('annotation_markers', '')
                marker_display = f'<sup class="cell-marker">{esc(markers)}</sup>' if markers else ''
                
                rows.append(f'<td class="schedule-cell" style="background: {cell_bg};" title="{value_type}">{esc(value)}{marker_display}</td>')
            else:
                rows.append('<td class="schedule-cell empty"></td>')
        
        rows.append('</tr>')
    
    # Cell type legend
    legend_items = []
    for vtype, color in CELL_TYPE_COLORS.items():
        if vtype != 'empty':
            legend_items.append(f'<span class="legend-item"><span class="legend-color" style="background: {color};"></span>{vtype}</span>')
    legend_html = ' '.join(legend_items)
    
    non_empty = sum(1 for c in schedule if c.get('cell_value'))
    
    return f'''
    <div class="comp">
        <div class="comp-header collapsible" style="background: {COLORS['schedule']};" onclick="toggleSection(this)">
            <span class="comp-title"><span class="toggle-icon">▼</span> Schedule Grid</span>
            <span class="comp-desc">{len(activities)} activities × {len(data_cols)} columns ({non_empty} cells)</span>
        </div>
        <div class="comp-body">
            <div class="legend">{legend_html}</div>
            <div class="grid-container">
                <table class="grid-table">{''.join(rows)}</table>
            </div>
        </div>
    </div>'''


# =============================================================================
# Full HTML Generator
# =============================================================================

def generate_resolved_html(data: dict, input_file: str, nav: Optional[NavContext] = None) -> str:
    """Generate complete resolved HTML visualization."""
    table_meta = data.get('table_metadata', {})
    table_id = table_meta.get('table_id', 'unknown')
    table_num = table_meta.get('table_number', '?')
    table_type = table_meta.get('table_type', 'unknown')
    table_title = table_meta.get('table_title', '')
    
    res_meta = data.get('resolution_metadata', {})
    res_status = res_meta.get('resolution_status', 'unknown')
    
    num_props = len(data.get('schedule_properties', []))
    num_acts = len(data.get('activities', []))
    num_cols = len([c for c in data.get('schedule_columns', []) if not c.get('is_label_column')])
    num_annots = len(data.get('annotations', []))
    
    css = f"""
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5; padding: 20px; font-size: 11px;
            max-width: 1600px; margin: 0 auto;
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
            color: {COLORS['header']};
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
            gap: 6px;
        }}
        .nav-btn {{
            padding: 4px 10px;
            background: #f0f0f0;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            font-size: 11px;
        }}
        .nav-btn:hover {{
            background: #e0e0e0;
        }}
        .nav-btn.disabled {{
            color: #ccc;
            cursor: default;
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
        .nav-table-btn.current {{
            background: {COLORS['header']};
            color: white;
        }}
        .nav-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .nav-action {{
            padding: 6px 12px;
            background: #C65911;
            color: white;
            border-radius: 4px;
            text-decoration: none;
            font-size: 11px;
            font-weight: 500;
        }}
        .nav-action:hover {{
            background: #a84a0e;
        }}
        
        .header {{
            background: linear-gradient(135deg, {COLORS['header']} 0%, #2E5EA8 100%);
            color: white; padding: 25px 30px; border-radius: 8px; margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 20px; margin-bottom: 8px; }}
        .header .sub {{ font-size: 12px; opacity: 0.9; margin-bottom: 4px; }}
        .header .meta {{ font-size: 11px; opacity: 0.8; }}
        
        .toolbar {{
            background: white; border-radius: 8px; padding: 10px 20px;
            margin-bottom: 15px; display: flex; gap: 10px; align-items: center;
        }}
        .toolbar button {{
            padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px;
            background: #f5f5f5; cursor: pointer; font-size: 11px;
        }}
        .toolbar button:hover {{ background: #e0e0e0; }}
        .toolbar .source-file {{ margin-left: auto; color: #666; font-size: 10px; }}
        
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
        .comp-title {{ font-weight: bold; font-size: 13px; }}
        .comp-desc {{ font-size: 11px; opacity: 0.9; }}
        .toggle-icon {{ display: inline-block; transition: transform 0.2s; margin-right: 8px; }}
        .comp.collapsed .toggle-icon {{ transform: rotate(-90deg); }}
        .comp-body {{ overflow: hidden; transition: max-height 0.3s; padding: 0; }}
        .comp.collapsed .comp-body {{ max-height: 0 !important; }}
        .comp-note {{ padding: 8px 15px; color: #666; font-size: 10px; border-top: 1px solid #eee; background: #f9f9f9; margin: 0; }}
        
        .comp-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .comp-table th {{
            background: #f5f5f5; padding: 8px 10px; text-align: left;
            font-weight: 600; border-bottom: 2px solid #ddd; white-space: nowrap;
        }}
        .comp-table td {{
            padding: 6px 10px; border-bottom: 1px solid #eee;
            vertical-align: top;
        }}
        .comp-table tr:hover {{ background: #fafafa; }}
        
        .id {{ font-family: 'SF Mono', Monaco, monospace; font-size: 10px; color: {COLORS['header']}; font-weight: bold; }}
        .field {{ font-weight: 600; color: #333; white-space: nowrap; width: 160px; }}
        .type {{ font-size: 10px; color: #666; }}
        .trace {{ color: #999; font-size: 10px; }}
        .comment {{ max-width: 350px; color: #555; }}
        .text-full {{ max-width: 400px; }}
        
        .type-badge {{ color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 500; }}
        .track-label {{ background: #7030A0; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px; }}
        
        .status-ok {{ color: {COLORS['status_ok']}; }}
        .status-warn {{ color: {COLORS['status_warn']}; }}
        .status-fail {{ color: {COLORS['status_fail']}; }}
        
        .level-cell {{ text-align: center; font-weight: bold; min-width: 40px; }}
        .level-num {{ text-align: center; width: 40px; }}
        
        .synth-badge {{ 
            background: #fd7e14; color: white; padding: 1px 4px; border-radius: 3px; 
            font-size: 9px; font-weight: bold; margin-left: 4px;
        }}
        
        .section-header {{ font-weight: bold; }}
        .activity-name {{ max-width: 300px; }}
        

        
        .marker {{ background: #fff3cd; padding: 1px 4px; border-radius: 2px; font-family: monospace; }}
        .marker-cell {{ text-align: center; }}
        
        .annot-section {{ margin-bottom: 15px; }}
        .annot-type-header {{
            color: white; padding: 8px 15px; font-size: 12px; font-weight: bold;
            border-radius: 4px 4px 0 0;
        }}
        .annot-section .comp-table {{ border-radius: 0 0 4px 4px; }}
        
        .legend {{
            padding: 10px 15px; background: #f9f9f9; border-bottom: 1px solid #eee;
            display: flex; gap: 15px; flex-wrap: wrap; font-size: 10px;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 4px; }}
        .legend-color {{ width: 14px; height: 10px; border-radius: 2px; border: 1px solid #ddd; }}
        
        .grid-container {{ overflow-x: auto; padding: 10px; }}
        .grid-table {{ border-collapse: separate; border-spacing: 0; font-size: 10px; }}
        .grid-table th, .grid-table td {{ border: 1px solid #ddd; padding: 3px 5px; }}
        
        .frozen-col {{
            position: sticky; left: 0; z-index: 2;
            min-width: {FROZEN_COL_WIDTH}px; max-width: {FROZEN_COL_WIDTH}px;
            background: #f5f5f5; border-right: 2px solid #999 !important;
        }}
        .grid-table th.frozen-col {{ z-index: 3; }}
        
        .activity-header {{ text-align: left; font-weight: bold; }}
        .activity-cell {{ text-align: left; vertical-align: top; }}
        .prop-row {{ text-align: left; font-size: 10px; }}
        .prop-id, .act-id {{ font-size: 9px; color: #999; font-family: monospace; }}
        .col-header {{ text-align: center; font-size: 9px; background: {COLORS['header']}; color: white; }}
        .prop-cell {{ text-align: center; font-size: 9px; }}
        .schedule-cell {{ text-align: center; font-weight: bold; }}
        .schedule-cell.empty {{ background: #fff; }}
        .cell-marker {{ color: #856404; font-size: 8px; }}
        
        .data.null {{ color: #999; font-style: italic; }}
        .data.bool {{ color: #0066cc; }}
        .data.arr {{ color: #666; }}
    """
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{table_id} - Resolved Table</title>
    <style>{css}</style>
</head>
<body>
    {gen_navigation(nav)}
    <div class="header">
        <h1>Table {table_num}: {esc(table_title) if table_title else table_id}</h1>
        <div class="sub">soa-table-resolved v1.0 | Layer 2 | {table_type}</div>
        <div class="meta">{num_props} properties | {num_acts} activities | {num_cols} columns | {num_annots} annotations</div>
    </div>
    
    <div class="toolbar">
        <button onclick="expandAll()">▼ Expand All</button>
        <button onclick="collapseAll()">▶ Collapse All</button>
        <span class="source-file">Source: {esc(input_file)}</span>
    </div>
    
    {gen_extraction_metadata(data)}
    {gen_resolution_metadata(data)}
    {gen_table_metadata(data)}
    {gen_property_hierarchy(data)}
    {gen_activities_component(data)}
    {gen_annotations_component(data)}
    {gen_schedule_grid(data)}
    
    <script>
        function toggleSection(header) {{
            const comp = header.closest('.comp');
            comp.classList.toggle('collapsed');
        }}
        function expandAll() {{
            document.querySelectorAll('.comp').forEach(c => c.classList.remove('collapsed'));
        }}
        function collapseAll() {{
            document.querySelectorAll('.comp').forEach(c => c.classList.add('collapsed'));
        }}
        // Start with metadata sections collapsed
        document.querySelectorAll('.comp').forEach((c, i) => {{
            if (i < 3) c.classList.add('collapsed');
        }});
    </script>
</body>
</html>'''
    
    return html


# =============================================================================
# Pipeline Step Class
# =============================================================================

class VisualizeResolvedStep(PipelineStepBase):
    """Generate HTML visualization from resolved JSON files (per-table)."""
    
    step_name = "visualize_resolved"
    
    def execute(self, data: dict) -> dict:
        """Execute visualization for all resolved files.
        
        Args:
            data: Must contain 'source' with protocol_id, collection
        
        Returns:
            Dict with input_files, output_files, and per-file results
        """
        source = data.get("source", {})
        protocol_id = source.get("protocol_id")
        collection = source.get("collection")
        
        if not protocol_id or not collection:
            self._log_error("Missing protocol_id or collection in source")
            return {"input_files": [], "output_files": [], "results": []}
        
        # Find resolved files
        resolved_files = config.find_resolved_files(protocol_id, collection)
        
        if not resolved_files:
            self._log_error(
                "No resolved files found",
                {"protocol_id": protocol_id, "collection": collection}
            )
            return {"input_files": [], "output_files": [], "results": []}
        
        self._analytics.record("resolved_files_found", len(resolved_files))
        
        # Build navigation context
        all_tables = []
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
        
        # Check if consolidated exists
        has_consolidated = config.find_consolidated_file(protocol_id, collection) is not None
        
        results = []
        output_files = []
        
        for resolved_file in resolved_files:
            result = self._visualize_file(resolved_file, protocol_id, collection, all_tables, has_consolidated)
            results.append(result)
            
            if result.get("status") == "success":
                output_files.append(result["output_file"])
                self._analytics.increment("files_visualized")
            else:
                self._analytics.increment("files_failed")
        
        return {
            "input_files": [str(f) for f in resolved_files],
            "output_files": output_files,
            "results": results
        }
    
    def _visualize_file(self, input_path: Path, protocol_id: str, collection: str,
                        all_tables: list, has_consolidated: bool) -> dict:
        """Visualize a single resolved file."""
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                resolved_data = json.load(f)
            
            table_meta = resolved_data.get('table_metadata', {})
            table_num = table_meta.get('table_number', 0)
            
            # Build navigation context
            nav = NavContext(
                protocol_id=protocol_id,
                collection=collection,
                current_table_num=table_num,
                all_tables=all_tables,
                has_consolidated=has_consolidated
            )
            
            html = generate_resolved_html(resolved_data, input_path.name, nav)
            
            # Output alongside the JSON file
            output_path = input_path.with_suffix('.html')
            output_path.write_text(html, encoding="utf-8")
            
            return {
                "input": input_path.name,
                "output": output_path.name,
                "output_file": str(output_path),
                "status": "success",
                "table_id": table_meta.get("table_id", ""),
                "activities": len(resolved_data.get("activities", [])),
                "columns": len([c for c in resolved_data.get("schedule_columns", []) 
                               if not c.get("is_label_column")])
            }
        
        except Exception as e:
            self._log_error(str(e), {"file": input_path.name})
            return {
                "input": input_path.name,
                "output": None,
                "status": "failed",
                "error": str(e)
            }
