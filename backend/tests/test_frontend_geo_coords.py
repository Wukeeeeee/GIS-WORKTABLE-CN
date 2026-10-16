"""前端显示转换必须与后端 WGS-84/GCJ-02 约定一致。"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from backend.services.geo_coords import wgs84_to_gcj02


@pytest.fixture(scope="module")
def conversions():
    node = shutil.which("node")
    if not node:
        pytest.skip("坐标前端验证需要 Node.js")
    source = Path(__file__).resolve().parents[2] / "frontend/js/geo_coords.js"
    script = """
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const coords = context.window.GIS.coords;
const points = [[120.405294,30.239492], [121.4737,31.2304],
                [116.3974,39.9093], [113.2644,23.1291],
                [-74.006,40.7128], [139.6917,35.6895]];
console.log(JSON.stringify(points.map(point => {
  const gcj = coords.wgs84ToGcj02(...point);
  return {point, gcj, back: coords.gcj02ToWgs84(...gcj)};
})));
"""
    result = subprocess.run(
        [node, "-e", script, str(source)], capture_output=True,
        text=True, encoding="utf-8", check=True, timeout=20,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("index", range(4))
def test_display_conversion_matches_backend(conversions, index):
    sample = conversions[index]
    assert sample["gcj"] == pytest.approx(wgs84_to_gcj02(*sample["point"]), abs=1e-10)
    assert sample["back"] == pytest.approx(sample["point"], abs=1e-9)


@pytest.mark.parametrize("index", [4, 5])
def test_display_does_not_shift_overseas_coordinates(conversions, index):
    sample = conversions[index]
    assert sample["gcj"] == sample["point"] == sample["back"]
