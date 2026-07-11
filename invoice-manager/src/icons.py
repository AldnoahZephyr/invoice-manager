# -*- coding: utf-8 -*-
"""
图标生成模块
使用 QPainter 程序化绘制应用图标和关闭按钮图标，无需外部图片文件，
天然兼容 PyInstaller 打包，且不存在版权问题。
"""

import os
import tempfile

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QBrush, QPen, QFont,
    QPainterPath, QLinearGradient, QIcon
)
from PyQt5.QtWidgets import QStyle, QApplication


# 缓存生成的临时文件路径
_temp_files = []


def _get_app_icon_pixmap(size=256):
    """绘制应用图标（发票主题：蓝底白色文件 + 发票字样）"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    # ---- 背景圆角矩形 ----
    margin = size * 0.06
    bg_rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = size * 0.18

    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor('#1976D2'))
    grad.setColorAt(1.0, QColor('#0D47A1'))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(bg_rect, radius, radius)

    # ---- 白色文档形状 ----
    doc_margin_x = size * 0.22
    doc_margin_top = size * 0.16
    doc_margin_bottom = size * 0.14
    doc_w = size - 2 * doc_margin_x
    doc_h = size - doc_margin_top - doc_margin_bottom
    doc_rect = QRectF(doc_margin_x, doc_margin_top, doc_w, doc_h)
    doc_radius = size * 0.04

    p.setBrush(QBrush(QColor('#FFFFFF')))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(doc_rect, doc_radius, doc_radius)

    # ---- 文档上的横线（模拟文字行）----
    p.setPen(QPen(QColor('#BBDEFB'), size * 0.018))
    line_left = doc_margin_x + doc_w * 0.15
    line_right = doc_margin_x + doc_w * 0.85
    line_start_y = doc_margin_top + doc_h * 0.25
    line_gap = doc_h * 0.12
    for i in range(4):
        y = line_start_y + i * line_gap
        # 最后一行短一些
        x2 = line_right if i < 3 else line_left + (line_right - line_left) * 0.6
        p.drawLine(QPointF(line_left, y), QPointF(x2, y))

    # ---- 底部 "发票" 印章圆 ----
    seal_cx = size * 0.72
    seal_cy = size * 0.74
    seal_r = size * 0.14
    p.setBrush(QBrush(QColor('#E53935')))
    p.setPen(QPen(QColor('#C62828'), size * 0.008))
    p.drawEllipse(QPointF(seal_cx, seal_cy), seal_r, seal_r)

    # 印章内文字 "票"
    p.setPen(QPen(QColor('#FFFFFF')))
    font = QFont('Microsoft YaHei', 1)
    font.setPixelSize(int(size * 0.12))
    font.setBold(True)
    p.setFont(font)
    text_rect = QRectF(seal_cx - seal_r, seal_cy - seal_r, seal_r * 2, seal_r * 2)
    p.drawText(text_rect, Qt.AlignCenter, '票')

    p.end()
    return pm


def _get_close_icon_pixmap(size=16, color='#E53935'):
    """绘制关闭按钮红叉图标"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    pen = QPen(QColor(color))
    pen.setWidth(max(2, int(size * 0.16)))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)

    inset = size * 0.25
    p.drawLine(QPointF(inset, inset), QPointF(size - inset, size - inset))
    p.drawLine(QPointF(size - inset, inset), QPointF(inset, size - inset))

    p.end()
    return pm


def _pixmap_to_temp_png(pixmap, name):
    """将 QPixmap 保存到临时 PNG 文件，返回路径"""
    path = os.path.join(tempfile.gettempdir(), f'_byinvoice_{name}.png')
    pixmap.save(path, 'PNG')
    if path not in _temp_files:
        _temp_files.append(path)
    return path


def get_app_icon():
    """获取应用图标 QIcon"""
    pm = _get_app_icon_pixmap(256)
    # 同时生成小尺寸以保持清晰
    icon = QIcon()
    for s in [16, 32, 48, 64, 128, 256]:
        icon.addPixmap(_get_app_icon_pixmap(s))
    return icon


def get_close_icon_path():
    """获取关闭按钮红叉图标的文件路径（供 stylesheet 使用）"""
    pm = _get_close_icon_pixmap(16, '#E53935')
    return _pixmap_to_temp_png(pm, 'close')


def get_close_hover_icon_path():
    """获取关闭按钮悬停时的红叉图标路径"""
    pm = _get_close_icon_pixmap(16, '#B71C1C')
    return _pixmap_to_temp_png(pm, 'close_hover')


def generate_ico_file(output_path):
    """
    生成 .ico 图标文件（供 PyInstaller 打包使用）
    需要安装 Pillow: pip install Pillow
    """
    pm = _get_app_icon_pixmap(256)
    png_path = _pixmap_to_temp_png(pm, 'app_icon')

    try:
        from PIL import Image
        img = Image.open(png_path)
        img.save(output_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return True
    except ImportError:
        # Pillow 不可用，直接用 PNG
        pm.save(output_path.replace('.ico', '.png'), 'PNG')
        return False
