# 路网获取（CN 版）

路网数据获取优先级：**离线/上传数据 > OSM 在线下载**。

## 方式一：离线/上传数据（演示与离线环境首选）
1. 项目预置离线路网包：`cache/offline/roadnet/`（GraphML / GeoJSON）
2. 用户上传路网文件（GeoJSON / Shapefile / GraphML），AI 自动识别为路网图层
3. 有路网图层后直接用 `network_analysis` 工具分析（见下文）

## 方式二：OSMnx 在线下载（网络受限时可能超时）
```python
import osmnx as ox
G = ox.graph_from_place('北京市海淀区', network_type='drive')
edges = ox.graph_to_gdfs(G, nodes=False)
print(edges.to_json())        # 自动推送到地图
```

## network_type 参数
`drive`(机动车) / `walk`(步行) / `bike`(自行车) / `drive_service` / `all`

## network_analysis 工具（基于已有路网图层做分析）
有路网图层后，用 `network_analysis` 工具做分析：
- **route**（最短路径）：传 origin + destination
- **service_area**（服务区）：传 facility + breaks（逗号分隔米数）
- **closest_facility**（最近设施）：传 origin + events（分号分隔坐标）

坐标参数统一格式：`"经度,纬度"`

## 注意
- Overpass 镜像地址已在 execute_python 环境初始化中自动设置（2026-10 校验：mail.ru 镜像已失效剔除）；也可用 `GIS_OVERPASS_ENDPOINT` 指向本地离线服务
- 查询范围不要太大（建议一个区/县城级别），否则超时（当前超时限制 120s）
- 在线下载失败/超时时会自动返回替代方案提示；**如实告知用户失败，禁止编造路网数据**
- 返回的边自带 `name`（道路名）、`highway`（道路类型）、`length`（长度，米）等字段
- 数据坐标系为 WGS-84 (EPSG:4326)，可直接上地图
