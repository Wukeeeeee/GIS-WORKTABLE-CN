# -*- coding: utf-8 -*-
"""pytest 全局配置：修复 PROJ_LIB / PROJ_DATA 环境冲突（PostGIS 旧 proj.db 覆盖 rasterio）"""
import os
import sys

os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

# 保证以 backend 为工作目录单独运行任一测试文件时，也能 import backend.* 包
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
