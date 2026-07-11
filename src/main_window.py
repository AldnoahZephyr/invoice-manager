# -*- coding: utf-8 -*-
"""
主窗口模块
实现菜单栏和多标签页界面，支持同时打开多个菜单页面并可关闭
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QAction, QWidget,
    QVBoxLayout, QStatusBar, QLabel
)

from .database import Database
from .import_view import ImportView
from .query_view import QueryView
from .invoice_calc_view import InvoiceCalcView
from .settings_dialog import SettingsDialog
from .welcome_view import WelcomeView
from .icons import get_app_icon, get_close_icon_path, get_close_hover_icon_path
from .version import APP_VERSION, APP_NAME
from . import extractors


APP_STYLE = """
QMainWindow { background: #f5f5f5; }
QMenuBar { background: #ffffff; border-bottom: 1px solid #ddd; padding: 2px; }
QMenuBar::item { padding: 4px 16px; background: transparent; }
QMenuBar::item:selected { background: #e3f2fd; }
QTabWidget::pane { border: 1px solid #ccc; background: #fff; }
QTabBar::tab { background: #e8e8e8; padding: 6px 24px 6px 12px; margin-right: 2px; border: 1px solid #ccc; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #fff; }
QTabBar::close-button { subcontrol-position: right; subcontrol-origin: padding; padding: 3px; width: 14px; height: 14px; image: url(%CLOSE_URL%); }
QTabBar::close-button:hover { image: url(%CLOSE_HOVER_URL%); background: #ffcccc; border-radius: 3px; }
QPushButton { padding: 4px 12px; border: 1px solid #bbb; border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fff, stop:1 #eee); min-height: 22px; }
QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e3f2fd, stop:1 #bbdefb); border-color: #90caf9; }
QPushButton:pressed { background: #bbdefb; }
QLineEdit { padding: 3px 6px; border: 1px solid #bbb; border-radius: 3px; min-height: 22px; }
QComboBox { padding: 3px 6px; border: 1px solid #bbb; border-radius: 3px; min-height: 22px; }
QTableWidget { gridline-color: #ddd; border: 1px solid #ccc; alternate-background-color: #f9f9f9; }
QHeaderView::section { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f0f0f0, stop:1 #ddd); padding: 4px; border: 1px solid #ccc; font-weight: bold; }
QLabel { font-size: 13px; }
"""


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, db=None):
        super().__init__()
        self.db = db if db is not None else Database()
        self._init_settings()
        self._init_ui()
        self._apply_style()

    def _init_settings(self):
        """从数据库加载系统参数并应用到运行时"""
        tesseract_path = self.db.get_setting(SettingsDialog.TESSERACT_KEY, '')
        extractors.set_tesseract_cmd(tesseract_path)

    def _init_ui(self):
        self.setWindowTitle(f'{APP_NAME} {APP_VERSION}')
        self.setWindowIcon(get_app_icon())
        self.resize(1200, 750)
        self.setMinimumSize(900, 500)

        # 菜单栏
        menubar = self.menuBar()
        menu_func = menubar.addMenu('菜单')

        action_import = QAction('识别入库', self)
        action_import.triggered.connect(lambda: self._open_tab('import'))
        menu_func.addAction(action_import)

        action_query = QAction('入库查询', self)
        action_query.triggered.connect(lambda: self._open_tab('query'))
        menu_func.addAction(action_query)

        menu_func.addSeparator()

        action_calc = QAction('发票计算', self)
        action_calc.triggered.connect(lambda: self._open_tab('calc'))
        menu_func.addAction(action_calc)

        # 参数设置菜单项（在"菜单"右侧）
        action_settings = QAction('参数设置', self)
        action_settings.triggered.connect(self._open_settings)
        menubar.addAction(action_settings)

        # 关于菜单项
        action_about = QAction('关于', self)
        action_about.triggered.connect(self._show_about)
        menubar.addAction(action_about)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        # 欢迎页（首页，不可关闭）
        self.welcome_view = WelcomeView(self.db)
        self.welcome_view.open_tab_requested.connect(self._open_tab)
        self.tab_widget.addTab(self.welcome_view, '首页')
        # 移除首页的关闭按钮
        self.tab_widget.tabBar().setTabButton(0, self.tab_widget.tabBar().RightSide, None)

        # 状态栏（显示版本号）
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        version_label = QLabel(f'{APP_VERSION}')
        version_label.setStyleSheet('color: #888; padding: 0 8px;')
        status_bar.addPermanentWidget(version_label)

    def _apply_style(self):
        close_path = get_close_icon_path().replace('\\', '/')
        close_hover_path = get_close_hover_icon_path().replace('\\', '/')
        style = APP_STYLE.replace('%CLOSE_URL%', close_path)
        style = style.replace('%CLOSE_HOVER_URL%', close_hover_path)
        self.setStyleSheet(style)

    def _open_tab(self, tab_type):
        """打开（或切换到）指定标签页"""
        # 检查是否已打开
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if tab_type == 'import' and isinstance(w, ImportView):
                self.tab_widget.setCurrentIndex(i)
                return
            if tab_type == 'query' and isinstance(w, QueryView):
                self.tab_widget.setCurrentIndex(i)
                return
            if tab_type == 'calc' and isinstance(w, InvoiceCalcView):
                self.tab_widget.setCurrentIndex(i)
                return

        # 新建标签页
        if tab_type == 'import':
            view = ImportView(self.db)
            self.tab_widget.addTab(view, '识别入库')
        elif tab_type == 'query':
            view = QueryView(self.db)
            self.tab_widget.addTab(view, '入库查询')
        elif tab_type == 'calc':
            view = InvoiceCalcView(self.db)
            self.tab_widget.addTab(view, '发票计算')
        self.tab_widget.setCurrentWidget(view)

    def _close_tab(self, index):
        """关闭标签页（首页不可关闭）"""
        if index == 0:
            return
        self.tab_widget.removeTab(index)

    def _on_tab_changed(self, index):
        """切换标签页事件（预留）"""
        pass

    def _open_settings(self):
        """打开参数设置对话框"""
        dialog = SettingsDialog(self.db, self)
        dialog.exec_()

    def _show_about(self):
        """显示关于对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(
            self, '关于',
            f'<b>{APP_NAME}</b><br>'
            f'版本：{APP_VERSION}<br><br>'
            f'功能：电子发票识别入库、查询管理、金额计算<br>'
            f'支持格式：PDF / OFD / Excel'
        )

    def _find_tab_view(self, tab_type):
        """查找已打开的标签页视图（用于截图等工具）"""
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if tab_type == 'import' and isinstance(w, ImportView):
                return w
            if tab_type == 'query' and isinstance(w, QueryView):
                return w
            if tab_type == 'calc' and isinstance(w, InvoiceCalcView):
                return w
        return None
