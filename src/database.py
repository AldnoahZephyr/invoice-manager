# -*- coding: utf-8 -*-
"""
数据库操作模块
负责 SQLite 数据库的初始化、增删改查等操作
"""

import os
import sys
import sqlite3


def get_base_dir():
    """获取程序所在目录（兼容 PyInstaller 打包后的 exe）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # __file__ 位于 src/database.py，向上一级到项目根目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path():
    """获取数据库文件路径"""
    return os.path.join(get_base_dir(), 'InvoiceManager.db')


class Database:
    """数据库管理类"""

    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else get_db_path()
        self._init_db()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库，创建表结构"""
        conn = self._get_conn()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS InvoiceRecords (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    发票号码    TEXT,
                    金额        REAL,
                    发票种类    TEXT,
                    文件名      TEXT,
                    归档路径    TEXT,
                    流程编号    TEXT,
                    时间        TEXT,
                    部门        TEXT,
                    姓名        TEXT,
                    备注        TEXT
                )
            ''')
            # 系统参数设置表（键值对存储，如 Tesseract 路径等）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS SystemSettings (
                    key         TEXT PRIMARY KEY,
                    value       TEXT,
                    update_time TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 系统参数读写
    # ------------------------------------------------------------------

    def get_setting(self, key, default=''):
        """获取系统参数值，不存在则返回 default"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                'SELECT value FROM SystemSettings WHERE key = ?', (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else default
        finally:
            conn.close()

    def set_setting(self, key, value):
        """设置系统参数值（存在则更新）"""
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = self._get_conn()
        try:
            conn.execute('''
                INSERT INTO SystemSettings (key, value, update_time)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    update_time = excluded.update_time
            ''', (key, str(value), now))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 查询操作
    # ------------------------------------------------------------------

    def get_existing_invoice_numbers(self):
        """获取数据库中所有发票号码集合，用于判断是否在库"""
        conn = self._get_conn()
        try:
            cursor = conn.execute('SELECT 发票号码 FROM InvoiceRecords')
            return {row['发票号码'] for row in cursor.fetchall() if row['发票号码']}
        finally:
            conn.close()

    def query_records(self, conditions):
        """
        模糊查询记录
        conditions: dict，键为字段名，值为查询关键字（空字符串表示不限制）
        """
        sql = 'SELECT * FROM InvoiceRecords WHERE 1=1'
        params = []
        field_map = {
            '发票号码': '发票号码', 'invoice_number': '发票号码',
            '金额': '金额', 'amount': '金额',
            '发票种类': '发票种类', 'invoice_type': '发票种类',
            '文件名': '文件名', 'filename': '文件名',
            '归档路径': '归档路径', 'archive_path': '归档路径',
            '流程编号': '流程编号', 'process_number': '流程编号',
            '时间': '时间', 'time': '时间',
            '部门': '部门', 'department': '部门',
            '姓名': '姓名', 'name': '姓名',
            '备注': '备注', 'remark': '备注',
        }
        for field, value in conditions.items():
            if field in field_map and value and value.strip():
                col = field_map[field]
                sql += f' AND CAST("{col}" AS TEXT) LIKE ?'
                params.append(f'%{value.strip()}%')
        sql += ' ORDER BY id DESC'
        conn = self._get_conn()
        try:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 插入操作
    # ------------------------------------------------------------------

    # 字段名中英文映射（英文 -> 中文）
    FIELD_ALIAS = {
        'invoice_number': '发票号码',
        'amount': '金额',
        'invoice_type': '发票种类',
        'filename': '文件名',
        'archive_path': '归档路径',
        'process_number': '流程编号',
        'time': '时间',
        'department': '部门',
        'name': '姓名',
        'remark': '备注',
    }

    def _get_field(self, record, cn_name, default=''):
        """从 record 中获取字段值，兼容中英文键名"""
        if cn_name in record:
            return record[cn_name]
        for en, cn in self.FIELD_ALIAS.items():
            if cn == cn_name and en in record:
                return record[en]
        return default

    def insert_record(self, record):
        """
        插入一条记录
        record: dict，键名支持中文（发票号码、金额...）或英文（invoice_number、amount...）
        """
        conn = self._get_conn()
        try:
            conn.execute('''
                INSERT INTO InvoiceRecords
                    (发票号码, 金额, 发票种类, 文件名, 归档路径, 流程编号, 时间, 部门, 姓名, 备注)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self._get_field(record, '发票号码', ''),
                self._get_field(record, '金额', 0.0),
                self._get_field(record, '发票种类', ''),
                self._get_field(record, '文件名', ''),
                self._get_field(record, '归档路径', ''),
                self._get_field(record, '流程编号', ''),
                self._get_field(record, '时间', ''),
                self._get_field(record, '部门', ''),
                self._get_field(record, '姓名', ''),
                self._get_field(record, '备注', ''),
            ))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 批量操作
    # ------------------------------------------------------------------

    def batch_update(self, ids, fields):
        """
        批量更新记录
        ids: list[int]，要更新的记录ID列表
        fields: dict，要更新的字段和值
        """
        if not ids:
            return
        allowed = ['发票种类', '流程编号', '时间', '部门', '姓名', '备注']
        set_clauses = []
        params = []
        for field in allowed:
            if field in fields:
                set_clauses.append(f'"{field}" = ?')
                params.append(fields[field])
        if not set_clauses:
            return
        placeholders = ','.join('?' * len(ids))
        sql = f'UPDATE InvoiceRecords SET {", ".join(set_clauses)} WHERE id IN ({placeholders})'
        params.extend(ids)
        conn = self._get_conn()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def batch_delete(self, ids):
        """批量删除记录"""
        if not ids:
            return
        placeholders = ','.join('?' * len(ids))
        sql = f'DELETE FROM InvoiceRecords WHERE id IN ({placeholders})'
        conn = self._get_conn()
        try:
            conn.execute(sql, ids)
            conn.commit()
        finally:
            conn.close()
