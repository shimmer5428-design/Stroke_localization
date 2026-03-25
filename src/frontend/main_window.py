"""Main application window."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter
)
from PyQt6.QtCore import Qt

from .symptom_panel import SymptomPanel
from .result_panel import ResultPanel
from .pathway_detail_panel import PathwayDetailPanel
from .styles import MAIN_STYLE
from ..backend.analyzer import LocalizationAnalyzer


class MainWindow(QMainWindow):
    """Main window: symptom panel (left) + results (right)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("互動式神經學路徑分析工具 — Neuro Localization")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(MAIN_STYLE)

        self._analyzer = LocalizationAnalyzer()
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: symptom panel
        self._symptom_panel = SymptomPanel()
        self._symptom_panel.analyze_btn.clicked.connect(self._on_analyze)
        splitter.addWidget(self._symptom_panel)

        # Right: results + detail
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._result_panel = ResultPanel()
        self._result_panel.pathway_clicked.connect(self._on_pathway_clicked)
        right_splitter.addWidget(self._result_panel)

        self._detail_panel = PathwayDetailPanel()
        right_splitter.addWidget(self._detail_panel)

        right_splitter.setSizes([500, 300])
        right_layout.addWidget(right_splitter)
        splitter.addWidget(right_widget)

        splitter.setSizes([450, 750])
        main_layout.addWidget(splitter)

    def _on_analyze(self):
        checked = self._symptom_panel.get_checked_symptoms()
        if not checked:
            self._result_panel.clear()
            self._detail_panel.clear()
            return

        result = self._analyzer.analyze(checked)
        self._result_panel.show_results(
            result["pathway_results"],
            result["intersection"],
            result["warnings"],
        )

        # Show detail for first pathway if any
        if result["active_pathways"]:
            self._detail_panel.show_pathway_detail(result["active_pathways"][0])

    def _on_pathway_clicked(self, pathway_name: str):
        """Show detail panel for clicked pathway."""
        self._detail_panel.show_pathway_detail(pathway_name)
