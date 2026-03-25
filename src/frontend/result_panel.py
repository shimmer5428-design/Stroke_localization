"""Result display panel showing atlas-based pathway analysis and intersection results."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal


class PathwayResultCard(QFrame):
    """A card showing one pathway's atlas zone levels. Clickable."""

    clicked = pyqtSignal(str)  # emits base pathway name

    def __init__(self, pw_info: dict, parent=None):
        super().__init__(parent)
        self._base_name = pw_info["base_name"]
        self._raw_name = pw_info["raw_name"]
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

        # Header: pathway name + laterality badge
        header_parts = [f"<b style='color:#2563eb'>{self._base_name}</b>"]
        lat = pw_info.get("laterality")
        if lat:
            color = "#dc2626" if lat == "R" else "#2563eb"
            header_parts.append(
                f"<span style='background:{color}; color:white; "
                f"border-radius:3px; padding:1px 6px; font-size:11px;'>{lat}</span>"
            )
        soma = pw_info.get("somatotopy")
        if soma:
            header_parts.append(
                f"<span style='color:#6b7280; font-size:11px;'>({soma})</span>"
            )
        header_parts.append(
            "<span style='color:#9ca3af; font-size:11px;'>&#x25B6; 點擊看詳情</span>"
        )

        name_label = QLabel("  ".join(header_parts))
        name_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(name_label)

        # Body: zone level info
        is_mapped = pw_info.get("is_mapped", True)
        zone_levels = pw_info.get("zone_levels", [])

        if not is_mapped:
            note = QLabel("(皮質功能，無圖譜中對應路徑)")
            note.setStyleSheet("color: #f59e0b; font-size: 12px;")
            layout.addWidget(note)
        elif zone_levels:
            count_label = QLabel(f"出現在 {len(zone_levels)} 個解剖層面")
            count_label.setStyleSheet("color: #059669; font-size: 12px; font-weight: bold;")
            layout.addWidget(count_label)
            # Show first few levels as preview
            preview = ", ".join(zone_levels[:3])
            if len(zone_levels) > 3:
                preview += f" ... (+{len(zone_levels) - 3})"
            preview_label = QLabel(preview)
            preview_label.setWordWrap(True)
            preview_label.setStyleSheet("color: #4b5563; font-size: 11px;")
            layout.addWidget(preview_label)
        else:
            no_data = QLabel("(圖譜中無對應資料)")
            no_data.setStyleSheet("color: #ef4444; font-size: 12px;")
            layout.addWidget(no_data)

    def mousePressEvent(self, event):
        self.clicked.emit(self._base_name)
        super().mousePressEvent(event)


