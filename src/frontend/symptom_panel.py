"""Symptom selection panel with categorized tabs."""
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QCheckBox, QGroupBox, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal


CATEGORY_DISPLAY = {
    "cranial_nerve": "Cranial Nerves",
    "motor": "Motor",
    "sensory": "Sensory",
    "cerebellar": "Cerebellar",
    "visual": "Visual Field",
    "other": "Other",
}

CATEGORY_ORDER = ["cranial_nerve", "motor", "sensory", "cerebellar", "visual", "other"]


def _classify_symptom(name: str) -> str:
    """Quick classify for UI grouping."""
    lower = name.lower()
    if lower.startswith("cn"):
        return "cranial_nerve"
    if "hemiparesis" in lower or "hemiparalysis" in lower or "distal fine" in lower:
        return "motor"
    if "hypoesthesia" in lower:
        return "sensory"
    if "fnf" in lower or "heel" in lower or "ataxia" in lower or "vertigo" in lower:
        return "cerebellar"
    if "eye" in lower or "rapd" in lower or "hemianopia" in lower or "quadrant" in lower:
        return "visual"
    if "conjugate" in lower:
        return "cranial_nerve"
    if "ptosis" in lower:
        return "cranial_nerve"
    return "other"


class SymptomPanel(QWidget):
    """Panel with categorized symptom checkboxes."""

    symptoms_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes: list[tuple[dict, QCheckBox]] = []
        self._symptoms = self._load_symptoms()
        self._init_ui()

    def _load_symptoms(self) -> list[dict]:
        data_path = Path(__file__).parent.parent.parent / "data" / "existing" / "symptoms.json"
        if data_path.exists():
            return json.loads(data_path.read_text())
        return []

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with buttons
        header = QHBoxLayout()
        title = QLabel("神經學症狀檢查 (NE)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #111827;")
        header.addWidget(title)
        header.addStretch()

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.clicked.connect(self.reset)

        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.setObjectName("analyzeBtn")

        header.addWidget(self.reset_btn)
        header.addWidget(self.analyze_btn)
        layout.addLayout(header)

        # Categorized tabs
        tabs = QTabWidget()
        categorized = {}
        for s in self._symptoms:
            cat = _classify_symptom(s["symptom"])
            categorized.setdefault(cat, []).append(s)

        for cat in CATEGORY_ORDER:
            if cat not in categorized:
                continue
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setSpacing(2)

            for s in categorized[cat]:
                cb = QCheckBox(s["symptom"])
                cb.stateChanged.connect(lambda _: self.symptoms_changed.emit())
                scroll_layout.addWidget(cb)
                self._checkboxes.append((s, cb))

            scroll_layout.addStretch()
            scroll.setWidget(scroll_content)
            tab_layout.addWidget(scroll)
            tabs.addTab(tab_widget, CATEGORY_DISPLAY.get(cat, cat))

        layout.addWidget(tabs)

    def get_checked_symptoms(self) -> list[dict]:
        """Return list of checked symptom dicts."""
        return [s for s, cb in self._checkboxes if cb.isChecked()]

    def reset(self):
        for _, cb in self._checkboxes:
            cb.setChecked(False)
        self.symptoms_changed.emit()
