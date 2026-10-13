"""地名 → 空间范围（EPSG:4326 bbox）。

使用 OpenStreetMap Nominatim 官方公开 API（稳定、非爬虫）。
按 Nominatim 使用规范携带可识别 User-Agent 并低频调用。

结果不命中、解析失败时抛明确错误，不静默返回空范围。
"""

from __future__ import annotations

from typing import Optional

from backend.services.data_providers.http import get_json, DEFAULT_TIMEOUT
from backend.services.data_providers.errors import DataNotFoundError, DataProviderError

# 仅官方 Nominatim 实例。可被测试覆盖替换。
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_ENDPOINTS = [NOMINATIM_ENDPOINT]

# CN 降级：阿里 DataV 行政边界服务（免 Key、可直连），用于解析中国地名 → bbox
DATAV_GEOJSON_URL = "https://geo.datav.aliyun.com/areas_v3/bound/geojson"


def _bbox_from_geojson_geometry(geom: dict) -> Optional[tuple]:
    """递归提取 GeoJSON geometry 的 (min_lng, min_lat, max_lng, max_lat)。"""
    coords = []

    def _collect(o):
        if isinstance(o, (list, tuple)):
            if o and isinstance(o[0], (int, float)):
                coords.append((float(o[0]), float(o[1])))
            else:
                for x in o:
                    _collect(x)

    _collect(geom)
    if not coords:
        return None
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lngs), min(lats), max(lngs), max(lats))


def _resolve_bbox_via_datav(area: str) -> Optional[tuple]:
    """CN 降级：用 DataV 行政边界解析中国地名 → bbox。失败返回 None（由调用方继续走 Nominatim）。"""
    try:
        data = get_json(DATAV_GEOJSON_URL, params={"name": str(area).strip()}, timeout=DEFAULT_TIMEOUT)
        features = data.get("features") if isinstance(data, dict) else None
        if not features:
            return None
        boxes = []
        for f in features:
            g = f.get("geometry") or {}
            bb = _bbox_from_geojson_geometry(g)
            if bb:
                boxes.append(bb)
        if not boxes:
            return None
        # DataV 返回 GCJ-02 坐标 → 转 WGS-84（与 datav_service 出口策略一致）
        try:
            from backend.services.geo_coords import gcj02_to_wgs84
            corners = []
            for lng, lat in [
                (min(b[0] for b in boxes), min(b[1] for b in boxes)),
                (max(b[2] for b in boxes), min(b[1] for b in boxes)),
                (min(b[0] for b in boxes), max(b[3] for b in boxes)),
                (max(b[2] for b in boxes), max(b[3] for b in boxes)),
            ]:
                w = gcj02_to_wgs84(lng, lat)
                corners.append((w[0], w[1]))
            return (
                min(c[0] for c in corners), min(c[1] for c in corners),
                max(c[0] for c in corners), max(c[1] for c in corners),
            )
        except Exception:
            # 转换模块不可用时退回原始 bbox（标注口径差异）
            return (
                min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes),
            )
    except Exception:
        return None


def resolve_area_bbox(area: str) -> tuple:
    """把地名解析为 (min_lng, min_lat, max_lng, max_lat)（EPSG:4326）。

    失败抛 DataNotFoundError / DataProviderError。
    """
    if not area or not str(area).strip():
        raise DataProviderError("缺少空间范围：请提供城市/区域名，或直接给出经纬度范围 bbox。")

    # CN 降级优先：DataV 行政边界（免 Key、可直连、WGS-84 转 GIS 已纠偏数据）
    try:
        from backend.services.cn_profile import is_cn
        if is_cn():
            bb = _resolve_bbox_via_datav(str(area).strip())
            if bb:
                return bb
    except Exception:
        pass

    params = {
        "q": str(area).strip(),
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "polygon_geojson": 0,
    }
    headers = {"Accept": "application/json"}

    # 依次尝试镜像（低频，单次即可）
    for url in _NOMINATIM_ENDPOINTS:
        try:
            results = get_json(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            raise DataProviderError(
                f"地名解析服务暂时不可用：{area}",
                provider="geocode",
                hint=str(e),
            ) from e
        if not isinstance(results, list) or not results:
            continue
        hit = results[0]
        bb = hit.get("boundingbox") or []
        if len(bb) >= 4:
            try:
                south, north, west, east = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
                return (min(west, east), min(south, north), max(west, east), max(south, north))
            except (ValueError, TypeError):
                pass
        # 退而求其次：用中心点做一个小范围
        lat, lon = hit.get("lat"), hit.get("lon")
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                d = 0.05  # 约 5km 缓冲
                return (lon - d, lat - d, lon + d, lat + d)
            except (ValueError, TypeError):
                pass

    raise DataNotFoundError(
        f"无法定位区域「{area}」，请确认地名拼写，或直接提供经纬度 bbox。",
        provider="geocode",
        hint="示例：bbox='112.9,28.1,113.1,28.3'（minLng,minLat,maxLng,maxLat）。",
    )


def bbox_to_text(bbox: tuple) -> str:
    """把 bbox 转成可读文本（用于显示与 Overpass 参数）。"""
    min_lng, min_lat, max_lng, max_lat = (round(float(v), 5) for v in bbox)
    return f"{min_lng},{min_lat},{max_lng},{max_lat}"


def bbox_to_overpass(bbox: tuple) -> str:
    """Overpass 需要的 (south,west,north,east) 顺序。"""
    min_lng, min_lat, max_lng, max_lat = bbox
    return f"{min_lat},{min_lng},{max_lat},{max_lng}"