class ResultPanel(QWidget):
    """Panel displaying atlas-based analysis results."""

    pathway_clicked = pyqtSignal(str)  # emits base pathway name

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

    def show_results(self, active_pathways: list, intersection_details: list,
                     near_miss: list, unmapped_pathways: list, warnings: list):
        """Display atlas-based analysis results."""
        self._clear_results()

        if not active_pathways:
            no_result = QLabel("未勾選任何症狀，或無對應路徑。")
            no_result.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
            no_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(no_result)
            return

        # --- Intersection result (most important, show first) ---
        self._show_intersection(intersection_details, near_miss)

        # --- Warnings ---
        if warnings:
            warn_title = QLabel("提醒")
            warn_title.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #111827; margin-top: 12px;"
            )
            self._content_layout.addWidget(warn_title)
            for w in warnings:
                wl = QLabel(w)
                wl.setWordWrap(True)
                wl.setStyleSheet("""
                    background-color: #dbeafe; color: #1e40af;
                    border-radius: 8px; padding: 12px; font-size: 13px;
                    margin: 2px 0;
                """)
                self._content_layout.addWidget(wl)

        # --- Unmapped pathways ---
        if unmapped_pathways:
            um_title = QLabel("皮質功能 (無圖譜路徑)")
            um_title.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #92400e; margin-top: 8px;"
            )
            self._content_layout.addWidget(um_title)
            um_text = QLabel(", ".join(unmapped_pathways))
            um_text.setWordWrap(True)
            um_text.setStyleSheet("""
                background-color: #fef3c7; color: #92400e;
                border-radius: 8px; padding: 8px; font-size: 12px;
            """)
            self._content_layout.addWidget(um_text)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e5e7eb; margin: 8px 0;")
        self._content_layout.addWidget(sep)

        # --- Individual pathway results ---
        mapped = [p for p in active_pathways if p["is_mapped"]]
        pw_title = QLabel(f"受影響路徑 ({len(mapped)} 條)")
        pw_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827;")
        self._content_layout.addWidget(pw_title)

        for pw_info in active_pathways:
            card = PathwayResultCard(pw_info)
            card.clicked.connect(self.pathway_clicked.emit)
            self._content_layout.addWidget(card)

        self._content_layout.addStretch()

    def _show_intersection(self, intersection_details: list, near_miss: list):
        """Show intersection or near-miss results."""
        title = QLabel("定位結果 — 路徑交集")
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #111827; margin-top: 4px;"
        )
        self._content_layout.addWidget(title)

        if intersection_details:
            # Group by region
            by_region: dict = {}
            for d in intersection_details:
                region = d.get("region", "Unknown")
                by_region.setdefault(region, []).append(d)

            container = QFrame()
            container.setStyleSheet("""
                background-color: #dcfce7; border-radius: 8px; padding: 12px;
            """)
            clayout = QVBoxLayout(container)
            clayout.setSpacing(8)

            summary = QLabel(
                f"<b style='color:#166534;'>找到 {len(intersection_details)} 個候選定位層面</b>"
            )
            summary.setTextFormat(Qt.TextFormat.RichText)
            clayout.addWidget(summary)

            for region, details in by_region.items():
                region_label = QLabel(f"<b>{region}</b>")
                region_label.setTextFormat(Qt.TextFormat.RichText)
                region_label.setStyleSheet("color: #166534; font-size: 13px; margin-top: 4px;")
                clayout.addWidget(region_label)

                for d in details:
                    level_text = f"  • {d['level_name']}"
                    vasc = d.get("vascular_territories", [])
                    if vasc:
                        level_text += f"  [{', '.join(vasc[:3])}]"
                    ll = QLabel(level_text)
                    ll.setWordWrap(True)
                    ll.setStyleSheet("color: #166534; font-size: 12px;")
                    clayout.addWidget(ll)

            self._content_layout.addWidget(container)

        elif near_miss:
            # Show near-miss results
            container = QFrame()
            container.setStyleSheet("""
                background-color: #fef9c3; border-radius: 8px; padding: 12px;
            """)
            clayout = QVBoxLayout(container)

            header = QLabel(
                "<b style='color:#854d0e;'>無完全交集，以下為近似匹配（出現在多數路徑）</b>"
            )
            header.setTextFormat(Qt.TextFormat.RichText)
            header.setWordWrap(True)
            clayout.addWidget(header)

            for nm in near_miss[:10]:
                text = f"• {nm['level_name']}  ({nm['count']}/{nm['total']} 條路徑)"
                nl = QLabel(text)
                nl.setWordWrap(True)
                nl.setStyleSheet("color: #854d0e; font-size: 12px;")
                clayout.addWidget(nl)

            self._content_layout.addWidget(container)
        else:
            no_int = QLabel("沒有交集，請根據下方各路徑自行校正")
            no_int.setWordWrap(True)
            no_int.setStyleSheet("""
                background-color: #fef9c3; color: #854d0e;
                border-radius: 8px; padding: 12px; font-size: 14px;
            """)
            self._content_layout.addWidget(no_int)

    def clear(self):
        self._clear_results()
        self._placeholder = QLabel("請勾選症狀後點擊「分析」按鈕")
        self._placeholder.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._placeholder)
