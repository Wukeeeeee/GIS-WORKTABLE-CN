# -*- coding: utf-8 -*-
"""GIS-WORKTABLE-CN 环境画像（profile）
=====================================
本仓库为 CN 版，默认 profile = "cn"：
- 底图/数据源默认走国内白名单（高德/天地图/DataV）
- 境外数据源（OSM 边界、Wikidata 等）默认禁用（合规+网络双原因）
- Overpass 等境外服务失败时给出离线/替代方案提示

可用取值：
- "cn"          CN 默认：境内优先，境外边界/实体工具禁用，路网等纯数据工具保留（失败有降级）
- "competition" 比赛/展示：在 cn 基础上进一步禁用所有境外在线数据工具（含路网下载），离线包优先
- "intl"        国际版行为（保留境外源与原默认值）

通过环境变量 GISWTB_PROFILE 覆盖（不影响国际版仓库，本文件仅存在于 CN 仓）。
"""

import os

_VALID = ("cn", "competition", "intl")

# 比赛模式下禁用的境外在线工具（注册表过滤）
_COMPETITION_DISABLED_TOOLS = {
    "download_road_network",
}
# CN 模式下禁用的工具（内容合规闸门：境外边界/实体数据不进 Agent 视野）
_CN_DISABLED_TOOLS = {
    "search_global_entities",        # Wikidata/Wikipedia（国家标签口径风险）
    "fetch_osm_boundary_or_features",  # OSM 行政边界/矢量（边界画法风险）
}


def get_profile() -> str:
    raw = os.environ.get("GISWTB_PROFILE", "cn").strip().lower()
    return raw if raw in _VALID else "cn"


def is_cn() -> bool:
    return get_profile() in ("cn", "competition")


def is_competition() -> bool:
    return get_profile() == "competition"


def disabled_tool_names() -> set:
    """返回当前 profile 下应从注册表剔除的工具名集合。"""
    if get_profile() == "intl":
        return set()
    return set(_CN_DISABLED_TOOLS) | (_COMPETITION_DISABLED_TOOLS if is_competition() else set())


def offline_dir() -> str:
    """离线数据包约定目录（DEM/路网/AOI/影像子集）。"""
    return os.environ.get(
        "GISWTB_OFFLINE_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache", "offline"),
    )
