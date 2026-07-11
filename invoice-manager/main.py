# -*- coding: utf-8 -*-
"""
InvoiceManager - 电子发票管理软件
程序入口
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.main_window import MainWindow
from src.icons import get_app_icon


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('InvoiceManager')
    app.setWindowIcon(get_app_icon())

    # 设置中文字体
    font = app.font()
    font.setFamily('Microsoft YaHei')
    font.setPointSize(9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
