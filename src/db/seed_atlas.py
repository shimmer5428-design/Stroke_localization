"""Seed database with atlas extraction data (batch JSON files)."""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from .models import (
    get_engine, get_session, AnatomicalLevel, VascularTerritory, Zone,
    Pathway, PathwayZone
)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "atlas_extractions"

# Maps batch region to parent anatomical level
LEVEL_PARENTS = {
    "spinal_cord": None,
    "medulla": None,
    "pons": None,
    "midbrain": None,
    "forebrain": None,
}

BATCH_LEVEL_MAP = {
    1: "spinal_cord",
    2: "medulla",
    3: "pons",
    4: "midbrain",
    5: "forebrain",
}


def _ensure_level(session: Session, name: str, display_name: str = None, parent_name: str = None) -> int:
    obj = session.query(AnatomicalLevel).filter_by(name=name).first()
    if obj:
        return obj.id
    parent_id = None
    if parent_name:
        parent = session.query(AnatomicalLevel).filter_by(name=parent_name).first()
        if parent:
            parent_id = parent.id
    obj = AnatomicalLevel(name=name, display_name=display_name or name, parent_id=parent_id)
    session.add(obj)
    session.flush()
    return obj.id


def _ensure_vascular(session: Session, name: str) -> int:
    if not name:
        return None
    obj = session.query(VascularTerritory).filter_by(name=name).first()
    if obj:
        return obj.id
    lat = None
    if "(L)" in name:
        lat = "L"
    elif "(R)" in name:
        lat = "R"
    elif name in ("ASA", "PSA"):
        lat = "midline"
    obj = VascularTerritory(name=name, laterality=lat)
    session.add(obj)
    session.flush()
    return obj.id


def _ensure_zone(session: Session, name: str, level_id: int, vasc_id: int = None,
                 quadrant: str = None, depth: str = None, lat: str = None) -> int:
    obj = session.query(Zone).filter_by(name=name, anatomical_level_id=level_id).first()
    if obj:
        return obj.id
    obj = Zone(
        name=name, anatomical_level_id=level_id,
        vascular_territory_id=vasc_id, quadrant=quadrant,
        depth=depth, laterality=lat
    )
    session.add(obj)
    session.flush()
    return obj.id


def seed_batch_file(session: Session, batch_file: Path):
    """Seed one batch JSON file."""
    data = json.loads(batch_file.read_text())
    meta = data.get("_metadata", {})
    batch_num = meta.get("batch", 0)
    parent_level_name = BATCH_LEVEL_MAP.get(batch_num, "unknown")

    # Ensure parent level
    parent_level_id = _ensure_level(session, parent_level_name)

    levels = data.get("anatomical_levels", [])
    for level in levels:
        level_id_str = level.get("level_id", "")
        level_name = level.get("level_name", level_id_str)

        # Create sub-level
        sub_level_id = _ensure_level(session, level_id_str, level_name, parent_level_name)

        for tract in level.get("tracts", []):
            clinical_pw = tract.get("clinical_pathway", "")
            if not clinical_pw:
                continue

            vasc_name = tract.get("vascular_territory", "")
            vasc_id = _ensure_vascular(session, vasc_name) if vasc_name else None

            zone_name = tract.get("zone", tract.get("tract_name", ""))
            quadrant = tract.get("quadrant", "")
            depth = tract.get("depth", "")

            zone_id = _ensure_zone(session, zone_name, sub_level_id, vasc_id, quadrant, depth)

            # Find or create pathway
            pw = session.query(Pathway).filter_by(name=clinical_pw).first()
            if not pw:
                # Try matching with laterality variants
                pw = Pathway(name=clinical_pw)
                session.add(pw)
                session.flush()

            # Create pathway-zone mapping
            existing = session.query(PathwayZone).filter_by(
                pathway_id=pw.id, zone_id=zone_id
            ).first()
            if not existing:
                session.add(PathwayZone(
                    pathway_id=pw.id,
                    zone_id=zone_id,
                    quadrant=quadrant,
                    depth=depth,
                    somatotopy_detail=tract.get("somatotopy", ""),
                    confidence="atlas",
                    source=f"Haines 8th, {level.get('figure', '')}",
                ))

    session.flush()
    print(f"  Seeded {batch_file.name}: {len(levels)} levels")


def seed_all_atlas():
    """Seed all batch files."""
    engine = get_engine()
    session = get_session(engine)
    try:
        print("Seeding atlas data...")
        for batch_file in sorted(DATA_DIR.glob("batch*_*.json")):
            if "pathway_zone_mapping" in batch_file.name:
                continue  # Skip mapping-only files, use the main batch files
            seed_batch_file(session, batch_file)
        session.commit()
        print("Atlas seed complete!")
    except Exception as e:
        session.rollback()
        print(f"Atlas seed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_all_atlas()
