# -*- coding: utf-8 -*-
"""
识别入库视图模块
实现识别类型选择、文件选择、扫描、入库弹窗等全部功能
"""

import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QFileDialog, QMessageBox, QDialog,
    QFormLayout, QLineEdit as QLE, QRadioButton, QButtonGroup,
    QFrame
)

from .widgets import CheckBoxTable, TableToolbar
from .extractors import scan_invoice_folder, extract_excel_invoice
from .database import Database


class ImportDialog(QDialog):
    """入库弹窗对话框"""

    def __init__(self, total_count, in_db_count, valid_amount, is_pdf_mode, parent=None):
        super().__init__(parent)
        self.total_count = total_count
        self.in_db_count = in_db_count
        self.valid_amount = valid_amount
        self.is_pdf_mode = is_pdf_mode
        self.archive_path = ''

        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('入库确认')
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)

        # 顶部提示信息
        if self.in_db_count == 0:
            msg = f'选中了{self.total_count}张发票，合计金额{self.valid_amount:.2f}元'
        else:
            msg = (f'选中了{self.total_count}张发票，'
                   f'其中{self.in_db_count}张已在库，'
                   f'有效合计金额{self.valid_amount:.2f}元')
        lbl_msg = QLabel(msg)
        lbl_msg.setStyleSheet('font-size: 14px; font-weight: bold; padding: 10px;')
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 表单输入
        form_layout = QFormLayout()
        self.edt_type = QLE()
        self.edt_process = QLE()
        self.edt_time = QLE()
        self.edt_dept = QLE()
        self.edt_name = QLE()
        self.edt_remark = QLE()

        form_layout.addRow('发票种类：', self.edt_type)
        form_layout.addRow('流程编号：', self.edt_process)
        form_layout.addRow('时间：', self.edt_time)
        form_layout.addRow('部门：', self.edt_dept)
        form_layout.addRow('姓名：', self.edt_name)
        form_layout.addRow('备注：', self.edt_remark)
        layout.addLayout(form_layout)

        # 归档选项
        if self.is_pdf_mode:
            archive_line = QHBoxLayout()
            self.rb_yes = QRadioButton('是')
            self.rb_no = QRadioButton('否')
            self.rb_no.setChecked(True)
            self.archive_group = QButtonGroup(self)
            self.archive_group.addButton(self.rb_yes)
            self.archive_group.addButton(self.rb_no)

            archive_line.addWidget(QLabel('是否归档至指定位置：'))
            archive_line.addWidget(self.rb_yes)
            archive_line.addWidget(self.rb_no)
            archive_line.addStretch()
            layout.addLayout(archive_line)

            # 归档路径选择行
            self.archive_edit = QLineEdit()
            self.archive_edit.setPlaceholderText('选择归档文件夹...')
            self.archive_edit.setEnabled(False)
            self.btn_archive = QPushButton('浏览')
            self.btn_archive.setEnabled(False)
            self.btn_archive.clicked.connect(self._choose_archive_path)
            self.rb_yes.toggled.connect(self._on_archive_toggled)

            path_line = QHBoxLayout()
            path_line.addWidget(self.archive_edit)
            path_line.addWidget(self.btn_archive)
            layout.addLayout(path_line)

        # 底部按钮
        btn_line = QHBoxLayout()
        btn_line.addStretch()
        btn_ok = QPushButton('确定')
        btn_cancel = QPushButton('取消')
        btn_ok.setFixedWidth(100)
        btn_cancel.setFixedWidth(100)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_line.addWidget(btn_ok)
        btn_line.addWidget(btn_cancel)
        layout.addLayout(btn_line)

    def _on_archive_toggled(self, checked):
        self.archive_edit.setEnabled(checked)
        self.btn_archive.setEnabled(checked)

    def _choose_archive_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择归档文件夹')
        if path:
            self.archive_path = path
            self.archive_edit.setText(path)

    def get_form_data(self):
        """获取表单数据"""
        data = {
            '发票种类': self.edt_type.text().strip(),
            '流程编号': self.edt_process.text().strip(),
            '时间': self.edt_time.text().strip(),
            '部门': self.edt_dept.text().strip(),
            '姓名': self.edt_name.text().strip(),
            '备注': self.edt_remark.text().strip(),
        }
        if self.is_pdf_mode:
            data['archive'] = self.rb_yes.isChecked()
            data['archive_path'] = self.archive_path if data['archive'] else ''
        else:
            data['archive'] = False
            data['archive_path'] = ''
        return data


