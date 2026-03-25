"""Core analysis engine — pathway intersection localization."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class LocalizationAnalyzer:
    """Analyzes NE findings to localize stroke via pathway intersection."""

    def __init__(self):
        self._symptoms = self._load_json("existing/symptoms.json")
        self._pathway_loc = self._load_json("existing/pathway_locations.json")
        self._regions = self._pathway_loc.get("regions", [])
        self._pathways = self._pathway_loc.get("pathways", {})

    def _load_json(self, rel_path: str):
        p = DATA_DIR / rel_path
        if p.exists():
            return json.loads(p.read_text())
        return {}

    def analyze(self, checked_symptoms: list[dict]) -> dict:
        """
        Run localization analysis.

        Args:
            checked_symptoms: list of symptom dicts with 'symptom', 'pathway1', 'pathway2'

        Returns:
            {
                "active_pathways": [str],
                "pathway_results": [{"name": str, "regions": [str]}],
                "intersection": [str],
                "warnings": [str],
            }
        """
        # 1. Collect active pathways
        active_pathways = []
        for s in checked_symptoms:
            p1 = (s.get("pathway1") or "").strip()
            p2 = (s.get("pathway2") or "").strip()
            if p1:
                active_pathways.append(p1)
            if p2:
                active_pathways.append(p2)

        # Deduplicate while preserving order
        seen = set()
        unique_pathways = []
        for p in active_pathways:
            if p not in seen:
                seen.add(p)
                unique_pathways.append(p)

        if not unique_pathways:
            return {
                "active_pathways": [],
                "pathway_results": [],
                "intersection": [],
                "warnings": [],
            }

        # 2. Find affected regions for each pathway
        pathway_results = []
        pathway_region_sets = []

        for pw in unique_pathways:
            bits = self._pathways.get(pw)
            if bits:
                regions = [self._regions[i] for i, b in enumerate(bits) if b == 1]
                pathway_results.append({"name": pw, "regions": regions})
                pathway_region_sets.append(set(regions))
            else:
                pathway_results.append({"name": pw, "regions": []})

        # 3. Calculate intersection
        valid_sets = [s for s in pathway_region_sets if s]
        if valid_sets:
            intersection = set(valid_sets[0])
            for s in valid_sets[1:]:
                intersection &= s
            intersection = sorted(intersection)
        else:
            intersection = []

        # 4. Generate warnings
        warnings = self._generate_warnings(unique_pathways, intersection)

        return {
            "active_pathways": unique_pathways,
            "pathway_results": pathway_results,
            "intersection": intersection,
            "warnings": warnings,
        }

    def _generate_warnings(self, pathways: list[str], intersection: list[str]) -> list[str]:
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

        # Aphasia/Apraxia + MCA
        has_aphasia = any("aphasia" in p.lower() for p in pathways)
        has_apraxia = any("aprasia" in p.lower() or "apraxia" in p.lower() for p in pathways)
        mca_in_intersection = any("mca" in r.lower() for r in intersection)

        if (has_aphasia or has_apraxia) and mca_in_intersection:
            warnings.append(
                "包含 aphasia/apraxia 且交集在 MCA 區域，請留意大面積中風。"
            )

        # Crossed signs (ipsilateral CN + contralateral motor/sensory)
        left_cn = any("(l)" in p.lower() and any(x in p.lower() for x in ["corticobulbar", "ew nucleus", "taste", "tl("])
                       for p in pathways)
        right_long = any("(r)" in p.lower() and any(x in p.lower() for x in ["corticospinal", "lemniscus", "spinothalamic"])
                         for p in pathways)
        right_cn = any("(r)" in p.lower() and any(x in p.lower() for x in ["corticobulbar", "ew nucleus", "taste", "tl("])
                        for p in pathways)
        left_long = any("(l)" in p.lower() and any(x in p.lower() for x in ["corticospinal", "lemniscus", "spinothalamic"])
                        for p in pathways)

        if (left_cn and right_long) or (right_cn and left_long):
            warnings.append(
                "交叉性症狀 (ipsilateral cranial nerve + contralateral long tract)，"
                "提示腦幹病灶 (brainstem stroke)。"
            )

        # Wallenberg syndrome hints
        has_horner = any("sympathetic" in p.lower() for p in pathways)
        has_spinothalamic = any("spinothalamic" in p.lower() for p in pathways)
        has_ataxia_path = any("cerebell" in p.lower() or "ataxia" in p.lower() for p in pathways)
        lat_medulla = any("lateral medulla" in r.lower() for r in intersection)

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
