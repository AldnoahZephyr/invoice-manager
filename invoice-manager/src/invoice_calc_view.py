# -*- coding: utf-8 -*-
"""
发票计算视图 —— PyQt5 复写
双表格界面：待选发票 / 已选发票，支持贪心智能计算
修复 tkinter 原版 bug：排序后勾选状态不会错乱
UI 风格统一：使用全局 APP_STYLE，不再自定彩色样式
"""

import os
import traceback
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QMessageBox, QFileDialog, QSplitter, QSizePolicy,
)

from .widgets import CheckBoxTable
from .extractors import extract_invoice


# ── 表格标题行（含全选/取消按钮）───────────────────────────────

class TableTitleBar(QWidget):
    """表格标题栏：标题文字 + 全选/取消按钮"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #333; padding: 4px 0;")
        layout.addWidget(title_label)

        layout.addStretch()

        self.btn_all = QPushButton('全选')
        self.btn_none = QPushButton('取消')
        self.btn_all.setFixedWidth(60)
        self.btn_none.setFixedWidth(60)
        layout.addWidget(self.btn_all)
        layout.addWidget(self.btn_none)


# ── 发票面板 ───────────────────────────────────────────────

class InvoicePanel(QWidget):
    """单个面板：表格 + 底部合计"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._title = title

        headers = ['文件名称', '发票号码', '发票金额']
        self.table = CheckBoxTable(headers, amount_col_idx=2)
        self._data: list = []          # 当前面板对应的原始数据列表
        self._title_bar = TableTitleBar(title)

        # 连接全选/取消
        self._title_bar.btn_all.clicked.connect(self.table.select_all)
        self._title_bar.btn_none.clicked.connect(self.table.deselect_all)

        # 底部合计 —— 简洁风格
        self._total_label = QLabel('¥ 0.00')
        self._total_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #333; padding: 2px 6px;"
        )
        self._total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._title_bar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self._total_label)

        # 信号：勾选变化 → 刷新合计
        self.table.check_changed.connect(self._refresh_total)

    def _refresh_total(self):
        self._total_label.setText(
            f'{self._title}合计: ¥ {self._sum_data():.2f}'
        )

    # ── 数据访问 ──────────────────────────────────────────

    def load_data(self, data):
        """
        加载数据到表格
        data: list[dict]，每个 dict 包含 display_name, invoice_no, amount, path
        
        修复排序后移动错乱（彻底方案）：
        - UserRole 中存储文件路径（唯一标识），而非 _data 索引
        - 排序后通过路径匹配 _data，不再依赖索引映射
        - 禁用排序后加载，确保 UserRole 在插入顺序下赋值
        - 重新启用排序后，items 携带路径值随排序移动，不会错乱
        """
        self._data = list(data)
        rows = [[
            d['display_name'],
            d['invoice_no'] or '(未识别)',
            str(d['amount'].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        ] for d in data]

        # 禁用排序 → 清除之前的排序指示器
        self.table.setSortingEnabled(False)
        self.table.set_rows(rows)
        # set_rows 内部会重新启用排序，再次禁用确保行序与 _data 一致
        self.table.setSortingEnabled(False)

        # 在插入顺序下设置 UserRole（存文件路径，而非索引）
        # 路径是唯一标识，排序后通过路径内容匹配 _data，彻底避免索引错乱
        self.table.blockSignals(True)
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                item.setData(Qt.UserRole, self._data[i]['path'])
        self.table.blockSignals(False)

        # 重新启用排序，路径值随 items 移动不会错乱
        self.table.setSortingEnabled(True)
        self._refresh_total()

    def _sum_data(self):
        return sum(
            (d['amount'] for d in self._data),
            start=Decimal('0')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_checked_data_indices(self):
        """
        获取被勾选行对应的 _data 索引列表
        通过 UserRole 中存储的文件路径匹配 _data，排序后不会错乱
        """
        checked_paths = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                path = item.data(Qt.UserRole)
                if path is not None:
                    checked_paths.add(path)

        indices = []
        for i, d in enumerate(self._data):
            if d['path'] in checked_paths:
                indices.append(i)
        return indices

    def get_checked_count(self):
        return self.table.get_checked_count()

    def get_data_count(self):
        return len(self._data)

    @property
    def data(self):
        return self._data


# ── 主视图 ──────────────────────────────────────────────────

class InvoiceCalcView(QWidget):
    """发票计算主视图"""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._folder = ''
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── 顶部工具栏 ──
        top_bar = QHBoxLayout()

        btn_folder = QPushButton('选择文件夹')
        btn_folder.clicked.connect(self._choose_folder)
        top_bar.addWidget(btn_folder)

        self._folder_label = QLabel('未选择文件夹')
        self._folder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_bar.addWidget(self._folder_label)

        btn_refresh = QPushButton('刷新')
        btn_refresh.clicked.connect(self._refresh)
        top_bar.addWidget(btn_refresh)

        top_bar.addSpacing(20)

        top_bar.addWidget(QLabel('目标金额:'))
        self._target_input = QLineEdit()
        self._target_input.setFixedWidth(100)
        self._target_input.setAlignment(Qt.AlignRight)
        self._target_input.textChanged.connect(self._update_remain)
        self._target_input.setPlaceholderText('0.00')
        top_bar.addWidget(self._target_input)

        top_bar.addSpacing(12)

        top_bar.addWidget(QLabel('剩余金额:'))
        self._remain_input = QLineEdit()
        self._remain_input.setFixedWidth(100)
        self._remain_input.setAlignment(Qt.AlignRight)
        self._remain_input.setReadOnly(True)
        top_bar.addWidget(self._remain_input)

        top_bar.addSpacing(12)

        btn_calc = QPushButton('计算')
        btn_calc.clicked.connect(self._auto_calculate)
        top_bar.addWidget(btn_calc)

        layout.addLayout(top_bar)

        # ── 分隔线 ──
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # ── 中部：双表格 + 方向按钮 ──
        splitter = QSplitter(Qt.Horizontal)

        # 左侧面板 —— 待选发票
        self._left_panel = InvoicePanel('待选发票')
        splitter.addWidget(self._left_panel)

        # 中间方向按钮
        btn_frame = QWidget()
        btn_layout = QVBoxLayout(btn_frame)
        btn_layout.setAlignment(Qt.AlignCenter)

        btn_right = QPushButton('→')
        btn_right.setFixedSize(40, 40)
        btn_right.clicked.connect(self._move_left_to_right)
        btn_layout.addWidget(btn_right)

        btn_left = QPushButton('←')
        btn_left.setFixedSize(40, 40)
        btn_left.clicked.connect(self._move_right_to_left)
        btn_layout.addWidget(btn_left)

        splitter.addWidget(btn_frame)

        # 右侧面板 —— 已选发票
        self._right_panel = InvoicePanel('已选发票')
        splitter.addWidget(self._right_panel)

        # 初始比例 1:0:1（中间固定宽度）
        splitter.setSizes([500, 60, 500])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)

        layout.addWidget(splitter, 1)

        # ── 底部状态信息 ──
        self._status = QLabel('就绪')
        self._status.setStyleSheet("color: #666; padding: 2px 6px;")
        layout.addWidget(self._status)

    # ── 文件夹扫描 ─────────────────────────────────────────

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择发票文件夹')
        if folder:
            self._folder = folder
            self._folder_label.setText(folder)
            self._refresh()

    def _refresh(self):
        if not self._folder or not os.path.isdir(self._folder):
            QMessageBox.warning(self, '提示', '请先选择有效的文件夹')
            return

        self._status.setText('正在扫描，请稍候…')

        # 使用 QObject + pyqtSignal 安全地将结果从后台线程传回主线程
        self._scanner = _ScanWorker(self._folder)
        self._scanner.finished.connect(self._on_scan_done)
        self._scanner.error_occurred.connect(self._on_scan_error)
        self._scanner.start()

    def _on_scan_done(self, data):
        """扫描完成回调（运行在主线程，安全地更新 UI）"""
        self._status.setText(f'共扫描到 {len(data)} 张发票')
        self._left_panel.load_data(data)
        self._right_panel.load_data([])
        self._update_remain()

    def _on_scan_error(self, err_msg):
        """扫描出错回调"""
        self._status.setText('扫描失败')
        QMessageBox.warning(self, '扫描错误', f'扫描过程出错：\n{err_msg}')

    # ── 移动操作 ────────────────────────────────────────────

    def _move_left_to_right(self):
        """待选 → 已选"""
        if self._left_panel.get_checked_count() == 0:
            QMessageBox.information(self, '提示', '请先在左侧表格中勾选要移动的发票行')
            return

        indices = self._left_panel.get_checked_data_indices()
        indices.sort(reverse=True)

        moved = []
        stay = list(self._left_panel.data)
        for idx in indices:
            moved.append(stay.pop(idx))

        self._left_panel.load_data(stay)
        self._right_panel.load_data(self._right_panel.data + moved)
        self._update_remain()
        self._status.setText(f'已移动 {len(moved)} 张发票至右侧')

    def _move_right_to_left(self):
        """已选 → 待选"""
        if self._right_panel.get_checked_count() == 0:
            QMessageBox.information(self, '提示', '请先在右侧表格中勾选要移动的发票行')
            return

        indices = self._right_panel.get_checked_data_indices()
        indices.sort(reverse=True)

        moved = []
        stay = list(self._right_panel.data)
        for idx in indices:
            moved.append(stay.pop(idx))

        self._right_panel.load_data(stay)
        self._left_panel.load_data(self._left_panel.data + moved)
        self._update_remain()
        self._status.setText(f'已移动 {len(moved)} 张发票至左侧')

    # ── 金额计算 ────────────────────────────────────────────

    def _update_remain(self):
        try:
            target = Decimal(self._target_input.text())
        except Exception:
            self._remain_input.setText('0.00')
            return
        right_sum = sum((d['amount'] for d in self._right_panel.data), start=Decimal('0'))
        remain = target - right_sum if target else Decimal('0')
        self._remain_input.setText(
            str(remain.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        )

    def _auto_calculate(self):
        try:
            target = Decimal(self._target_input.text())
            if target <= 0:
                raise ValueError
        except Exception:
            QMessageBox.warning(self, '提示', '请输入有效的目标金额（正数）')
            return

        all_data = self._left_panel.data + self._right_panel.data
        total = sum(d['amount'] for d in all_data)

        if total < target:
            self._right_panel.load_data(all_data)
            self._left_panel.load_data([])
            QMessageBox.information(
                self, '计算结果',
                f'发票总额 ¥{total:.2f} 小于目标金额 ¥{target:.2f}，'
                f'已将全部 {len(all_data)} 张发票移至右侧。'
            )
        else:
            sel_idx = _smart_select(all_data, target)
            sel_set = set(sel_idx)
            new_right = [all_data[i] for i in sorted(sel_set)]
            new_left = [all_data[i] for i in range(len(all_data)) if i not in sel_set]
            right_sum = sum(d['amount'] for d in new_right)
            self._right_panel.load_data(new_right)
            self._left_panel.load_data(new_left)
            QMessageBox.information(
                self, '计算结果',
                f'已选 {len(new_right)} 张发票移至右侧，\n'
                f'现有金额 ¥{right_sum:.2f} ≥ 目标金额 ¥{target:.2f}。'
            )

        self._update_remain()
        self._status.setText(
            f'计算完成 —— 左侧 {self._left_panel.get_data_count()} 张，'
            f'右侧 {self._right_panel.get_data_count()} 张'
        )


# ── 线程安全的扫描 Worker ──────────────────────────────────

class _ScanWorker(QObject):
    """后台扫描，通过信号将结果安全传回主线程"""
    finished = pyqtSignal(list)          # 扫描完成，携带数据列表
    error_occurred = pyqtSignal(str)     # 扫描出错，携带错误信息

    def __init__(self, folder):
        super().__init__()
        self._folder = folder

    def start(self):
        """启动后台线程执行扫描"""
        import threading
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        """在后台线程中执行，只做文件 I/O，不碰任何 UI 控件"""
        try:
            data = _scan_folder(self._folder)
            self.finished.emit(data)         # pyqtSignal 是线程安全的
        except Exception:
            self.error_occurred.emit(traceback.format_exc())


def _scan_folder(folder):
    """递归扫描文件夹，提取所有 PDF/OFD 发票信息"""
    results = []
    folder = os.path.normpath(folder)
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for fname in sorted(files):
            ext = fname.lower()
            if not (ext.endswith('.pdf') or ext.endswith('.ofd')):
                continue
            full_path = os.path.join(root, fname)
            rel = os.path.relpath(full_path, folder)
            try:
                invoice_no, amount = extract_invoice(full_path)
                amount_d = Decimal(str(amount))
            except Exception:
                # 单个文件解析失败不中断整体扫描
                invoice_no = ''
                amount_d = Decimal('0')
            results.append({
                'display_name': rel,
                'invoice_no': invoice_no,
                'amount': amount_d,
                'path': full_path,
            })
    return results


def _smart_select(items, target):
    """贪心选取最少数量的发票使 total >= target"""
    total = sum(it['amount'] for it in items)
    if total < target:
        return list(range(len(items)))
    sorted_idx = sorted(
        range(len(items)),
        key=lambda i: items[i]['amount'],
        reverse=True
    )
    selected, running = [], Decimal('0')
    for idx in sorted_idx:
        selected.append(idx)
        running += items[idx]['amount']
        if running >= target:
            break
    return selected
