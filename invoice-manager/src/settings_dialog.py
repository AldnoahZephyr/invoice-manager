# -*- coding: utf-8 -*-
"""
参数设置对话框
允许用户设置 Tesseract OCR 引擎路径，保存到数据库
"""

import os
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QGroupBox
)

from .database import Database
from . import extractors


class SettingsDialog(QDialog):
    """参数设置对话框"""

    TESSERACT_KEY = 'tesseract_path'

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        self.setWindowTitle('参数设置')
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- OCR 设置组 ----
        ocr_group = QGroupBox('OCR 引擎设置')
        ocr_layout = QVBoxLayout(ocr_group)
        ocr_layout.setSpacing(8)

        # 说明文字
        hint = QLabel(
            'Tesseract OCR 引擎用于识别图片型发票（如机票行程单）。\n'
            '请指定 tesseract.exe 的完整路径。留空则使用程序内置或系统默认路径。'
        )
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 12px;')
        ocr_layout.addWidget(hint)

        # 路径选择行
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel('Tesseract 路径：'))
        self.edt_tesseract = QLineEdit()
        self.edt_tesseract.setPlaceholderText('例如：C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
        path_layout.addWidget(self.edt_tesseract, 1)

        self.btn_browse = QPushButton('浏览...')
        self.btn_browse.setFixedWidth(80)
        self.btn_browse.clicked.connect(self._on_browse)
        path_layout.addWidget(self.btn_browse)

        ocr_layout.addLayout(path_layout)

        # 测试与状态行
        test_layout = QHBoxLayout()
        self.btn_test = QPushButton('测试路径')
        self.btn_test.setFixedWidth(100)
        self.btn_test.clicked.connect(self._on_test)
        test_layout.addWidget(self.btn_test)

        self.lbl_status = QLabel('')
        self.lbl_status.setStyleSheet('font-size: 12px;')
        test_layout.addWidget(self.lbl_status, 1)
        ocr_layout.addLayout(test_layout)

        layout.addWidget(ocr_group)

        # ---- 底部按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton('保存')
        self.btn_save.setFixedWidth(100)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton('取消')
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """从数据库加载已保存的设置"""
        path = self.db.get_setting(self.TESSERACT_KEY, '')
        self.edt_tesseract.setText(path)

        # 显示当前生效的路径
        current = extractors.get_tesseract_cmd()
        if current:
            self.lbl_status.setText(f'当前生效路径：{current}')
            self.lbl_status.setStyleSheet('font-size: 12px; color: #4caf50;')
        else:
            self.lbl_status.setText('当前未找到 Tesseract 引擎')
            self.lbl_status.setStyleSheet('font-size: 12px; color: #e53935;')

    def _on_browse(self):
        """浏览选择 tesseract.exe"""
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 Tesseract 可执行文件', '',
            '可执行文件 (*.exe);;所有文件 (*.*)'
        )
        if path:
            self.edt_tesseract.setText(path)

    def _on_test(self):
        """测试输入的路径是否可用"""
        path = self.edt_tesseract.text().strip()

        if not path:
            QMessageBox.warning(self, '提示', '请先输入 Tesseract 路径')
            return

        if not os.path.isfile(path):
            self.lbl_status.setText('路径无效：文件不存在')
            self.lbl_status.setStyleSheet('font-size: 12px; color: #e53935;')
            QMessageBox.warning(self, '测试失败', f'文件不存在：\n{path}')
            return

        # 尝试运行 tesseract --version
        try:
            result = subprocess.run(
                [path, '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.strip().split('\n')[0]
                self.lbl_status.setText(f'测试成功：{version_line}')
                self.lbl_status.setStyleSheet('font-size: 12px; color: #4caf50;')
                QMessageBox.information(self, '测试成功', f'Tesseract 可正常运行：\n{version_line}')
            else:
                self.lbl_status.setText('测试失败：返回错误')
                self.lbl_status.setStyleSheet('font-size: 12px; color: #e53935;')
                QMessageBox.warning(self, '测试失败', f'tesseract 执行返回错误：\n{result.stderr}')
        except Exception as e:
            self.lbl_status.setText(f'测试失败：{e}')
            self.lbl_status.setStyleSheet('font-size: 12px; color: #e53935;')
            QMessageBox.warning(self, '测试失败', f'执行 tesseract 时出错：\n{e}')

    def _on_save(self):
        """保存设置"""
        path = self.edt_tesseract.text().strip()

        # 如果输入了路径但文件不存在，给警告但允许保存
        if path and not os.path.isfile(path):
            ret = QMessageBox.question(
                self, '路径警告',
                f'指定的文件不存在：\n{path}\n\n是否仍然保存？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return

        # 保存到数据库
        self.db.set_setting(self.TESSERACT_KEY, path)

        # 即时生效：更新 extractors 模块的自定义路径
        extractors.set_tesseract_cmd(path)

        QMessageBox.information(self, '保存成功', '参数设置已保存并即时生效。')
        self.accept()