class ImportView(QWidget):
    """识别入库视图"""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.scan_results = []  # 扫描结果缓存
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ---- 顶部操作行 ----
        top_line = QHBoxLayout()

        top_line.addWidget(QLabel('识别类型：'))
        self.cmb_type = QComboBox()
        self.cmb_type.addItem('电子发票')
        self.cmb_type.addItem('Excel')
        self.cmb_type.setFixedWidth(120)
        self.cmb_type.currentTextChanged.connect(self._on_type_changed)
        top_line.addWidget(self.cmb_type)

        self.btn_select = QPushButton('选择文件')
        self.btn_select.setFixedWidth(100)
        self.btn_select.clicked.connect(self._on_select_file)
        top_line.addWidget(self.btn_select)

        self.edt_path = QLineEdit()
        self.edt_path.setReadOnly(True)
        self.edt_path.setPlaceholderText('请选择文件或文件夹...')
        top_line.addWidget(self.edt_path, 1)

        self.btn_scan = QPushButton('扫描')
        self.btn_scan.setFixedWidth(80)
        self.btn_scan.clicked.connect(self._on_scan)
        top_line.addWidget(self.btn_scan)

        self.btn_import = QPushButton('入库')
        self.btn_import.setFixedWidth(80)
        self.btn_import.clicked.connect(self._on_import)
        top_line.addWidget(self.btn_import)

        layout.addLayout(top_line)

        # ---- 中间表格 ----
        headers = ['文件名称', '发票号码', '金额', '是否在库']
        self.table = CheckBoxTable(headers, amount_col_idx=2)
        layout.addWidget(self.table, 1)

        # ---- 底部工具栏 ----
        self.toolbar = TableToolbar(self.table)
        layout.addWidget(self.toolbar)

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def _on_type_changed(self, text):
        """识别类型变化时清空路径和表格"""
        self.edt_path.clear()
        self.scan_results = []
        self.table.clear_rows()
        self.toolbar.update_info()

    def _on_select_file(self):
        """文件/文件夹选择"""
        id_type = self.cmb_type.currentText()
        if id_type == '电子发票':
            path = QFileDialog.getExistingDirectory(self, '选择电子发票所在文件夹')
            if path:
                self.edt_path.setText(path)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, '选择 Excel 文件', '',
                'Excel 文件 (*.xls *.xlsx)'
            )
            if path:
                self.edt_path.setText(path)

    def _on_scan(self):
        """扫描"""
        path = self.edt_path.text().strip()
        if not path:
            QMessageBox.warning(self, '提示', '请先选择文件或文件夹')
            return

        id_type = self.cmb_type.currentText()
        if id_type == '电子发票':
            if not os.path.isdir(path):
                QMessageBox.warning(self, '提示', '请选择有效的文件夹')
                return
            self.scan_results = scan_invoice_folder(path)
            if not self.scan_results:
                QMessageBox.information(self, '提示', '所选文件夹中未找到 PDF 或 OFD 文件')
                return
        else:
            if not os.path.isfile(path):
                QMessageBox.warning(self, '提示', '请选择有效的 Excel 文件')
                return
            self.scan_results = extract_excel_invoice(path)
            if not self.scan_results:
                QMessageBox.information(self, '提示', '未能从 Excel 文件中提取到发票数据，请确认包含"发票号码"和"金额"列')
                return

        self._refresh_table()

    def _refresh_table(self):
        """刷新表格显示"""
        existing_numbers = self.db.get_existing_invoice_numbers()
        rows = []
        for item in self.scan_results:
            in_db = '是' if item['invoice_number'] and item['invoice_number'] in existing_numbers else '否'
            rows.append([
                item['file_name'],
                item['invoice_number'],
                f"{item['amount']:.2f}",
                in_db,
            ])
        self.table.set_rows(rows)

    def _on_import(self):
        """入库"""
        checked_indices = self.table.get_checked_row_indices()
        if not checked_indices:
            QMessageBox.information(self, '提示', '请先勾选需要入库的记录')
            return

        # 收集勾选记录
        in_db_count = 0
        total_amount = 0.0
        valid_records = []
        for idx in checked_indices:
            row_data = self.table.get_row_data(idx)
            # row_data: [文件名称, 发票号码, 金额, 是否在库]
            file_name = row_data[0]
            invoice_number = row_data[1]
            amount = float(row_data[2]) if row_data[2] else 0.0
            in_db = row_data[3] == '是'

            if in_db:
                in_db_count += 1
            else:
                total_amount += amount
                valid_records.append({
                    'file_name': file_name,
                    'invoice_number': invoice_number,
                    'amount': amount,
                    'row_index': idx,
                })

        if not valid_records:
            QMessageBox.information(self, '提示', '勾选的记录均已入库，无需重复入库')
            return

        total_count = len(checked_indices)
        is_pdf_mode = self.cmb_type.currentText() == '电子发票'

        # 弹出入库确认对话框
        dialog = ImportDialog(total_count, in_db_count, total_amount, is_pdf_mode, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        form_data = dialog.get_form_data()
        source_folder = self.edt_path.text().strip()

        # 执行入库
        for record in valid_records:
            archive_path = ''
            if form_data['archive'] and is_pdf_mode:
                # 移动 PDF 文件到归档目录
                src_path = os.path.join(source_folder, record['file_name'])
                dst_path = os.path.join(form_data['archive_path'], record['file_name'])
                try:
                    if os.path.exists(src_path):
                        shutil.move(src_path, dst_path)
                        archive_path = dst_path
                    elif os.path.exists(dst_path):
                        archive_path = dst_path
                except Exception as e:
                    print(f'[文件移动错误] {src_path} -> {dst_path}: {e}')

            db_record = {
                '发票号码': record['invoice_number'],
                '金额': record['amount'],
                '发票种类': form_data['发票种类'],
                '文件名': record['file_name'],
                '归档路径': archive_path,
                '流程编号': form_data['流程编号'],
                '时间': form_data['时间'],
                '部门': form_data['部门'],
                '姓名': form_data['姓名'],
                '备注': form_data['备注'],
            }
            self.db.insert_record(db_record)

        # 刷新表格（更新是否在库列）
        self._refresh_table()
        QMessageBox.information(self, '成功', f'成功入库 {len(valid_records)} 条记录')
