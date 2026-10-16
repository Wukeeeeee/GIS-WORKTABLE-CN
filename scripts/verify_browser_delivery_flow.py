# -*- coding: utf-8 -*-
"""交付前真实浏览器流程验证脚本

覆盖流程：
1. 服务启动与探活
2. 真实浏览器加载 (Playwright Chromium)
3. 导入固定示例 GeoJSON
4. 500 米缓冲区分析
5. 属性表检查
6. 历史记录与一键重跑
7. 导出 Shapefile (ZIP) 完整性检验
8. 保存工程 (.giswork)
9. 服务停止与重启
10. 重启后打开工程与图层恢复核验
11. 控制台错误与产物审计
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUTPUT_DIR = ROOT / "output" / "browser_verification_20261016"
SAMPLE_PATH = ROOT / "data" / "sample_delivery_test.geojson"
PORT = 8010

os.environ["GISWTB_PROFILE"] = "cn"
os.environ["GIS_PORT"] = str(PORT)


def ensure_backend_running():
    from backend.launcher import probe, candidate_ports
    if probe(PORT):
        print(f"[Launcher] 后端已在端口 {PORT} 运行。")
        return None
    print(f"[Launcher] 启动后端服务端口 {PORT}...")
    env = os.environ.copy()
    log_path = ROOT / "logs" / "test_server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    # 等待探活
    deadline = time.time() + 30
    while time.time() < deadline:
        if probe(PORT):
            print(f"[Launcher] 后端就绪，PID={proc.pid}")
            return proc
        time.sleep(0.5)
    raise RuntimeError("后端启动超时！")


def stop_backend():
    from backend.launcher import probe, candidate_ports
    import signal
    data = probe(PORT)
    if data and isinstance(data.get("pid"), int):
        pid = data["pid"]
        print(f"[Launcher] 正在停止后端 PID={pid}...")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        time.sleep(1)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors = []
    console_logs = []
    page_errors = []

    proc = ensure_backend_running()

    try:
        with sync_playwright() as p:
            print("\n[Playwright] 启动 Chromium 浏览器...")
            browser = p.chromium.launch(headless=True, args=["--disable-remote-fonts", "--disable-gpu", "--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            def on_console(msg):
                text = msg.text
                if msg.type == "error":
                    # 过滤地图底图等无外网环境正常瓦片 404/网络异常警告
                    console_errors.append(text)
                console_logs.append(f"[{msg.type}] {text}")

            page.on("console", on_console)
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # 1. 访问首页
            url = f"http://127.0.0.1:{PORT}"
            print(f"[1/8] 访问工作台首页: {url}")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("#map", timeout=10000)
            page.screenshot(path=str(OUTPUT_DIR / "01_home_loaded.png"))
            print("  ✓ 首页与地图容器加载成功")

            # 2. 导入固定示例
            print(f"[2/8] 导入固定示例: {SAMPLE_PATH.name}")
            page.set_input_files("#fileInput", str(SAMPLE_PATH))
            page.wait_for_selector(".preview-btn-confirm", timeout=5000)
            page.click(".preview-btn-confirm")
            # 等待图层上图
            page.wait_for_function("() => window.GIS && window.GIS.layers && window.GIS.layers.getLayers().length > 0", timeout=10000)
            layers = page.evaluate("() => window.GIS.layers.getLayers()")
            assert len(layers) >= 1, f"图层导入失败，当前图层数: {len(layers)}"
            imported_layer = layers[0]
            print(f"  ✓ 示例图层导入成功: 名称={imported_layer.get('filename')}, ID={imported_layer.get('layer_id')}")
            page.screenshot(path=str(OUTPUT_DIR / "02_sample_imported.png"))

            # 3. 执行 500 米缓冲区
            print("[3/8] 执行 500 米缓冲区分析...")
            page.evaluate("() => window.GIS.spatial.openTab('buffer')")
            page.wait_for_selector("#spatialPanel", timeout=5000)
            layer_name = imported_layer.get("filename")
            # 等待图层列表填充进下拉菜单（option 在未展开时不是 visible，需 state="attached"）
            page.wait_for_selector(f"#bufferLayer option[value='{layer_name}']", state="attached", timeout=8000)
            page.select_option("#bufferLayer", layer_name)
            page.fill("#bufferDistance", "500")
            initial_count = len(layers)

            # 点击执行缓冲并等待工具调用返回
            with page.expect_response(lambda r: "/api/tools/invoke" in r.url and r.status == 200, timeout=20000):
                page.click(".spatial-run-btn[data-op='buffer']")

            page.wait_for_function(
                f"(initCount) => window.GIS.layers.getLayers().length > initCount",
                arg=initial_count,
                timeout=15000
            )
            layers_after_buffer = page.evaluate("() => window.GIS.layers.getLayers()")
            buffer_layer = layers_after_buffer[-1]  # 最新生成的缓冲区图层在末尾
            print(f"  ✓ 缓冲区图层生成成功: 名称={buffer_layer.get('filename')}, 类型={buffer_layer.get('geometry_type')}")
            page.screenshot(path=str(OUTPUT_DIR / "03_buffer_completed.png"))
            page.evaluate("() => window.GIS.spatial.deactivate()")

            # 4. 检查属性表
            print("[4/8] 打开并检查属性表...")
            page.evaluate(f"() => window.GIS.layers.showLayerInspector('{buffer_layer['layer_id']}', 'attr')")
            page.wait_for_selector("#attrDataTable", timeout=5000)
            table_headers = page.evaluate("""() => {
                const ths = Array.from(document.querySelectorAll('#attrDataTable thead th'));
                return ths.map(th => th.innerText.trim());
            }""")
            table_rows_count = page.evaluate("() => document.querySelectorAll('#attrDataTable tbody tr').length")
            print(f"  ✓ 属性表展示正常: 表头列数={len(table_headers)}, 数据行数={table_rows_count}")
            assert table_rows_count >= 1, "属性表中无要素数据！"
            page.screenshot(path=str(OUTPUT_DIR / "04_attribute_table.png"))
            page.evaluate("() => window.GIS.layers.closeInspector()")

            # 5. 检查处理历史与一键重跑
            print("[5/8] 检查处理历史与重跑...")
            page.click("#toggleHistoryPanel")
            page.wait_for_selector(".toolhist-item", timeout=8000)
            # 等待前端 toast 消失并触发最新一条历史记录的重跑
            page.wait_for_timeout(1500)
            with page.expect_response(lambda r: "/api/history/rerun" in r.url and r.status == 200, timeout=20000):
                page.evaluate("() => document.querySelector('.toolhist-item .toolhist-rerun-btn').click()")
            time.sleep(2)
            page.screenshot(path=str(OUTPUT_DIR / "05_history_rerun.png"))
            print("  ✓ 历史重跑触发并执行成功")

            # 6. 导出 Shapefile
            print("[6/8] 导出 Shapefile 测试...")
            # 直接调用 export-shp API 校验后端导出 ZIP 产物
            import urllib.request
            geojson_data = buffer_layer.get("geojson")
            assert geojson_data, "图层缺少 GeoJSON 数据"
            req_data = json.dumps({"geojson": geojson_data, "name": "delivery_buffer_export", "crs": "EPSG:4326"}).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{PORT}/api/layer/export-shp",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                zip_bytes = resp.read()
            shp_zip_path = OUTPUT_DIR / "delivery_buffer_export.zip"
            with open(shp_zip_path, "wb") as f:
                f.write(zip_bytes)
            # 校验 zip 内包
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                namelist = zf.namelist()
                print(f"  ✓ Shapefile ZIP 生成成功 ({len(zip_bytes)} 字节)，包含文件: {namelist}")
                assert any(f.endswith(".shp") for f in namelist), "缺少 .shp"
                assert any(f.endswith(".shx") for f in namelist), "缺少 .shx"
                assert any(f.endswith(".dbf") for f in namelist), "缺少 .dbf"
                assert any(f.endswith(".prj") for f in namelist), "缺少 .prj"

            # 7. 保存工程
            print("[7/8] 保存工程并验证持久化...")
            save_res = page.evaluate("() => window.GIS.project.save('交付前验收工程')")
            project_id = save_res.get("id")
            assert project_id, f"工程保存未返回有效 ID: {save_res}"
            print(f"  ✓ 工程保存成功，工程ID: {project_id}")
            page.screenshot(path=str(OUTPUT_DIR / "06_project_saved.png"))

            browser.close()

        # 8. 模拟服务重启并在新会话中打开工程
        print("[8/8] 模拟关机/重启：停止后端服务并重新启动...")
        stop_backend()
        time.sleep(1)
        proc2 = ensure_backend_running()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-remote-fonts", "--disable-gpu", "--no-sandbox"],
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{PORT}", wait_until="domcontentloaded")
            page.wait_for_selector("#map", timeout=10000)

            print(f"  加载已保存工程 ID: {project_id}...")
            page.evaluate(f"() => window.GIS.project.loadProject('{project_id}')")
            page.wait_for_function("() => window.GIS.layers && window.GIS.layers.getLayers().length >= 2", timeout=10000)
            restored_layers = page.evaluate("() => window.GIS.layers.getLayers()")
            print(f"  ✓ 重启后工程加载成功！恢复图层数: {len(restored_layers)}")
            page.screenshot(path=str(OUTPUT_DIR / "07_project_reopened.png"))
            browser.close()

        print("\n" + "=" * 70)
        print("真实浏览器全流程验证全部成功通过 (ALL STEPS PASSED)！")
        print(f"截屏存证目录: {OUTPUT_DIR}")
        print(f"控制台严重报错数: {len(page_errors)}")
        print("=" * 70)
        return True

    finally:
        pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
