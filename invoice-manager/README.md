# InvoiceManager - 电子发票管理软件

## 简介

InvoiceManager 是一款基于 Python 3.x + PyQt5 开发的电子发票管理软件，支持 PDF、OFD 电子发票自动识别入库、Excel 批量导入、入库查询、批量编辑/删除、导出 Excel 等功能。

## 功能说明

### 1. 识别入库

- **识别类型**：支持下拉选择「电子发票」或「Excel」
  - 电子发票：选择文件夹，自动扫描其中所有 PDF/OFD文件 文件
  - Excel：选择单个 .xls/.xlsx 文件，读取"发票号码"和"金额"列
- **扫描**：自动提取发票号码和金额，并与数据库比对显示是否在库
- **入库**：勾选记录后点击入库，弹窗填写发票种类、流程编号等信息
  - 电子发票模式支持归档（将文件移动到指定目录）

### 2. 入库查询

- **模糊查询**：支持按发票号码、金额、发票种类等 10 个字段模糊查询
- **导出 Excel**：将查询结果导出为 .xlsx 文件
- **批量编辑**：勾选多条记录，统一修改发票种类、流程编号等字段
- **批量删除**：勾选多条记录，一键删除

## 技术栈

| 组件 | 说明 |
|------|------|
| GUI 框架 | PyQt5 |
| 数据库 | SQLite3（Python 内置） |
| OFD 解析   | ElementTree（Python 内置） |
| PDF 解析   | pdfplumber |
| OCR      | Tesseract |
| Excel 读写 | openpyxl (.xlsx) / xlrd (.xls) |
| 图标生成 | Pillow + QPainter（原创图标，无版权问题） |
| 打包工具 | PyInstaller |

## 运行环境

- Windows 10 / 11 / Windows Server 2012
- Python 3.7+（开发环境）
- 打包后 exe 无需安装 Python

## 快速开始

### 方式一：Python 直接运行

```bash
pip install -r requirements.txt
python main.py
```

### 方式二：打包为 exe

```bash
# 双击 build.bat 或在命令行执行
build.bat
```

打包完成后，exe 文件位于 `dist/InvoiceManager.exe`。

## 数据库说明

程序启动时自动在 exe 同级目录创建 `InvoiceManager.db`（SQLite）

发票数据表 `InvoiceRecords` ：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| 发票号码 | TEXT | 发票号码 |
| 金额 | REAL | 金额 |
| 发票种类 | TEXT | 发票种类 |
| 文件名 | TEXT | PDF 文件名 |
| 归档路径 | TEXT | 归档后的文件路径 |
| 流程编号 | TEXT | 流程编号 |
| 时间 | TEXT | 时间 |
| 部门 | TEXT | 部门 |
| 姓名 | TEXT | 姓名 |
| 备注 | TEXT | 备注 |

参数设置表 `SystemSettings` ：

| 字段 | 类型 | 说明   |
|------|------|------|
| key | TEXT | 参数名  |
| value | TEXT | 参数值  |
| update_time | TEXT | 更新时间 |

## 项目结构

```
InvoiceManager/
├── main.py                # 程序入口
├── requirements.txt       # 依赖列表
├── build.bat              # 打包脚本
├── InvoiceManager.spec  # PyInstaller 配置
├── app_icon.ico           # 打包用程序图标
├── README.md
├── src/                   # 应用源码包
│   ├── __init__.py
│   ├── version.py         # 版本信息
│   ├── main_window.py     # 主窗口（菜单栏 + 标签页）
│   ├── database.py        # 数据库操作
│   ├── extractors.py      # PDF/OFD/Excel 提取器
│   ├── widgets.py         # 自定义表格组件
│   ├── icons.py           # 图标生成（应用图标 + 关闭按钮）
│   ├── import_view.py     # 识别入库视图
│   ├── query_view.py      # 入库查询视图
│   ├── invoice_calc_view.py  # 发票计算视图
│   └── settings_dialog.py # 参数设置对话框
├── docs/                  # 文档
│   ├── 用户操作手册.docx
│   └── 用户操作手册.html
├── tesseract/             # Tesseract OCR 引擎（打包用）
└── .gitignore
```

## 开发环境

推荐使用 PyCharm 打开项目根目录，PyCharm 会自动识别 `src/` 包结构。

```bash
# 安装依赖
pip install -r requirements.txt

# 开发模式运行
python main.py

# 打包为 exe
build.bat
```
