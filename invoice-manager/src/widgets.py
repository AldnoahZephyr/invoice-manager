# -*- coding: utf-8 -*-
"""
自定义表格组件模块
提供带复选框、全选/反选、排序、序号、合计功能的 QTableWidget
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget,
    QHBoxLayout, QPushButton, QLabel, QAbstractItemView, QHeaderView
)


class NumericTableWidgetItem(QTableWidgetItem):
    """数值型表格项，确保按数值大小排序而非字符串排序"""

    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except (ValueError, TypeError):
            return super().__lt__(other)


class CheckBoxTable(QTableWidget):
    """
    带复选框的自定义表格
    - 第 0 列为复选框列
    - 第 1 列为序号列（自动编号，排序后自动重排）
    - 支持全选/反选
    - 支持列名点击排序（排序后复选框状态跟随行数据）
    - 底部合计标签
    """

    check_changed = pyqtSignal()

    def __init__(self, headers, amount_col_idx=None, parent=None):
        """
        headers: list[str]，表头列表（不含复选框和序号列，内部自动添加）
        amount_col_idx: int，金额列在 headers 中的索引（用于合计），None 则不合计
        """
        self._data_headers = headers
        self._amount_col_idx = amount_col_idx
        # 实际列：复选框 + 序号 + 数据列
        full_headers = ['', '序号'] + headers
        super().__init__(0, len(full_headers), parent)

        self._is_updating = False  # 防止递归更新的标志

        self._init_ui(full_headers)
        self._connect_signals()

    def _init_ui(self, headers):
        """初始化表格外观"""
        self.setHorizontalHeaderLabels(headers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)

        header = self.horizontalHeader()
        # 复选框 + 序号列：固定宽度
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 36)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 50)
        # 数据列：自适应宽度，加载数据后自动 resizeColumnsToContents
        for i in range(2, self.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        header.setStretchLastSection(True)

        # 复选框列和序号列不可排序
        header.setSectionsClickable(True)

    def _connect_signals(self):
        """连接信号"""
        self.itemChanged.connect(self._on_item_changed)
        self.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)

    # ------------------------------------------------------------------
    # 数据操作
    # ------------------------------------------------------------------

    def set_rows(self, rows_data):
        """
        批量设置表格数据
        rows_data: list of list，每个子列表对应一行数据列的值（不含复选框和序号）
        """
        self._is_updating = True
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setRowCount(len(rows_data))

        for row_idx, row_data in enumerate(rows_data):
            self._insert_row(row_idx, row_data)

        self.setSortingEnabled(True)
        self._is_updating = False
        self._update_serial_numbers()
        self.resizeColumnsToContents()
        self.check_changed.emit()

    def add_row(self, row_data):
        """添加一行数据"""
        self._is_updating = True
        row_idx = self.rowCount()
        self.insertRow(row_idx)
        self._insert_row(row_idx, row_data)
        self._is_updating = False
        self._update_serial_numbers()
        self.check_changed.emit()

    def _insert_row(self, row_idx, row_data):
        """在指定行插入数据"""
        # 复选框列
        cb_item = QTableWidgetItem()
        cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        cb_item.setCheckState(Qt.Unchecked)
        self.setItem(row_idx, 0, cb_item)

        # 序号列（稍后统一更新）
        sn_item = NumericTableWidgetItem()
        sn_item.setFlags(Qt.ItemIsEnabled)
        sn_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row_idx, 1, sn_item)

        # 数据列
        for col_idx, value in enumerate(row_data):
            real_col = col_idx + 2
            if self._amount_col_idx is not None and col_idx == self._amount_col_idx:
                item = NumericTableWidgetItem()
                try:
                    item.setText(f'{float(value):.2f}')
                except (ValueError, TypeError):
                    item.setText(str(value))
            else:
                item = QTableWidgetItem(str(value) if value is not None else '')
            item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row_idx, real_col, item)

    def clear_rows(self):
        """清空表格"""
        self._is_updating = True
        self.setRowCount(0)
        self._is_updating = False
        self.check_changed.emit()

    # ------------------------------------------------------------------
    # 复选框操作
    # ------------------------------------------------------------------

    def _on_item_changed(self, item):
        """复选框状态变化时的回调"""
        if self._is_updating:
            return
        if item.column() == 0:
            self.check_changed.emit()

    def select_all(self):
        """全选"""
        self._is_updating = True
        for i in range(self.rowCount()):
            item = self.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self._is_updating = False
        self.check_changed.emit()

    def invert_selection(self):
        """反选"""
        self._is_updating = True
        for i in range(self.rowCount()):
            item = self.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        self._is_updating = False
        self.check_changed.emit()

    def deselect_all(self):
        """取消全选"""
        self._is_updating = True
        for i in range(self.rowCount()):
            item = self.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self._is_updating = False
        self.check_changed.emit()

    def get_checked_row_indices(self):
        """获取所有勾选行的索引列表"""
        return [i for i in range(self.rowCount())
                if self.item(i, 0) and self.item(i, 0).checkState() == Qt.Checked]

    def get_checked_count(self):
        """获取勾选行数"""
        return len(self.get_checked_row_indices())

    # ------------------------------------------------------------------
    # 排序与序号
    # ------------------------------------------------------------------

    def _on_sort_changed(self):
        """排序变化后重新编号序号"""
        self._is_updating = True
        self._update_serial_numbers()
        self._is_updating = False

    def _update_serial_numbers(self):
        """重新编号所有行的序号"""
        for i in range(self.rowCount()):
            item = self.item(i, 1)
            if item:
                item.setText(str(i + 1))

    # ------------------------------------------------------------------
    # 合计
    # ------------------------------------------------------------------

    def get_amount_total(self, checked_only=False):
        """获取金额合计"""
        total = 0.0
        for i in range(self.rowCount()):
            if checked_only:
                item_cb = self.item(i, 0)
                if not item_cb or item_cb.checkState() != Qt.Checked:
                    continue
            if self._amount_col_idx is not None:
                real_col = self._amount_col_idx + 2
                item = self.item(i, real_col)
                if item:
                    try:
                        total += float(item.text())
                    except (ValueError, TypeError):
                        pass
        return total

    def get_row_data(self, row_idx):
        """获取指定行的数据列值列表（不含复选框和序号）"""
        data = []
        for col in range(2, self.columnCount()):
            item = self.item(row_idx, col)
            data.append(item.text() if item else '')
        return data

    def get_row_count(self):
        """获取数据行数"""
        return self.rowCount()


class TableToolbar(QWidget):
    """表格操作工具栏：全选、反选、取消选择 + 合计信息"""

    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self._init_ui()
        table.check_changed.connect(self.update_info)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_all = QPushButton('全选')
        btn_invert = QPushButton('反选')
        btn_none = QPushButton('取消选择')
        btn_all.setFixedWidth(80)
        btn_invert.setFixedWidth(80)
        btn_none.setFixedWidth(90)

        btn_all.clicked.connect(self.table.select_all)
        btn_invert.clicked.connect(self.table.invert_selection)
        btn_none.clicked.connect(self.table.deselect_all)

        self.info_label = QLabel()

        layout.addWidget(btn_all)
        layout.addWidget(btn_invert)
        layout.addWidget(btn_none)
        layout.addStretch()
        layout.addWidget(self.info_label)

    def update_info(self):
        """更新合计信息"""
        total = self.table.get_amount_total()
        checked_total = self.table.get_amount_total(checked_only=True)
        count = self.table.get_row_count()
        checked_count = self.table.get_checked_count()
        self.info_label.setText(
            f'共 {count} 条记录，合计金额: ¥{total:.2f}  |  '
            f'已勾选 {checked_count} 条，勾选合计: ¥{checked_total:.2f}'
        )
