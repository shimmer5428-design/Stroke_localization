"""Core analysis engine — atlas-based pathway intersection localization."""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ATLAS_DIR = DATA_DIR / "atlas_extractions"

# Levels to exclude (summary/overview figures, not real cross-sections)
_EXCLUDED_LEVEL_KEYWORDS = [
    "Overview", "Territory Diagram", "Territory Map", "Sagittal Context",
]

# Regex to parse lateralized+somatotopy pathway names from symptoms.json
# e.g. "motor-corticospinal tract(R)-hand>leg" → base="motor-corticospinal tract", lat="R", soma="hand>leg"
# Also handles edge case: "sensory-ant spinothalamic tract(L)Hand>leg" (no dash before somatotopy)
_PW_PATTERN = re.compile(r'^(.+?)\(([LR])\)[-]?(.*)$')

# Region ordering for display (anatomically rostral→caudal is reversed here:
# spinal cord is most caudal, forebrain most rostral, but we display rostral first)
REGION_ORDER = {
    "Forebrain": 0,
    "Midbrain": 1,
    "Pons": 2,
    "Medulla Oblongata": 3,
    "Medulla": 3,
    "Spinal Cord": 4,
}

# Manual aliases for symptom bases that don't directly match atlas clinical_pathway
_MANUAL_ALIASES = {
    "sensory-Auditory pathway": [
        "auditory", "auditory pathway (cochlear nuclei)", "auditory relay",
        "auditory relay (IC to MGN)", "auditory relay (IC-MGN-auditory cortex)",
        "auditory relay (binaural integration)",
        "auditory relay — inferior colliculus → MGN → auditory cortex (Heschl gyri)",
    ],
    "eye-Light Reflex negative": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "pupillary light reflex pathway (pretectal nuclei coordination); damage → Argyll Robertson pupil / Parinaud",
        "EW nucleus", "EW nucleus + pupillary light reflex arc",
    ],
    "eye-RAPD positive": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "visual pathway", "visual pathway relay",
    ],
    "eye field-Bitemporal/nasal hemianopia": [
        "visual pathway", "visual pathway relay",
        "visual pathway — chiasm lesion: bitemporal hemianopia; optic tract: contralateral homonymous hemianopia",
    ],
    "eye field-Left homonymous hemianopia": [
        "visual pathway", "visual pathway relay",
        "optic radiation (visual pathway)",
        "optic tract/radiation (visual pathway); posterior thalamic radiation (somesthetic)",
        "optic tract/radiation — contralateral homonymous hemianopia if damaged",
        "optic tract/radiation — visual field deficits map predictably to lesion location",
        "optic tract/radiation — visual relay; optic tract → LGN → optic radiation → V1",
        "visual pathway — contralateral homonymous hemianopia with complete lesion",
        "optic radiation — LGN to primary visual cortex (V1 at calcarine sulcus); hemianopia / quadrantanopia depending on lesion location",
    ],
    "eye field-Right homonymous hemianopia": [
        "visual pathway", "visual pathway relay",
        "optic radiation (visual pathway)",
        "optic tract/radiation (visual pathway); posterior thalamic radiation (somesthetic)",
        "optic tract/radiation — contralateral homonymous hemianopia if damaged",
        "optic tract/radiation — visual field deficits map predictably to lesion location",
        "optic tract/radiation — visual relay; optic tract → LGN → optic radiation → V1",
        "visual pathway — contralateral homonymous hemianopia with complete lesion",
        "optic radiation — LGN to primary visual cortex (V1 at calcarine sulcus); hemianopia / quadrantanopia depending on lesion location",
    ],
    "eye field-Left superior homonymous quadrantanopia": [
        "optic radiation (visual pathway)",
        "optic radiation — Meyer loop carries superior visual field information; anterior temporal lobectomy → contralateral superior quadrantanopia ('pie in the sky')",
        "optic radiation — LGN to primary visual cortex (V1 at calcarine sulcus); hemianopia / quadrantanopia depending on lesion location",
    ],
    "eye field-Right superior homonymous quadrantanopia": [
        "optic radiation (visual pathway)",
        "optic radiation — Meyer loop carries superior visual field information; anterior temporal lobectomy → contralateral superior quadrantanopia ('pie in the sky')",
        "optic radiation — LGN to primary visual cortex (V1 at calcarine sulcus); hemianopia / quadrantanopia depending on lesion location",
    ],
    "eye field-left eye blind": [
        "visual pathway", "visual pathway relay",
        "visual pathway — chiasm lesion: bitemporal hemianopia; optic tract: contralateral homonymous hemianopia",
    ],
    "eye field-right eye blind": [
        "visual pathway", "visual pathway relay",
        "visual pathway — chiasm lesion: bitemporal hemianopia; optic tract: contralateral homonymous hemianopia",
    ],
    # These use "L"/"R" as suffix without parentheses
    "eye-Light Reflex negative L": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "pupillary light reflex pathway (pretectal nuclei coordination); damage → Argyll Robertson pupil / Parinaud",
        "EW nucleus", "EW nucleus + pupillary light reflex arc",
    ],
    "eye-Light Reflex negative R": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "pupillary light reflex pathway (pretectal nuclei coordination); damage → Argyll Robertson pupil / Parinaud",
        "EW nucleus", "EW nucleus + pupillary light reflex arc",
    ],
    "eye-RAPD positive L": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "visual pathway", "visual pathway relay",
    ],
    "eye-RAPD positive R": [
        "pupillary light reflex arc", "pupillary light reflex (consensual limb)",
        "pupillary light reflex (consensual)",
        "visual pathway", "visual pathway relay",
    ],
}

