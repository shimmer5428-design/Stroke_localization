"""SQLAlchemy 2.0 ORM models for neuro_localization database."""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey, UniqueConstraint,
    create_engine, CheckConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = "postgresql://localhost/neuro_localization"


class Base(DeclarativeBase):
    pass


class AnatomicalLevel(Base):
    __tablename__ = "anatomical_levels"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200))
    parent_id = Column(Integer, ForeignKey("anatomical_levels.id"))
    sort_order = Column(Integer, default=0)

    parent = relationship("AnatomicalLevel", remote_side=[id])
    zones = relationship("Zone", back_populates="anatomical_level")


class VascularTerritory(Base):
    __tablename__ = "vascular_territories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200))
    artery = Column(String(100))
    laterality = Column(String(10))

    zones = relationship("Zone", back_populates="vascular_territory")


class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    display_name = Column(String(300))
    anatomical_level_id = Column(Integer, ForeignKey("anatomical_levels.id"), nullable=False)
    vascular_territory_id = Column(Integer, ForeignKey("vascular_territories.id"))
    quadrant = Column(String(50))
    depth = Column(String(30))
    laterality = Column(String(10))
    description = Column(Text)

    anatomical_level = relationship("AnatomicalLevel", back_populates="zones")
    vascular_territory = relationship("VascularTerritory", back_populates="zones")
    pathway_zones = relationship("PathwayZone", back_populates="zone")

    __table_args__ = (UniqueConstraint("name", "anatomical_level_id"),)


class Pathway(Base):
    __tablename__ = "pathways"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    canonical_name = Column(String(200))
    modality = Column(String(30))
    laterality = Column(String(10))
    crosses_midline = Column(Boolean, default=False)
    crossing_level = Column(String(100))
    somatotopy_note = Column(Text)
    description = Column(Text)

    pathway_zones = relationship("PathwayZone", back_populates="pathway")
    legacy_regions = relationship("PathwayLegacyRegion", back_populates="pathway")
    symptom_mappings = relationship("SymptomPathwayMapping", back_populates="pathway")


class PathwayZone(Base):
    __tablename__ = "pathway_zones"
    id = Column(Integer, primary_key=True)
    pathway_id = Column(Integer, ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    quadrant = Column(String(50))
    depth = Column(String(30))
    somatotopy_detail = Column(Text)
    confidence = Column(String(20), default="atlas")
    source = Column(String(100))

    pathway = relationship("Pathway", back_populates="pathway_zones")
    zone = relationship("Zone", back_populates="pathway_zones")

    __table_args__ = (UniqueConstraint("pathway_id", "zone_id"),)


class LegacyRegion(Base):
    __tablename__ = "legacy_regions"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)


class PathwayLegacyRegion(Base):
    __tablename__ = "pathway_legacy_regions"
    id = Column(Integer, primary_key=True)
    pathway_id = Column(Integer, ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    legacy_region_id = Column(Integer, ForeignKey("legacy_regions.id", ondelete="CASCADE"), nullable=False)
    present = Column(Boolean, default=True, nullable=False)

    pathway = relationship("Pathway", back_populates="legacy_regions")
    legacy_region = relationship("LegacyRegion")

    __table_args__ = (UniqueConstraint("pathway_id", "legacy_region_id"),)


class Symptom(Base):
    __tablename__ = "symptoms"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), unique=True, nullable=False)
    category = Column(String(50))
    subcategory = Column(String(100))
    laterality = Column(String(10))
    description = Column(Text)

    pathway_mappings = relationship("SymptomPathwayMapping", back_populates="symptom")


class SymptomPathwayMapping(Base):
    __tablename__ = "symptom_pathway_mappings"
    id = Column(Integer, primary_key=True)
    symptom_id = Column(Integer, ForeignKey("symptoms.id", ondelete="CASCADE"), nullable=False)
    pathway_id = Column(Integer, ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=True)

    symptom = relationship("Symptom", back_populates="pathway_mappings")
    pathway = relationship("Pathway", back_populates="symptom_mappings")

    __table_args__ = (UniqueConstraint("symptom_id", "pathway_id"),)


class ClinicalSyndrome(Base):
    __tablename__ = "clinical_syndromes"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    display_name = Column(String(300))
    description = Column(Text)
    typical_vascular_territory = Column(String(200))
    anatomical_level = Column(String(100))

    syndrome_zones = relationship("SyndromeZone", back_populates="syndrome")


class SyndromeZone(Base):
    __tablename__ = "syndrome_zones"
    id = Column(Integer, primary_key=True)
    syndrome_id = Column(Integer, ForeignKey("clinical_syndromes.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)

    syndrome = relationship("ClinicalSyndrome", back_populates="syndrome_zones")
    zone = relationship("Zone")

    __table_args__ = (UniqueConstraint("syndrome_id", "zone_id"),)


def get_engine(url=None):
    return create_engine(url or DATABASE_URL)


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
