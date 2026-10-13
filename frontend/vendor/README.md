# frontend/vendor — 本地静态库（CN 版）

全部库文件本地化，来源为 npmmirror（registry.npmmirror.com）官方包，离线/比赛网络零外链。
重新下载/升级：`python gis_workbuddy_outputs/giswtb_cn_audit/scripts/download_vendor.py`

| 目录 | 包@版本 | 供谁用 |
|---|---|---|
| leaflet/ | leaflet@1.9.4（js+css+images） | index.html、geosource_map.html |
| marked/ | marked@15.0.6 | index.html（Markdown 渲染） |
| leaflet-heat/ | leaflet.heat@0.2.0 | index.html（热力图） |
| leaflet-draw/ | leaflet-draw@1.0.4（js+css+images） | index.html（绘制） |
| leaflet-vectorgrid/ | @s3pweb/leaflet.vectorgrid@1.3.0 | index.html（矢量瓦片） |
| echarts/ | echarts@5.5.1 | create_chart 生成 HTML（本地 file:// + CDN 回退） |
| three/ | three@0.128.0（three.min.js+OrbitControls.js） | view_3d_terrain 生成 HTML（同上） |
| cesium/ | cesium@1.119.0（Build/Cesium 完整 376 文件） | renderer_cesium.js 回退链首位 |
