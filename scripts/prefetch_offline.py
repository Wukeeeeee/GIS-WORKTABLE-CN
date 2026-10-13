# -*- coding: utf-8 -*-
"""CN 版离线数据预热脚本（赛前/展示前跑一次，断网即全功能）
====================================================
预热内容：
1. DataV 34 省级行政边界 → cache/aoi/（datav_adcode_{adcode}.json + datav_{名称}.json 双键）
2. 可选 --with-cities：全部地级市边界（~333 请求，0.3s 礼貌间隔）
用法：python prefetch_offline.py [--with-cities]
"""
import json
import os
import sys
import time
import urllib.request

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
AOI = os.path.join(REPO, "cache", "aoi")
BASE = "https://geo.datav.aliyun.com/areas_v3/bound"

PROVINCES = {
    "北京市": "110000", "天津市": "120000", "河北省": "130000", "山西省": "140000",
    "内蒙古自治区": "150000", "辽宁省": "210000", "吉林省": "220000", "黑龙江省": "230000",
    "上海市": "310000", "江苏省": "320000", "浙江省": "330000", "安徽省": "340000",
    "福建省": "350000", "江西省": "360000", "山东省": "370000", "河南省": "410000",
    "湖北省": "420000", "湖南省": "430000", "广东省": "440000", "广西壮族自治区": "450000",
    "海南省": "460000", "重庆市": "500000", "四川省": "510000", "贵州省": "520000",
    "云南省": "530000", "西藏自治区": "540000", "陕西省": "610000", "甘肃省": "620000",
    "青海省": "630000", "宁夏回族自治区": "640000", "新疆维吾尔自治区": "650000",
    "台湾省": "710000", "香港特别行政区": "810000", "澳门特别行政区": "820000",
}


def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "GISWTB-CN-prefetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def save(name_key, adcode, data):
    os.makedirs(AOI, exist_ok=True)
    p1 = os.path.join(AOI, f"datav_adcode_{adcode}.json")
    p2 = os.path.join(AOI, f"datav_{name_key}.json")
    for p in (p1, p2):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    return p1, p2


def prefetch(cities=False):
    ok = fail = 0
    city_list = []
    for name, adcode in PROVINCES.items():
        try:
            data = fetch_json(f"{BASE}/{adcode}_full.json")
            save(name, adcode, data)
            for feat in data.get("features", []):
                p = feat.get("properties", {})
                if p.get("level") == "city" or (p.get("name") or "").endswith("市"):
                    city_list.append((p.get("name"), p.get("adcode")))
            ok += 1
            print(f"[省] {name} ✓", flush=True)
        except Exception as e:
            fail += 1
            print(f"[省] {name} ✗ {type(e).__name__}", flush=True)
        time.sleep(0.2)
    print(f"省级完成：{ok} 成功 / {fail} 失败")

    if cities:
        cok = cfail = 0
        for name, adcode in city_list:
            if not name or not adcode:
                continue
            try:
                data = fetch_json(f"{BASE}/{adcode}_full.json")
                save(name, adcode, data)
                cok += 1
            except Exception:
                cfail += 1
            time.sleep(0.3)
        print(f"市级完成：{cok} 成功 / {cfail} 失败")
    print(f"缓存目录：{AOI}")


if __name__ == "__main__":
    prefetch(cities="--with-cities" in sys.argv)
