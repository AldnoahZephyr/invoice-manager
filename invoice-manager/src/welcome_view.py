# -*- coding: utf-8 -*-
"""
欢迎页模块
精简大气设计：标题区 + 三张渐变功能卡片，干净不空洞
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QColor

from .version import APP_VERSION, APP_NAME


# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------

WELCOME_STYLE = """
#WelcomeRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f5f7fa, stop:1 #e8ecf3);
}
#FuncCard_import {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e3f2fd, stop:1 #bbdefb);
    border: 2px solid #90caf9;
    border-radius: 14px;
}
#FuncCard_import:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #bbdefb, stop:1 #90caf9);
    border: 2px solid #42a5f5;
}
#FuncCard_query {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e0f2f1, stop:1 #b2dfdb);
    border: 2px solid #80cbc4;
    border-radius: 14px;
}
#FuncCard_query:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #b2dfdb, stop:1 #80cbc4);
    border: 2px solid #26a69a;
}
#FuncCard_calc {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fff8e1, stop:1 #ffecb3);
    border: 2px solid #ffe082;
    border-radius: 14px;
}
#FuncCard_calc:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffecb3, stop:1 #ffe082);
    border: 2px solid #ffc107;
}
#IconCircle_import {
    background: #1565c0;
    border: none;
    border-radius: 28px;
}
#IconCircle_query {
    background: #00796b;
    border: none;
    border-radius: 28px;
}
#IconCircle_calc {
    background: #f57f17;
    border: none;
    border-radius: 28px;
}
"""


# ---------------------------------------------------------------------------
# 功能入口卡片
# ---------------------------------------------------------------------------

class FuncCard(QFrame):
    """可点击的功能入口卡片 — 带渐变背景和圆形图标"""

    clicked = pyqtSignal(str)

    def __init__(self, icon_text, title, desc, color_hex, tab_type, parent=None):
        super().__init__(parent)
        self.tab_type = tab_type
        self.setObjectName(f'FuncCard_{tab_type}')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build_ui(icon_text, title, desc, color_hex)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def _build_ui(self, icon_text, title, desc, color_hex):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # 左侧：圆形图标区
        icon_circle = QFrame()
        icon_circle.setObjectName(f'IconCircle_{self.tab_type}')
        icon_circle.setFixedSize(56, 56)
        icon_layout = QVBoxLayout(icon_circle)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(
            'font-size: 26px; color: #fff; background: transparent; border: none;'
        )
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)

        # 右侧：标题 + 描述
        right = QVBoxLayout()
        right.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f'font-size: 18px; font-weight: bold; color: {color_hex}; '
            'background: transparent; border: none;'
        )

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(
            'font-size: 13px; color: #555; background: transparent; border: none;'
        )
        desc_label.setWordWrap(True)

        right.addWidget(title_label)
        right.addWidget(desc_label)
        right.addStretch()

        layout.addWidget(icon_circle)
        layout.addLayout(right, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.tab_type)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# 欢迎主页
# ---------------------------------------------------------------------------

class WelcomeView(QWidget):
    """欢迎主页 — 精简大气：标题 + 三张渐变功能卡片"""

    open_tab_requested = pyqtSignal(str)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName('WelcomeRoot')
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(48, 36, 48, 36)
        root_layout.setSpacing(28)
        root_layout.addStretch(1)   # 顶部弹性空间，推内容到中间偏上

        # ---- 标题区 ----
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_layout.setAlignment(Qt.AlignCenter)

        app_name = QLabel(APP_NAME)
        app_name.setStyleSheet(
            'font-size: 28px; font-weight: bold; color: #1565c0; '
            'background: transparent; border: none;'
        )
        app_name.setAlignment(Qt.AlignCenter)

        subtitle = QLabel('发票识别  ·  查询管理  ·  金额计算')
        subtitle.setStyleSheet(
            'font-size: 14px; color: #9e9e9e; background: transparent; border: none;'
        )
        subtitle.setAlignment(Qt.AlignCenter)

        title_layout.addWidget(app_name)
        title_layout.addWidget(subtitle)
        root_layout.addLayout(title_layout)

        root_layout.addSpacing(20)

        # ---- 三张功能卡片 ----
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        card_import = FuncCard(
            '📄', '识别入库',
            '批量识别 PDF / OFD / Excel 发票\n自动提取号码、金额、种类等信息\n一键入库保存到数据库',
            '#1565c0', 'import'
        )
        card_query = FuncCard(
            '🔍', '入库查询',
            '按发票号码、金额、部门等条件查询\n支持批量编辑、删除和导出 Excel\n方便管理和核对',
            '#00796b', 'query'
        )
        card_calc = FuncCard(
            '🧮', '发票计算',
            '根据目标金额自动计算所需发票\n便于报销核对',
            '#f57f17', 'calc'
        )

        for card in (card_import, card_query, card_calc):
            card.clicked.connect(self._on_card_clicked)
            cards_layout.addWidget(card)

        root_layout.addLayout(cards_layout)

        root_layout.addSpacing(16)

        # ---- 版本号 ----
        ver_label = QLabel(f'{APP_VERSION}')
        ver_label.setStyleSheet(
            'font-size: 12px; color: #bbb; background: transparent; border: none;'
        )
        ver_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(ver_label)

        root_layout.addStretch(2)   # 底部弹性空间，比顶部多，内容偏上居中

    def _on_card_clicked(self, tab_type):
        self.open_tab_requested.emit(tab_type)

    def _apply_style(self):
        self.setStyleSheet(WELCOME_STYLE)
