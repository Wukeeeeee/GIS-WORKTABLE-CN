# -*- coding: utf-8 -*-
"""Layer 3: GIS 工具集成测试 (GIS Tools Integration Tests)

测试目标：
1. 空间数据处理工具（缓冲区、分级设色、数据查询）；
2. 专题图与可视化生成（execute_python 实际产出图片文件）；
3. 真实/可控测试数据验证；
4. 真实工具执行入口，不 mock 核心空间算法。
"""
import os
import json
import glob
import pytest
import backend.services.tools as gis_tools
from backend.services.tools import (
    datav_boundary,
    spatial_graduated_colors,
    spatial_buffer,
    execute_python,
    _register_layer
)

pytestmark = [pytest.mark.gis_tools, pytest.mark.integration]


def test_gis_tool_datav_boundary_real_or_controlled_execution():
    """验证边界查询工具：返回成功摘要，并以 WGS-84 FeatureCollection 注册到图层快照"""
    # 查询南京市鼓楼区（工具返回可读摘要，边界数据注册进图层快照）
    # 先清空注册表，避免单进程全量跑时被前序测试的同名 stub 图层污染
    gis_tools.reset_registered_layers([])
    res_str = datav_boundary.invoke({"name": "南京市鼓楼区"})
    assert "鼓楼区" in res_str
    assert ("成功" in res_str or "边界" in res_str)

    snap = gis_tools.get_registered_layers_snapshot()
    matched = [s for s in snap if s.get("filename") == "南京市鼓楼区"]
    assert matched, "datav_boundary 未将边界图层注册到图层快照"

    fc = matched[0]["geojson"]
    assert fc.get("type") == "FeatureCollection"
    assert len(fc.get("features", [])) > 0

    feature = fc["features"][0]
    assert feature["geometry"]["type"] in ["Polygon", "MultiPolygon"]
    props = feature.get("properties", {})
    assert "鼓楼" in (props.get("name") or props.get("fullname") or "")

    # 坐标范围应在南京经纬度范围内 (118°E, 32°N 附近)，且为 WGS-84
    coords = feature["geometry"]["coordinates"]

    def _first_point(c):
        """递归取第一个数值坐标对，兼容 Polygon/MultiPolygon/空环"""
        if isinstance(c, (list, tuple)):
            if len(c) >= 2 and all(isinstance(v, (int, float)) for v in c[:2]):
                return c
            for sub in c:
                pt = _first_point(sub)
                if pt:
                    return pt
        return None

    sample_pt = _first_point(coords)
    assert sample_pt, "边界坐标中未找到有效坐标点"
    assert 118.0 < sample_pt[0] < 119.5
    assert 31.5 < sample_pt[1] < 32.5


def test_gis_tool_execute_python_generates_real_image():
    """验证 execute_python 真实执行 Python/Matplotlib 制图，产出真实有效的 PNG 图片"""
    script = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 4))
ax.text(0.5, 0.5, '2025 GDP: 2245.8', ha='center', va='center', fontsize=14)
ax.set_title('Integration Test Card')
output_path = 'output/integration_test_card.png'
plt.savefig(output_path, dpi=100)
plt.close()
print(f'OUTPUT_IMAGE:{output_path}')
"""
    result = execute_python.invoke({"code": script})
    assert "integration_test_card" in result

    # 输出目录需动态读取（init_temp_dir 后才指向临时输出目录，不能在 import 时取值）
    gis_tools.init_temp_dir()
    candidates = glob.glob(os.path.join(gis_tools._temp_output_dir, "*integration_test_card*.png"))
    assert candidates, f"成果文件未在 {gis_tools._temp_output_dir} 实际生成"
    target_file = max(candidates, key=os.path.getmtime)
    assert os.path.getsize(target_file) > 500, "生成的图片文件大小异常"

    # 验证 PNG 文件签名 (Magic Bytes: \x89PNG\r\n\x1a\n)
    with open(target_file, "rb") as f:
        header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n", "文件头不属于标准 PNG 图像"


def test_gis_tool_spatial_graduated_colors_multi_feature(sample_multi_polygon_geojson):
    """验证多要素分级设色工具正常生成渲染样式"""
    _register_layer("nanjing_districts", sample_multi_polygon_geojson)
    res = spatial_graduated_colors.invoke({
        "layer_name": "nanjing_districts",
        "field": "gdp",
        "n_classes": 2
    })
    # 成功生成样式或色阶
    assert "分级" in res or "颜色" in res or "成功" in res or "classes" in res or "graduated" in res.lower()


def test_gis_tool_spatial_graduated_colors_single_feature_graceful_guidance(sample_polygon_geojson):
    """验证单要素分级设色优雅降级，给出建设性建议而非死锁报错"""
    _register_layer("single_district", sample_polygon_geojson)
    res = spatial_graduated_colors.invoke({
        "layer_name": "single_district",
        "field": "gdp"
    })
    # 返回友好指引提示
    assert "单要素" in res or "单个" in res or "建议" in res or "看板" in res
