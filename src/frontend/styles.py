"""QSS styles for the Neuro Localization app."""

MAIN_STYLE = """
QMainWindow {
    background-color: #f3f4f6;
}

QWidget#centralWidget {
    background-color: #f3f4f6;
}

/* Card-like panels */
QGroupBox {
    background-color: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px;
    padding-top: 28px;
    font-size: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 4px 8px;
    font-size: 16px;
    font-weight: bold;
    color: #111827;
}

/* Buttons */
QPushButton#analyzeBtn {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
    min-width: 100px;
}
QPushButton#analyzeBtn:hover {
    background-color: #1d4ed8;
}
QPushButton#analyzeBtn:pressed {
    background-color: #1e40af;
}

QPushButton#resetBtn {
    background-color: #6b7280;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
    min-width: 100px;
}
QPushButton#resetBtn:hover {
    background-color: #4b5563;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: #374151;
    padding: 4px 0;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #d1d5db;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}
QCheckBox::indicator:hover {
    border-color: #2563eb;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #e5e7eb;
    background: white;
    border-radius: 0 0 8px 8px;
}
QTabBar::tab {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 12px;
    color: #6b7280;
}
QTabBar::tab:selected {
    background: white;
    color: #2563eb;
    font-weight: bold;
    border-bottom: none;
}

/* Scroll area */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* Result labels */
QLabel#resultTitle {
    font-size: 16px;
    font-weight: bold;
    color: #111827;
    padding: 8px 0;
}

QLabel#intersectionResult {
    background-color: #dcfce7;
    color: #166534;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-weight: bold;
}

QLabel#noIntersection {
    background-color: #fef9c3;
    color: #854d0e;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
}

QLabel#warningLabel {
    background-color: #dbeafe;
    color: #1e40af;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
}

QLabel#pathwayLabel {
    background-color: #f9fafb;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #374151;
}

/* Splitter */
QSplitter::handle {
    background-color: #e5e7eb;
    width: 2px;
}
"""