# Cortical/clinical pathways with no atlas tract representation
_CORTICAL_PATHWAYS = {
    "Aphasia", "Aprasia", "Incontinence", "Personality change",
}


@dataclass
class ZoneEntry:
    """One tract record from the atlas at a specific anatomical level."""
    level_name: str
    level_id: str
    region: str  # e.g. "Spinal Cord", "Medulla Oblongata"
    zone: str
    quadrant: str
    depth: str
    somatotopy: str
    vascular_territory: str
    clinical_pathway: str  # the original atlas clinical_pathway value


@dataclass
class ParsedPathway:
    """A parsed symptom pathway name."""
    raw: str
    base: str
    laterality: str | None  # "L", "R", or None
    somatotopy: str | None  # e.g. "hand>leg", "3,4", "intercaudalis-polaris"


class LocalizationAnalyzer:
    """Analyzes NE findings to localize stroke via atlas-based pathway intersection."""

    def __init__(self):
        self._symptoms = self._load_json("existing/symptoms.json")
        # atlas clinical_pathway → list of ZoneEntry
        self._zone_index: dict[str, list[ZoneEntry]] = {}
        # symptom base_name (lowercase) → list of atlas clinical_pathway strings
        self._base_to_atlas: dict[str, list[str]] = {}

        self._build_zone_index()
        self._build_pathway_mapping()

    # ------------------------------------------------------------------ #
    #  Data loading
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_json(rel_path: str):
        p = DATA_DIR / rel_path
        if p.exists():
            return json.loads(p.read_text())
        return {}

    def _build_zone_index(self):
        """Load all atlas batch JSONs and index by clinical_pathway."""
        for batch_file in sorted(ATLAS_DIR.glob("batch[0-9]_*.json")):
            if "pathway_zone_mapping" in batch_file.name:
                continue
            data = json.loads(batch_file.read_text())
            region = data.get("_metadata", {}).get("region", "Unknown")
            for level in data.get("anatomical_levels", []):
                level_name = level.get("level_name", "")
                level_id = level.get("level_id", "")

                # Skip overview/summary levels
                if any(kw.lower() in level_name.lower() for kw in _EXCLUDED_LEVEL_KEYWORDS):
                    continue

                for tract in level.get("tracts", []):
                    cp = (tract.get("clinical_pathway") or "").strip()
                    if not cp:
                        continue

                    entry = ZoneEntry(
                        level_name=level_name,
                        level_id=level_id,
                        region=region,
                        zone=tract.get("zone", ""),
                        quadrant=tract.get("quadrant", ""),
                        depth=tract.get("depth", ""),
                        somatotopy=tract.get("somatotopy", ""),
                        vascular_territory=tract.get("vascular_territory", ""),
                        clinical_pathway=cp,
                    )
                    self._zone_index.setdefault(cp, []).append(entry)

    def _build_pathway_mapping(self):
        """Build mapping from symptom base names → matching atlas clinical_pathway keys."""
        # Collect all unique base names from symptoms.json
        bases: set[str] = set()
        for s in self._symptoms:
            for key in ("pathway1", "pathway2"):
                raw = (s.get(key) or "").strip()
                if raw:
                    parsed = self._parse_pathway(raw)
                    bases.add(parsed.base)

        atlas_keys = list(self._zone_index.keys())

        for base in bases:
            bl = base.lower()

            # Check manual aliases first
            if base in _MANUAL_ALIASES:
                # Filter to aliases that actually exist in atlas
                matched = [a for a in _MANUAL_ALIASES[base] if a in self._zone_index]
                if matched:
                    self._base_to_atlas[bl] = matched
                continue

            # Check if it's a known cortical pathway
            if base in _CORTICAL_PATHWAYS:
                continue  # No atlas mapping

            # Auto-match against atlas keys
            matched = []
            for acp in atlas_keys:
                al = acp.lower()

                # Exact match
                if bl == al:
                    matched.append(acp)
                    continue

                # Prefix match (atlas key starts with base)
                if al.startswith(bl):
                    matched.append(acp)
                    continue

                # Compound match: atlas key like "A + B + C" where base matches a component
                if " + " in acp:
                    parts = [p.strip() for p in acp.split("+")]
                    for part in parts:
                        pl = part.lower()
                        if bl == pl or pl.startswith(bl):
                            matched.append(acp)
                            break

            if matched:
                self._base_to_atlas[bl] = matched

    # ------------------------------------------------------------------ #
    #  Parsing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_pathway(raw_name: str) -> ParsedPathway:
        """Parse a symptom pathway name into components."""
        m = _PW_PATTERN.match(raw_name)
        if m:
            base = m.group(1).rstrip("-")
            lat = m.group(2)
            soma = m.group(3).strip("-").strip() or None
            return ParsedPathway(raw=raw_name, base=base, laterality=lat, somatotopy=soma)
        return ParsedPathway(raw=raw_name, base=raw_name, laterality=None, somatotopy=None)

    # ------------------------------------------------------------------ #
    #  Core algorithm
    # ------------------------------------------------------------------ #

    def analyze(self, checked_symptoms: list[dict]) -> dict:
        """
        Run atlas-based localization analysis.

        Args:
            checked_symptoms: list of symptom dicts with 'symptom', 'pathway1', 'pathway2'

        Returns:
            {
                "active_pathways": list[dict],
                "intersection_details": list[dict],
                "near_miss": list[dict],
                "unmapped_pathways": list[str],
                "warnings": list[str],
            }
        """
        # 1. Collect unique parsed pathways
        seen = set()
        parsed_pathways: list[ParsedPathway] = []
        for s in checked_symptoms:
            for key in ("pathway1", "pathway2"):
                raw = (s.get(key) or "").strip()
                if raw and raw not in seen:
                    seen.add(raw)
                    parsed_pathways.append(self._parse_pathway(raw))

        if not parsed_pathways:
            return {
                "active_pathways": [],
                "intersection_details": [],
                "near_miss": [],
                "unmapped_pathways": [],
                "warnings": [],
            }

        # 2. Resolve each pathway to atlas zone levels
        active_pathways = []
        zone_sets: list[set[str]] = []  # level_name sets for intersection
        unmapped = []

        for pp in parsed_pathways:
            levels, matched_atlas, is_mapped = self._resolve_zones(pp)
            pw_info = {
                "raw_name": pp.raw,
                "base_name": pp.base,
                "laterality": pp.laterality,
                "somatotopy": pp.somatotopy,
                "matched_atlas_pathways": matched_atlas,
                "zone_levels": levels,
                "is_mapped": is_mapped,
            }
            active_pathways.append(pw_info)

            if is_mapped and levels:
                zone_sets.append(set(levels))
            elif not is_mapped:
                unmapped.append(pp.raw)

        # 3. Compute intersection
        intersection_levels = self._compute_intersection(zone_sets)

        # 4. Enrich intersection with details
        intersection_details = self._enrich_intersection(intersection_levels, parsed_pathways)

        # 5. Compute near-miss if intersection is empty
        near_miss = []
        if not intersection_levels and len(zone_sets) >= 2:
            near_miss = self._compute_near_miss(zone_sets, threshold=1)

        # 6. Generate warnings
        pathway_names = [pp.raw for pp in parsed_pathways]
        warnings = self._generate_warnings(pathway_names, intersection_details)

        return {
            "active_pathways": active_pathways,
            "intersection_details": intersection_details,
            "near_miss": near_miss,
            "unmapped_pathways": unmapped,
            "warnings": warnings,
        }

    def _resolve_zones(self, pp: ParsedPathway) -> tuple[list[str], list[str], bool]:
        """Resolve a parsed pathway to atlas zone levels.

        Returns:
            (level_names, matched_atlas_pathways, is_mapped)
        """
        bl = pp.base.lower()

        # Check if cortical/unmapped
        if pp.base in _CORTICAL_PATHWAYS:
            return [], [], False

        # Check manual aliases (already lowercased in _base_to_atlas)
        atlas_matches = self._base_to_atlas.get(bl, [])

        if not atlas_matches:
            return [], [], False

        # If somatotopy specified, check if there are somatotopy-specific atlas entries
        levels = set()
        used_atlas = []

        if pp.somatotopy:
            # Try to find somatotopy-specific atlas entries first
            soma_lower = pp.somatotopy.lower()
            specific_matches = []
            generic_matches = []

            for acp in atlas_matches:
                al = acp.lower()
                base_lower = pp.base.lower()
                # Check if atlas entry contains the somatotopy suffix
                if soma_lower in al:
                    specific_matches.append(acp)
                elif al.startswith(base_lower):
                    generic_matches.append(acp)
                else:
                    generic_matches.append(acp)

            # Use specific if available, otherwise use all matches
            use_matches = specific_matches if specific_matches else atlas_matches
        else:
            use_matches = atlas_matches

        for acp in use_matches:
            entries = self._zone_index.get(acp, [])
            if entries:
                used_atlas.append(acp)
                for e in entries:
                    levels.add(e.level_name)

        return sorted(levels), used_atlas, True

    def _compute_intersection(self, zone_sets: list[set[str]]) -> list[str]:
        """Compute intersection of all zone sets."""
        if not zone_sets:
            return []
        result = set(zone_sets[0])
        for s in zone_sets[1:]:
            result &= s
        return self._sort_levels(list(result))

    def _compute_near_miss(self, zone_sets: list[set[str]], threshold: int = 1) -> list[dict]:
        """Find levels that appear in at least (N - threshold) of N pathway sets."""
        n = len(zone_sets)
        if n < 2:
            return []

        counter = Counter()
        for s in zone_sets:
            for level in s:
                counter[level] += 1

        min_count = max(n - threshold, 2)  # at least 2 pathways must share the level
        near_misses = [
            {"level_name": level, "count": count, "total": n}
            for level, count in counter.most_common()
            if min_count <= count < n
        ]
        return near_misses

    def _enrich_intersection(self, levels: list[str],
                             parsed_pathways: list[ParsedPathway]) -> list[dict]:
        """Add vascular territory and region info to intersected levels."""
        if not levels:
            return []

        # Collect zone entries for all mapped pathways at these levels
        level_info: dict[str, dict] = {}
        for level_name in levels:
            vasc = set()
            involved = set()
            region = ""
            level_id = ""

            # Search through all atlas entries at this level
            for pp in parsed_pathways:
                bl = pp.base.lower()
                atlas_matches = self._base_to_atlas.get(bl, [])
                for acp in atlas_matches:
                    for entry in self._zone_index.get(acp, []):
                        if entry.level_name == level_name:
                            if entry.vascular_territory:
                                vasc.add(entry.vascular_territory)
                            involved.add(pp.raw)
                            region = entry.region
                            level_id = entry.level_id

            level_info[level_name] = {
                "level_name": level_name,
                "level_id": level_id,
                "region": region,
                "vascular_territories": sorted(vasc),
                "involved_pathways": sorted(involved),
            }

        # Sort by anatomical order
        details = list(level_info.values())
        details.sort(key=lambda d: (
            REGION_ORDER.get(d["region"], 99),
            d["level_id"],
        ))
        return details

    def _sort_levels(self, levels: list[str]) -> list[str]:
        """Sort level names by anatomical order."""
        # Build a lookup from level_name → (region, level_id)
        level_meta = {}
        for entries in self._zone_index.values():
            for e in entries:
                if e.level_name in level_meta:
                    continue
                level_meta[e.level_name] = (e.region, e.level_id)

        def sort_key(name):
            region, lid = level_meta.get(name, ("", ""))
            return (REGION_ORDER.get(region, 99), lid)

        return sorted(levels, key=sort_key)

    # ------------------------------------------------------------------ #
    #  Warnings
    # ------------------------------------------------------------------ #

    def _generate_warnings(self, pathways: list[str],
                           intersection_details: list[dict]) -> list[str]:
        warnings = []
        if not pathways:
            return warnings

        # Classify pathways
        has_motor = any(self._is_type(p, "motor") for p in pathways)
        has_sensory = any(self._is_type(p, "sensory") for p in pathways)
        has_ataxia = any(self._is_type(p, "ataxia") for p in pathways)

        # Lacunar infarction check
        pure_motor = has_motor and not has_sensory and not has_ataxia
        pure_sensory = has_sensory and not has_motor and not has_ataxia
        pure_ataxia = has_ataxia and not has_motor and not has_sensory

        if pure_motor or pure_sensory or pure_ataxia:
            syndrome_type = "純運動" if pure_motor else ("純感覺" if pure_sensory else "純運動失調")
            warnings.append(
                f"單一系統受損 ({syndrome_type})，可能為 lacunar infarction。"
                f"常見位置：internal capsule, basal ganglia, thalamus, pons。"
            )

        # Sensorimotor stroke
        if has_motor and has_sensory and not has_ataxia:
            warnings.append(
                "運動+感覺同時受損，提示 thalamocapsular region 或 cortical stroke。"
            )

        # Ataxic hemiparesis
        if has_motor and has_ataxia:
            warnings.append(
                "運動+共濟失調同時受損，可能為 ataxic hemiparesis (basis pontis or internal capsule)。"
            )

        # Aphasia/Apraxia check
        has_aphasia = any("aphasia" in p.lower() for p in pathways)
        has_apraxia = any("aprasia" in p.lower() or "apraxia" in p.lower() for p in pathways)

        if has_aphasia or has_apraxia:
            warnings.append(
                "包含 aphasia/apraxia，屬於皮質功能，提示 MCA territory cortical stroke。"
            )

        # Crossed signs
        left_cn = any(
            "(l)" in p.lower() and any(
                x in p.lower() for x in ["corticobulbar", "ew nucleus", "taste", "tl("]
            ) for p in pathways
        )
        right_long = any(
            "(r)" in p.lower() and any(
                x in p.lower() for x in ["corticospinal", "lemniscus", "spinothalamic"]
            ) for p in pathways
        )
        right_cn = any(
            "(r)" in p.lower() and any(
                x in p.lower() for x in ["corticobulbar", "ew nucleus", "taste", "tl("]
            ) for p in pathways
        )
        left_long = any(
            "(l)" in p.lower() and any(
                x in p.lower() for x in ["corticospinal", "lemniscus", "spinothalamic"]
            ) for p in pathways
        )

        if (left_cn and right_long) or (right_cn and left_long):
            warnings.append(
                "交叉性症狀 (ipsilateral cranial nerve + contralateral long tract)，"
                "提示腦幹病灶 (brainstem stroke)。"
            )

        # Wallenberg syndrome hints
        has_horner = any("sympathetic" in p.lower() for p in pathways)
        has_spinothalamic = any("spinothalamic" in p.lower() for p in pathways)
        has_ataxia_path = any("cerebell" in p.lower() or "ataxia" in p.lower() for p in pathways)

        if has_horner and has_spinothalamic and has_ataxia_path:
            warnings.append(
                "Horner syndrome + 對側痛溫覺障礙 + 共濟失調 → "
                "高度懷疑 Wallenberg syndrome (lateral medullary syndrome, PICA territory)。"
            )

        # Consciousness change
        has_consciousness = any("reticular" in p.lower() for p in pathways)
        if has_consciousness:
            warnings.append(
                "意識改變提示 reticular formation 受損，可能為 basilar artery occlusion "
                "或雙側腦幹病灶。需緊急評估。"
            )

        # Vascular territory hint from intersection
        if intersection_details:
            all_vasc = set()
            for d in intersection_details:
                all_vasc.update(d.get("vascular_territories", []))
            if all_vasc:
                vasc_str = ", ".join(sorted(all_vasc)[:5])
                warnings.append(f"交集處主要血管供應：{vasc_str}")

        return warnings

    @staticmethod
    def _is_type(pathway: str, ptype: str) -> bool:
        lower = pathway.lower()
        if ptype == "motor":
            return any(k in lower for k in ["motor", "corticospinal", "corticobulbar", "rubrospinal"])
        if ptype == "sensory":
            return any(k in lower for k in ["sensory", "lemniscus", "spinothalamic", "taste"])
        if ptype == "ataxia":
            return any(k in lower for k in ["ataxia", "cerebell"])
        return False
