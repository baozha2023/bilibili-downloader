# -*- coding: utf-8 -*-

class UIStyles:
    """UI Styles for the application"""
    
    MAIN_WINDOW = """
        QMainWindow {
            background-color: #f6f7f8;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            font-size: 22px;
        }
    """

    TAB_WIDGET = """
        QTabWidget {
            background-color: #ffffff;
            border: none;
        }
        QTabWidget::pane {
            border: 1px solid #e7e7e7;
            background-color: #ffffff;
            border-radius: 8px;
            top: -1px; 
        }
        QTabBar::tab {
            background-color: #f6f7f8;
            color: #61666d;
            padding: 10px 15px;
            border: 1px solid #e7e7e7;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 4px;
            font-size: 20px;
            min-width: 80px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #fb7299;
            font-weight: bold;
            border-bottom: 1px solid #ffffff;
        }
        QTabBar::tab:hover:!selected {
            background-color: #ffffff;
            color: #fb7299;
        }
    """

    WIDGETS = """
        QLabel {
            color: #18191c;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            font-size: 14px;
        }
        QPushButton {
            background-color: #fb7299;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #fc8bab;
        }
        QPushButton:pressed {
            background-color: #e45c84;
        }
        QPushButton:disabled {
            background-color: #e7e7e7;
            color: #999999;
        }
        QLineEdit {
            border: 1px solid #e7e7e7;
            padding: 10px;
            border-radius: 4px;
            background-color: #ffffff;
            selection-background-color: #fb7299;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 1px solid #fb7299;
        }
        QProgressBar {
            border: none;
            border-radius: 4px;
            background-color: #e7e7e7;
            text-align: center;
            font-size: 14px;
            color: #333333;
            min-height: 20px;
        }
        QProgressBar::chunk {
            background-color: #fb7299;
            border-radius: 4px;
        }
        QTableWidget {
            border: 1px solid #e7e7e7;
            border-radius: 6px;
            background-color: #ffffff;
            selection-background-color: #fef0f5;
            selection-color: #fb7299;
            gridline-color: #f0f0f0;
            font-size: 14px;
        }
        QTableWidget::item {
            padding: 8px;
        }
        QHeaderView::section {
            background-color: #f6f7f8;
            color: #61666d;
            padding: 10px;
            border: none;
            border-bottom: 1px solid #e7e7e7;
            border-right: 1px solid #e7e7e7;
            font-weight: bold;
            font-size: 14px;
        }
        QGroupBox {
            border: 1px solid #e7e7e7;
            border-radius: 6px;
            margin-top: 25px;
            font-weight: bold;
            padding-top: 20px;
            font-size: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            color: #333333;
        }
        QCheckBox {
            spacing: 8px;
            color: #61666d;
            font-size: 14px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 1px solid #cccccc;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:unchecked:hover {
            border-color: #fb7299;
        }
        QCheckBox::indicator:checked {
            background-color: #fb7299;
            border-color: #fb7299;
        }
        QComboBox {
            border: 1px solid #e7e7e7;
            border-radius: 4px;
            padding: 8px 12px;
            min-width: 6em;
            font-size: 14px;
        }
        QComboBox:hover {
            border-color: #c0c0c0;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left-width: 0px;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        QTextEdit {
            border: 1px solid #e7e7e7;
            border-radius: 4px;
            font-size: 13px;
        }
    """
    
    # Specific styles for Download Tab
    DOWNLOAD_GROUP_BOX = """
        QGroupBox { 
            font-weight: bold; 
            font-size: 28px; 
        }
        QLabel, QLineEdit {
            font-size: 24px;
        }
    """
    
    DOWNLOAD_BTN = "background-color: #fb7299; color: white; font-weight: bold; padding: 5px 15px; font-size: 26px;"
    CANCEL_BTN = "background-color: #999; color: white; padding: 5px 15px; font-size: 26px;"
    
    # Popular Tab
    POPULAR_BTN = """
        QPushButton {
            background-color: #fb7299;
            color: white;
            border-radius: 5px;
            font-size: 20px;
            font-weight: bold;
            padding: 8px 20px;
            border: none;
        }
        QPushButton:hover {
            background-color: #fc8bab;
        }
        QPushButton:pressed {
            background-color: #e45c84;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
    """
    
    # Account Tab
    LOGIN_BTN = "background-color: #00a1d6; color: white; font-weight: bold; padding: 8px 15px; font-size: 22px;"
    UNLOCK_BTN = """
        QPushButton {
            background-color: #fb7299;
            color: white;
            font-size: 20px;
            font-weight: bold;
            padding: 10px 40px;
            border-radius: 25px;
            border: none;
        }
        QPushButton:hover {
            background-color: #fc8bab;
        }
    """
    
    @staticmethod
    def get_main_style():
        return UIStyles.MAIN_WINDOW + UIStyles.TAB_WIDGET + UIStyles.WIDGETS
