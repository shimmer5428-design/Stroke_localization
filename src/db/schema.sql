-- Neuro Localization Database Schema
-- Database: neuro_localization

CREATE TABLE IF NOT EXISTS anatomical_levels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,        -- e.g. 'spinal_cord', 'medulla', 'pons'
    display_name VARCHAR(200),                 -- e.g. '脊髓', '延髓'
    parent_id INTEGER REFERENCES anatomical_levels(id),
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vascular_territories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,         -- e.g. 'MCA(L)', 'PICA(R)', 'ASA'
    display_name VARCHAR(200),
    artery VARCHAR(100),                        -- e.g. 'middle cerebral artery'
    laterality VARCHAR(10) CHECK (laterality IN ('L', 'R', 'bilateral', 'midline'))
);

CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,                -- e.g. 'lateral_medulla_L', 'pyramid_R'
    display_name VARCHAR(300),
    anatomical_level_id INTEGER NOT NULL REFERENCES anatomical_levels(id),
    vascular_territory_id INTEGER REFERENCES vascular_territories(id),
    quadrant VARCHAR(50),                       -- dorsal/ventral/lateral/medial combinations
    depth VARCHAR(30),                          -- surface, superficial, mid, deep
    laterality VARCHAR(10) CHECK (laterality IN ('L', 'R', 'bilateral', 'midline')),
    description TEXT,
    UNIQUE(name, anatomical_level_id)
);

CREATE TABLE IF NOT EXISTS pathways (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,         -- clinical name: 'motor-corticospinal tract(L)-hand>leg'
    canonical_name VARCHAR(200),                -- atlas name: 'lateral corticospinal tract'
    modality VARCHAR(30) CHECK (modality IN ('motor', 'sensory', 'autonomic', 'special_sense', 'mixed', 'other')),
    laterality VARCHAR(10) CHECK (laterality IN ('L', 'R', 'bilateral')),
    crosses_midline BOOLEAN DEFAULT FALSE,
    crossing_level VARCHAR(100),                -- e.g. 'pyramidal decussation', 'medulla'
    somatotopy_note TEXT,                       -- e.g. 'hand fibers medial, leg fibers lateral in lateral CST'
    description TEXT
);

CREATE TABLE IF NOT EXISTS pathway_zones (
    id SERIAL PRIMARY KEY,
    pathway_id INTEGER NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    zone_id INTEGER NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    quadrant VARCHAR(50),
    depth VARCHAR(30),
    somatotopy_detail TEXT,
    confidence VARCHAR(20) DEFAULT 'atlas' CHECK (confidence IN ('atlas', 'textbook', 'inferred', 'legacy')),
    source VARCHAR(100),                        -- e.g. 'Haines 8th, Fig 6-1A'
    UNIQUE(pathway_id, zone_id)
);

-- Legacy 29-region binary system (for backward compatibility)
CREATE TABLE IF NOT EXISTS legacy_regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE           -- e.g. 'MCA territory(L)', 'pons(L)-SCA'
);

CREATE TABLE IF NOT EXISTS pathway_legacy_regions (
    id SERIAL PRIMARY KEY,
    pathway_id INTEGER NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    legacy_region_id INTEGER NOT NULL REFERENCES legacy_regions(id) ON DELETE CASCADE,
    present BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(pathway_id, legacy_region_id)
);

CREATE TABLE IF NOT EXISTS symptoms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL UNIQUE,
    category VARCHAR(50),                       -- 'cranial_nerve', 'motor', 'sensory', 'cerebellar', 'visual', 'other'
    subcategory VARCHAR(100),                   -- e.g. 'CN5', 'hemiparesis'
    laterality VARCHAR(10) CHECK (laterality IN ('L', 'R', 'bilateral', NULL)),
    description TEXT
);

CREATE TABLE IF NOT EXISTS symptom_pathway_mappings (
    id SERIAL PRIMARY KEY,
    symptom_id INTEGER NOT NULL REFERENCES symptoms(id) ON DELETE CASCADE,
    pathway_id INTEGER NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT TRUE,            -- pathway1 = primary, pathway2 = secondary
    UNIQUE(symptom_id, pathway_id)
);

CREATE TABLE IF NOT EXISTS clinical_syndromes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,          -- e.g. 'Wallenberg syndrome'
    display_name VARCHAR(300),
    description TEXT,
    typical_vascular_territory VARCHAR(200),     -- e.g. 'PICA'
    anatomical_level VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS syndrome_zones (
    id SERIAL PRIMARY KEY,
    syndrome_id INTEGER NOT NULL REFERENCES clinical_syndromes(id) ON DELETE CASCADE,
    zone_id INTEGER NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    UNIQUE(syndrome_id, zone_id)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_zones_level ON zones(anatomical_level_id);
CREATE INDEX IF NOT EXISTS idx_zones_vascular ON zones(vascular_territory_id);
CREATE INDEX IF NOT EXISTS idx_pathway_zones_pathway ON pathway_zones(pathway_id);
CREATE INDEX IF NOT EXISTS idx_pathway_zones_zone ON pathway_zones(zone_id);
CREATE INDEX IF NOT EXISTS idx_symptom_pathway ON symptom_pathway_mappings(symptom_id);
CREATE INDEX IF NOT EXISTS idx_pathway_legacy ON pathway_legacy_regions(pathway_id);
