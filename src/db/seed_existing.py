"""Seed database with existing data from JSON files."""
import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from .models import (
    get_engine, get_session, AnatomicalLevel, VascularTerritory, Zone,
    Pathway, PathwayZone, LegacyRegion, PathwayLegacyRegion,
    Symptom, SymptomPathwayMapping
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def classify_symptom(name: str) -> tuple[str, str, str | None]:
    """Return (category, subcategory, laterality) for a symptom."""
    lower = name.lower()
    lat = None
    if " l " in f" {lower} " or lower.endswith(" l") or "(l)" in lower or "left" in lower:
        lat = "L"
    elif " r " in f" {lower} " or lower.endswith(" r") or "(r)" in lower or "right" in lower:
        lat = "R"

    cn_match = re.match(r"CN(\d+)", name)
    if cn_match:
        return "cranial_nerve", f"CN{cn_match.group(1)}", lat
    if "hemiparesis" in lower or "hemiparalysis" in lower:
        return "motor", "hemiparesis", lat
    if "hypoesthesia" in lower:
        return "sensory", "hypoesthesia", lat
    if "fnf" in lower or "heel" in lower or "ataxia" in lower or "vertigo" in lower:
        return "cerebellar", "ataxia", lat
    if "eye" in lower or "rapd" in lower or "hemianopia" in lower or "quadrant" in lower:
        return "visual", "visual_field", lat
    if "conjugate" in lower or "mlf" in lower:
        return "cranial_nerve", "gaze", lat
    if "distal fine" in lower:
        return "motor", "fine_movement", lat
    if "aphasia" in lower:
        return "other", "language", None
    if "aprasia" in lower or "apraxia" in lower:
        return "other", "praxis", None
    if "personality" in lower:
        return "other", "personality", None
    if "incontinence" in lower:
        return "other", "autonomic", None
    if "consciousness" in lower:
        return "other", "consciousness", None
    if "ptosis" in lower:
        return "cranial_nerve", "ptosis", lat
    return "other", "other", lat


def classify_pathway(name: str) -> tuple[str, str | None]:
    """Return (modality, laterality) for a pathway."""
    lower = name.lower()
    lat = None
    if "(l)" in lower:
        lat = "L"
    elif "(r)" in lower:
        lat = "R"

    if lower.startswith("motor") or "corticospinal" in lower or "corticobulbar" in lower or "rubrospinal" in lower:
        return "motor", lat
    if lower.startswith("sensory") or "lemniscus" in lower or "spinothalamic" in lower:
        return "sensory", lat
    if "sympathetic" in lower:
        return "autonomic", lat
    if "auditory" in lower or "taste" in lower:
        return "special_sense", lat
    if "ataxia" in lower or "cerebell" in lower:
        return "motor", lat
    if "eye" in lower or "ew nucleus" in lower:
        return "special_sense", lat
    return "other", lat


def seed_legacy_regions(session: Session):
    """Seed the 29 legacy regions."""
    data = json.loads((DATA_DIR / "existing" / "pathway_locations.json").read_text())
    regions = data["regions"]
    for r in regions:
        session.merge(LegacyRegion(name=r))
    session.flush()
    print(f"  Seeded {len(regions)} legacy regions")
    return {r.name: r.id for r in session.query(LegacyRegion).all()}


def seed_pathways_and_legacy(session: Session, region_map: dict):
    """Seed pathways and their legacy region mappings."""
    data = json.loads((DATA_DIR / "existing" / "pathway_locations.json").read_text())
    regions = data["regions"]
    pathway_map = {}

    for pw_name, bits in data["pathways"].items():
        modality, lat = classify_pathway(pw_name)
        pw = Pathway(
            name=pw_name,
            modality=modality,
            laterality=lat,
            crosses_midline="corticospinal" in pw_name.lower() or "lemniscus" in pw_name.lower(),
        )
        session.merge(pw)
        session.flush()

        pw_obj = session.query(Pathway).filter_by(name=pw_name).one()
        pathway_map[pw_name] = pw_obj.id

        for i, bit in enumerate(bits):
            if bit == 1:
                region_id = region_map[regions[i]]
                existing = session.query(PathwayLegacyRegion).filter_by(
                    pathway_id=pw_obj.id, legacy_region_id=region_id
                ).first()
                if not existing:
                    session.add(PathwayLegacyRegion(
                        pathway_id=pw_obj.id,
                        legacy_region_id=region_id,
                        present=True
                    ))

    session.flush()
    print(f"  Seeded {len(pathway_map)} pathways with legacy region mappings")
    return pathway_map


def seed_symptoms(session: Session, pathway_map: dict):
    """Seed symptoms and their pathway mappings."""
    symptoms = json.loads((DATA_DIR / "existing" / "symptoms.json").read_text())

    for s in symptoms:
        cat, subcat, lat = classify_symptom(s["symptom"])
        sym = Symptom(name=s["symptom"], category=cat, subcategory=subcat, laterality=lat)
        session.merge(sym)
        session.flush()

        sym_obj = session.query(Symptom).filter_by(name=s["symptom"]).one()

        for key, is_primary in [("pathway1", True), ("pathway2", False)]:
            pw_name = s.get(key)
            if pw_name and pw_name in pathway_map:
                existing = session.query(SymptomPathwayMapping).filter_by(
                    symptom_id=sym_obj.id, pathway_id=pathway_map[pw_name]
                ).first()
                if not existing:
                    session.add(SymptomPathwayMapping(
                        symptom_id=sym_obj.id,
                        pathway_id=pathway_map[pw_name],
                        is_primary=is_primary
                    ))
            elif pw_name:
                # Pathway not in pathway_locations.json, create it
                modality, lat = classify_pathway(pw_name)
                pw = Pathway(name=pw_name, modality=modality, laterality=lat)
                session.merge(pw)
                session.flush()
                pw_obj = session.query(Pathway).filter_by(name=pw_name).one()
                pathway_map[pw_name] = pw_obj.id
                session.add(SymptomPathwayMapping(
                    symptom_id=sym_obj.id,
                    pathway_id=pw_obj.id,
                    is_primary=is_primary
                ))

    session.flush()
    print(f"  Seeded {len(symptoms)} symptoms with pathway mappings")


def seed_all():
    """Run complete seed process."""
    engine = get_engine()
    session = get_session(engine)
    try:
        print("Seeding existing data...")
        region_map = seed_legacy_regions(session)
        pathway_map = seed_pathways_and_legacy(session, region_map)
        seed_symptoms(session, pathway_map)
        session.commit()
        print("Seed complete!")
    except Exception as e:
        session.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_all()
