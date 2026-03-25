"""Result display panel showing pathway analysis and intersection results."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal


class PathwayResultCard(QFrame):
    """A card showing one pathway's affected regions. Clickable."""

    clicked = pyqtSignal(str)  # emits pathway name

    def __init__(self, pathway_name: str, regions: list[str], parent=None):
        super().__init__(parent)
        self._pathway_name = pathway_name
        self.setObjectName("pathwayCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#pathwayCard {
                background-color: #f9fafb;
                border-radius: 6px;
                padding: 8px;
                margin: 2px 0;
            }
            QFrame#pathwayCard:hover {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        name_label = QLabel(f"<b style='color:#2563eb'>{pathway_name}</b>  <span style='color:#9ca3af; font-size:11px;'>&#x25B6; 點擊看詳情</span>")
        name_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(name_label)

        if regions:
            regions_text = ", ".join(regions)
            regions_label = QLabel(f"影響區域: {regions_text}")
            regions_label.setWordWrap(True)
            regions_label.setStyleSheet("color: #4b5563; font-size: 12px;")
            layout.addWidget(regions_label)
        else:
            no_data = QLabel("(pathway 資料庫中無對應區域)")
            no_data.setStyleSheet("color: #ef4444; font-size: 12px;")
            layout.addWidget(no_data)

    def mousePressEvent(self, event):
        self.clicked.emit(self._pathway_name)
        super().mousePressEvent(event)


class ResultPanel(QWidget):
    """Panel displaying analysis results."""

    pathway_clicked = pyqtSignal(str)  # emits pathway name when a card is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("分析結果")
        title.setObjectName("resultTitle")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #111827; padding: 8px 0;")
        self._layout.addWidget(title)

        # Scroll area for results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll_content = QWidget()
        self._content_layout = QVBoxLayout(self._scroll_content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._scroll_content)
        self._layout.addWidget(scroll)

        # Placeholder
        self._placeholder = QLabel("請勾選症狀後點擊「分析」按鈕")
        self._placeholder.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._placeholder)

    def _clear_results(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def show_results(self, pathway_results: list[dict], intersection: list[str],
                     warnings: list[str]):
        """
        Display analysis results.

        Args:
            pathway_results: [{"name": str, "regions": [str]}]
            intersection: list of intersected region names
            warnings: list of warning/hint strings
        """
        self._clear_results()

        if not pathway_results:
            no_result = QLabel("未勾選任何症狀，或無對應路徑。")
            no_result.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
            no_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(no_result)
            return

        # --- Intersection result (most important, show first) ---
        intersection_title = QLabel("共同影響的區域 (交集)")
        intersection_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827; margin-top: 4px;")
        self._content_layout.addWidget(intersection_title)

        if intersection:
            text = ", ".join(intersection)
            result_label = QLabel(text)
            result_label.setWordWrap(True)
            result_label.setObjectName("intersectionResult")
            result_label.setStyleSheet("""
                background-color: #dcfce7; color: #166534;
                border-radius: 8px; padding: 12px;
                font-size: 14px; font-weight: bold;
            """)
            self._content_layout.addWidget(result_label)
        else:
            no_int = QLabel("沒有交集，請根據下方各路徑自行校正")
            no_int.setWordWrap(True)
            no_int.setObjectName("noIntersection")
            no_int.setStyleSheet("""
                background-color: #fef9c3; color: #854d0e;
                border-radius: 8px; padding: 12px; font-size: 14px;
            """)
            self._content_layout.addWidget(no_int)

        # --- Warnings ---
        if warnings:
            warn_title = QLabel("提醒")
            warn_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; margin-top: 12px;")
            self._content_layout.addWidget(warn_title)
            for w in warnings:
                wl = QLabel(w)
                wl.setWordWrap(True)
                wl.setObjectName("warningLabel")
                wl.setStyleSheet("""
                    background-color: #dbeafe; color: #1e40af;
                    border-radius: 8px; padding: 12px; font-size: 13px;
                    margin: 2px 0;
                """)
                self._content_layout.addWidget(wl)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e5e7eb; margin: 8px 0;")
        self._content_layout.addWidget(sep)

        # --- Individual pathway results ---
        pw_title = QLabel(f"受影響路徑 ({len(pathway_results)} 條)")
        pw_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827;")
        self._content_layout.addWidget(pw_title)

        for pr in pathway_results:
            card = PathwayResultCard(pr["name"], pr["regions"])
            card.clicked.connect(self.pathway_clicked.emit)
            self._content_layout.addWidget(card)

        self._content_layout.addStretch()

    def clear(self):
        self._clear_results()
        self._placeholder = QLabel("請勾選症狀後點擊「分析」按鈕")
        self._placeholder.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._placeholder)
