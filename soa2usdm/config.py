"""
SoA2USDM Configuration

Paths, constants, and discovery functions.
All paths relative to the repository root (parent of this package folder).
"""

import os
from pathlib import Path

# =============================================================================
# Base Paths — relative to repo root
# =============================================================================

PKG_DIR = Path(__file__).parent
REPO_ROOT = PKG_DIR.parent  # soa2usdm/ package is at repo root

# Protocol collections live in a separate repo (soa2usdm-collections).
# Default: sibling checkout. Override with SOA2USDM_COLLECTIONS env var.
COLLECTIONS_ROOT = Path(os.environ.get(
    "SOA2USDM_COLLECTIONS",
    REPO_ROOT.parent / "soa2usdm-collections" / "collections",
))

# Regression fixtures ship with this repo — tests run on a fresh clone
# with no collections checkout present.
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"

# Discover collections: every COLLECTIONS_ROOT subfolder with a protocols/ dir.
COLLECTIONS = {
    d.name: d / "protocols"
    for d in (sorted(COLLECTIONS_ROOT.iterdir()) if COLLECTIONS_ROOT.is_dir() else [])
    if d.is_dir() and (d / "protocols").is_dir()
}
COLLECTIONS["fixtures"] = FIXTURES_ROOT / "protocols"

# Default collection: first discovered real collection, else the fixtures.
DEFAULT_COLLECTION = next((c for c in COLLECTIONS if c != "fixtures"), "fixtures")

# Schema locations
SCHEMAS_DIR = PKG_DIR.parent / "schemas"
EXTRACTION_SCHEMA = SCHEMAS_DIR / "soa-table-extraction.schema.json"
RESOLVED_SCHEMA = SCHEMAS_DIR / "soa-table-resolved.schema.json"
CONSOLIDATED_SCHEMA = SCHEMAS_DIR / "soa-tables-consolidated.schema.json"
CORRECTIONS_SCHEMA = SCHEMAS_DIR / "soa-table-corrections.schema.json"


# =============================================================================
# Path Discovery Functions
# =============================================================================

def get_collection_path(collection: str) -> Path:
    """Get path for a collection name."""
    if collection not in COLLECTIONS:
        valid = ", ".join(COLLECTIONS.keys())
        raise ValueError(f"Unknown collection '{collection}'. Valid: {valid}")
    return COLLECTIONS[collection]


def get_collection_root(collection: str) -> Path:
    """Get the root folder of a collection (parent of protocols/)."""
    return get_collection_path(collection).parent


def get_protocol_path(protocol_id: str, collection: str) -> Path:
    """Get path to a specific protocol folder."""
    collection_path = get_collection_path(collection)
    protocol_path = collection_path / protocol_id
    if not protocol_path.exists():
        raise FileNotFoundError(f"Protocol not found: {protocol_path}")
    return protocol_path


def get_soa2usdm_folder(protocol_id: str, collection: str) -> Path:
    """Get the SoA2USDM folder for a protocol."""
    protocol_path = get_protocol_path(protocol_id, collection)
    soa_folder = protocol_path / "SoA2USDM"
    if not soa_folder.exists():
        raise FileNotFoundError(f"SoA2USDM folder not found: {soa_folder}")
    return soa_folder


def get_extracted_dir(protocol_id: str, collection: str) -> Path:
    """Get the extracted directory for a protocol."""
    return get_soa2usdm_folder(protocol_id, collection) / "extracted"


def get_resolved_dir(protocol_id: str, collection: str) -> Path:
    """Get the resolved directory for a protocol."""
    return get_soa2usdm_folder(protocol_id, collection) / "resolved"


def get_consolidated_dir(protocol_id: str, collection: str) -> Path:
    """Get the consolidated directory for a protocol."""
    return get_soa2usdm_folder(protocol_id, collection) / "consolidated"


def get_visualized_dir(protocol_id: str, collection: str) -> Path:
    """Get the visualized directory for a protocol."""
    return get_soa2usdm_folder(protocol_id, collection) / "visualized"


def find_extraction_files(protocol_id: str, collection: str) -> list[Path]:
    """Find extraction JSON files for a protocol.

    Prefers the verified extraction (raw + corrections applied,
    `*_extraction.verified.json`) when present; otherwise the raw
    `*_extraction.json`. The raw file is never returned when a verified
    sibling exists, so downstream always consumes the corrected data.
    """
    try:
        extracted_dir = get_extracted_dir(protocol_id, collection)
    except FileNotFoundError:
        return []
    if not extracted_dir.exists():
        return []
    files = []
    for raw in sorted(extracted_dir.glob("*_extraction.json")):
        verified = raw.with_name(raw.stem + ".verified.json")
        files.append(verified if verified.exists() else raw)
    return files


def find_resolved_files(protocol_id: str, collection: str) -> list[Path]:
    """Find all resolved JSON files for a protocol."""
    try:
        resolved_dir = get_resolved_dir(protocol_id, collection)
    except FileNotFoundError:
        return []
    if not resolved_dir.exists():
        return []
    return sorted(resolved_dir.glob("*_resolved.json"))


def find_consolidated_file(protocol_id: str, collection: str) -> Path | None:
    """Find the consolidated JSON file for a protocol."""
    try:
        consolidated_dir = get_consolidated_dir(protocol_id, collection)
    except FileNotFoundError:
        return None
    if not consolidated_dir.exists():
        return None
    consolidated_file = consolidated_dir / f"{protocol_id}_consolidated.json"
    if consolidated_file.exists():
        return consolidated_file
    return None


# =============================================================================
# Utility Functions
# =============================================================================

def extraction_to_resolved_filename(extraction_filename: str) -> str:
    """Convert extraction filename (raw or verified) to resolved filename.

    Both `X_extraction.json` and `X_extraction.verified.json` map to
    `X_resolved.json`, so a corrected table's resolved output keeps the
    canonical name.
    """
    return (extraction_filename
            .replace("_extraction.verified.json", "_resolved.json")
            .replace("_extraction.json", "_resolved.json"))


def list_protocols(collection: str) -> list[str]:
    """List all protocol IDs in a collection."""
    collection_path = get_collection_path(collection)
    if not collection_path.exists():
        return []
    protocols = [
        d.name for d in collection_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    return sorted(protocols)


def list_extractable_protocols(collection: str) -> list[str]:
    """List protocols that have extraction files ready for the full pipeline."""
    return [
        p for p in list_protocols(collection)
        if find_extraction_files(p, collection)
    ]


def list_ready_protocols(collection: str) -> list[str]:
    """List protocols that have resolved files ready for processing."""
    return [
        p for p in list_protocols(collection)
        if find_resolved_files(p, collection)
    ]
