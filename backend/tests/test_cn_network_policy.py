"""区域数据策略必须在网络请求发生前生效。"""
from unittest.mock import Mock

import pytest

from backend.services.network_policy import check_data_url, data_request, NetworkPolicyError


@pytest.mark.parametrize("url", [
    "https://nominatim.openstreetmap.org/reverse?lat=30&lon=106",
    "https://overpass-api.de/api/interpreter",
    "https://api.open-meteo.com/v1/elevation",
    "https://restapi.amap.com.evil.example/path",
    "https://restapi.amap.com@evil.example/path",
    "http://restapi.amap.com/path", "https://127.0.0.1/path",
    "file:///etc/passwd", "https://restapi.amap.com:8443/path",
])
def test_cn_rejects_before_request(monkeypatch, url):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    request = Mock()
    monkeypatch.setattr("requests.request", request)
    with pytest.raises(NetworkPolicyError):
        data_request("GET", url)
    request.assert_not_called()


def test_redirect_cannot_escape_whitelist(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "competition")
    redirect = Mock(status_code=302, headers={"Location": "https://overpass-api.de/api/interpreter"})
    request = Mock(return_value=redirect)
    monkeypatch.setattr("requests.request", request)
    with pytest.raises(NetworkPolicyError):
        data_request("GET", "https://restapi.amap.com/start")
    assert request.call_count == 1
    assert request.call_args.kwargs["allow_redirects"] is False
    redirect.close.assert_called_once()


def test_domestic_request_and_relative_redirect(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    final = Mock(status_code=200)
    request = Mock(side_effect=[Mock(status_code=302, headers={"Location": "/result"}), final])
    monkeypatch.setattr("requests.request", request)
    assert data_request("GET", "https://restapi.amap.com/start", params={"key": "secret"}) is final
    assert request.call_args.args[1] == "https://restapi.amap.com/result"
    assert "params" not in request.call_args.kwargs


def test_intl_keeps_existing_network_behavior(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "intl")
    request = Mock()
    monkeypatch.setattr("requests.request", request)
    data_request("GET", "https://overpass-api.de/api/interpreter")
    assert "allow_redirects" not in request.call_args.kwargs


def test_invalid_profile_fails_closed(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "typo")
    with pytest.raises(NetworkPolicyError):
        check_data_url("https://overpass-api.de/api/interpreter")


def test_python_and_web_tools_enforce_policy(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    from backend.services import tools
    request = Mock()
    monkeypatch.setattr("requests.request", request)
    assert "错误" in tools.fetch_webpage_impl("https://overpass-api.de/api/interpreter")
    assert "错误" in tools.scrape_page.invoke({"url": "https://nominatim.openstreetmap.org/reverse"})
    assert tools._ast_sandbox_check("import osmnx as ox")
    assert tools._ast_sandbox_check("import pandas as pd\npd.read_csv('https://example.com/data.csv')")
    assert tools._ast_sandbox_check("import numpy as np\nprint(np.mean([1, 2]))") is None
    request.assert_not_called()


def test_cloud_and_provider_requests_are_blocked(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    from backend.services import cloud_native, url_gis_service
    from backend.services.data_providers import http
    request = Mock()
    monkeypatch.setattr("requests.request", request)
    url = "https://example.com/data.tif"
    with pytest.raises(NetworkPolicyError):
        http.request_with_retry("GET", url)
    with pytest.raises(cloud_native.CloudNativeError):
        cloud_native._as_vsi_path(url)
    with pytest.raises(NetworkPolicyError):
        cloud_native._HttpRangeSource(url).get_bytes(0, 64)
    with pytest.raises(url_gis_service.UrlGisError):
        url_gis_service._http_get(url)
    request.assert_not_called()


def test_satellite_never_falls_back_to_foreign_source(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    from backend.services import tools
    tools._tile_cache.clear()
    request = Mock(side_effect=RuntimeError("domestic source unavailable"))
    monkeypatch.setattr("requests.request", request)
    with pytest.raises(RuntimeError):
        tools._fetch_satellite_imagery(106.08, 30.94, 106.081, 30.941, zoom=10)
    assert request.call_count == 1
    assert "autonavi.com" in request.call_args.args[1]
    with pytest.raises(NetworkPolicyError):
        tools._fetch_satellite_imagery(106.08, 30.94, 106.081, 30.941, source="esri")


def test_reverse_geocode_does_not_fall_back_to_osm(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    from backend import main
    from backend.services import tools
    monkeypatch.setattr(tools, "_current_amap_key", "")
    request = Mock()
    monkeypatch.setattr("requests.get", request)
    monkeypatch.setattr("requests.request", request)
    result = main._reverse_geocode_sync(106.08, 30.94)
    assert result["lng"] == 106.08
    assert result["province"] == ""
    request.assert_not_called()


def test_python_runtime_blocks_constructed_network_url(monkeypatch):
    monkeypatch.setenv("GISWTB_PROFILE", "cn")
    from backend.services import tools
    code = "import pandas as pd\nu = ''.join(['https', '://', 'example.com/data.csv'])\nprint(pd.read_csv(u))"
    assert tools._ast_sandbox_check(code) is None
    result = tools.execute_python.invoke({"code": code})
    assert "CN 模式 Python 禁止联网" in result
