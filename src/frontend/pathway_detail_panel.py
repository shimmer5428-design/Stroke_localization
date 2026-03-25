"""Pathway detail panel showing zone-level information from atlas data."""
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QTreeWidget,
    QTreeWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "atlas_extractions"


class PathwayDetailPanel(QWidget):
    """Shows detailed zone information for a selected pathway."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zone_data = self._load_zone_data()
        self._init_ui()

    def _load_zone_data(self) -> dict:
        """Load all batch pathway zone mappings."""
        all_mappings = {}
        for batch_file in sorted(DATA_DIR.glob("batch*_pathway_zone_mapping.json")):
            try:
                data = json.loads(batch_file.read_text())
                mappings = data.get("pathway_zone_mappings", [])
                for m in mappings:
                    key = m.get("clinical_pathway", "")
                    if key:
                        all_mappings.setdefault(key, []).append(m)
            except (json.JSONDecodeError, KeyError):
                continue

        # Also load from batch level files
        for batch_file in sorted(DATA_DIR.glob("batch*_*.json")):
            if "pathway_zone_mapping" in batch_file.name:
                continue
            try:
                data = json.loads(batch_file.read_text())
                levels = data.get("anatomical_levels", [])
                for level in levels:
                    for tract in level.get("tracts", []):
                        cp = tract.get("clinical_pathway", "")
                        if cp:
                            entry = {
                                "level": level.get("level_name", ""),
                                "figure": level.get("figure", ""),
                                "zone": tract.get("zone", ""),
                                "quadrant": tract.get("quadrant", ""),
                                "depth": tract.get("depth", ""),
                                "somatotopy": tract.get("somatotopy", ""),
                                "vascular_territory": tract.get("vascular_territory", ""),
                                "notes": tract.get("notes", ""),
                            }
                            all_mappings.setdefault(cp, []).append(entry)
            except (json.JSONDecodeError, KeyError):
                continue

        return all_mappings

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("路徑詳情 (Atlas Zone Data)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827; padding: 8px 0;")
        layout.addWidget(title)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Level / Property", "Value"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tree.setAlternatingRowColors(True)
        self._tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:alternate {
                background-color: #f9fafb;
            }
        """)
        layout.addWidget(self._tree)

        self._placeholder = QLabel("點擊分析結果中的路徑以查看詳情")
        self._placeholder.setStyleSheet("color: #9ca3af; font-size: 13px; padding: 12px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._placeholder)

    def show_pathway_detail(self, pathway_name: str):
        """Show zone details for a given pathway name."""
        self._tree.clear()
        self._placeholder.setVisible(False)
        self._tree.setVisible(True)

        # Try exact match first, then fuzzy
        entries = self._zone_data.get(pathway_name, [])
        if not entries:
            # Try matching without laterality
            base = pathway_name.replace("(L)", "").replace("(R)", "").strip()
            for key, val in self._zone_data.items():
                if base in key or key in base:
                    entries = val
                    break

        if not entries:
            self._placeholder.setText(f"無 atlas 資料: {pathway_name}")
            self._placeholder.setVisible(True)
            self._tree.setVisible(False)
            return

        root = QTreeWidgetItem(self._tree, [pathway_name, ""])
        root.setExpanded(True)

        seen_levels = set()
        for entry in entries:
            level = entry.get("level") or entry.get("level_name", "unknown")
            if level in seen_levels:
                continue
            seen_levels.add(level)

            level_item = QTreeWidgetItem(root, [level, ""])
            level_item.setExpanded(True)

            for field in ["zone", "quadrant", "depth", "somatotopy", "vascular_territory", "notes", "figure"]:
                val = entry.get(field, "")
                if val:
                    # Handle dict (from pathway_zone_mapping format)
                    if isinstance(val, dict):
                        for k, v in val.items():
                            QTreeWidgetItem(level_item, [k, str(v)])
                    else:
                        QTreeWidgetItem(level_item, [field, str(val)])

        self._tree.expandAll()

    def clear(self):
        self._tree.clear()
        self._placeholder.setText("點擊分析結果中的路徑以查看詳情")
        self._placeholder.setVisible(True)
