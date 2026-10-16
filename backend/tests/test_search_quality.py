# -*- coding: utf-8 -*-
"""搜索链路质量测试：关键词拆解 / 相关性评分 / 垃圾页识别 / 引擎降级顺序 / 无境外引擎。

全部用例都不访问真实网络：引擎函数在测试内被替换为固定返回值。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services import tools


def test_query_tokens_basic():
    assert tools._query_tokens("广州地铁 线路图") == ["广州地铁", "线路图"]
    assert tools._query_tokens("2024年 GDP的") == ["2024", "GDP"]
    assert tools._query_tokens("") == []
    assert tools._query_tokens("a b") == []
    assert tools._query_tokens("广州地铁 广州地铁") == ["广州地铁"]


def test_relevance_score_hit_ratio():
    toks = tools._query_tokens("广州地铁 线路图")
    assert tools._relevance_score("广州地铁线路图", toks) == 1.0
    assert tools._relevance_score("广州地铁", toks) == 0.5
    assert tools._relevance_score("完全无关的内容", toks) == 0.0
    assert tools._relevance_score("任何内容", []) == 0.0


def test_looks_like_junk():
    assert tools._looks_like_junk("") is True
    assert tools._looks_like_junk("太短") is True
    assert tools._looks_like_junk("404 Not Found " + "x" * 200) is True
    assert tools._looks_like_junk("请开启 JavaScript 后继续 " + "x" * 200) is True
    assert tools._looks_like_junk("安全验证 " + "x" * 200) is True
    assert tools._looks_like_junk("正常的搜索结果摘要 " + "内容" * 100) is False


def _install_fake_engines(monkeypatch, baidu, sogou, bing, calls):
    monkeypatch.setattr(tools, "_engine_throttle", lambda name: None)
    monkeypatch.setattr(tools, "_search_call_count", 0)
    monkeypatch.setattr(tools, "_baidu_html_search", baidu)
    monkeypatch.setattr(tools, "_sogou_html_search", sogou)
    monkeypatch.setattr(tools, "_cn_bing_search", bing)
    return calls


def _good_result():
    return "广州地铁 线路图 " + "正常的搜索结果摘要内容 " * 20


def test_engine_fallback_order(monkeypatch):
    calls = []

    def baidu(query, timeout=12.0):
        calls.append("baidu")
        return ""

    def sogou(query, timeout=12.0):
        calls.append("sogou")
        return "404 Not Found " + "x" * 200

    def bing(query, timeout=12.0):
        calls.append("bing")
        return _good_result()

    _install_fake_engines(monkeypatch, baidu, sogou, bing, calls)
    out = tools.search_web.invoke({"query": "广州地铁 线路图"})
    assert calls == ["baidu", "sogou", "bing"], calls
    assert "Bing 中国" in out, out
    assert "相关性 100%" in out, out
    assert "404" not in out, out


def test_first_relevant_engine_short_circuits(monkeypatch):
    calls = []

    def baidu(query, timeout=12.0):
        calls.append("baidu")
        return _good_result()

    def sogou(query, timeout=12.0):
        calls.append("sogou")
        return _good_result()

    def bing(query, timeout=12.0):
        calls.append("bing")
        return _good_result()

    _install_fake_engines(monkeypatch, baidu, sogou, bing, calls)
    out = tools.search_web.invoke({"query": "广州地铁 线路图"})
    assert calls == ["baidu"], calls
    assert "百度" in out, out


def test_all_engines_fail_is_explicit(monkeypatch):
    calls = []

    def baidu(query, timeout=12.0):
        calls.append("baidu")
        return ""

    def sogou(query, timeout=12.0):
        calls.append("sogou")
        return "404 Not Found " + "x" * 200

    def bing(query, timeout=12.0):
        calls.append("bing")
        return "安全验证 " + "x" * 200

    _install_fake_engines(monkeypatch, baidu, sogou, bing, calls)
    out = tools.search_web.invoke({"query": "广州地铁 线路图"})
    assert calls == ["baidu", "sogou", "bing"], calls
    assert "搜索失败" in out and "所有引擎" in out, out


def test_search_chain_has_no_foreign_engine_domains():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src = io.open(os.path.join(root, "backend", "services", "tools.py"), encoding="utf-8").read().lower()
    forbidden = [
        "duck" + "duckgo",
        "html.duck" + "duckgo.com",
        "www." + "bing.com",
    ]
    for token in forbidden:
        assert token not in src, "搜索链路仍含境外引擎域名: " + token
    assert "cn.bing.com" in src
    for name in ("_baidu_html_search", "_sogou_html_search", "_cn_bing_search"):
        assert ("def " + name) in src, "缺少国内搜索引擎函数: " + name
