"""CN 数据访问策略。白名单是产品配置，不代表服务的数据授权或部署合规认证。"""
from urllib.parse import urljoin, urlsplit

from backend.services.cn_profile import is_cn


class NetworkPolicyError(ValueError):
    pass


# 只允许工作台使用的国内服务及政府/教育来源；不以任意 .cn 域名作为信任依据。
CN_DATA_HOSTS = (
    "amap.com", "autonavi.com", "tianditu.gov.cn", "tianditu.com",
    "geo.datav.aliyun.com", "baidu.com", "sogou.com", "cn.bing.com",
    "bilibili.com", "gov.cn", "edu.cn", "stats.gov.cn",
)

CN_MODEL_HOSTS = {
    "api.deepseek.com", "open.bigmodel.cn", "dashscope.aliyuncs.com",
    "ark.cn-beijing.volces.com", "api.moonshot.cn", "api.siliconflow.cn",
    "api.minimax.chat", "api.minimaxi.com",
}


def check_model_url(url: str) -> None:
    if not is_cn():
        return
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        local = host in ("localhost", "127.0.0.1", "::1") and parts.scheme in ("http", "https")
        valid = local or (host in CN_MODEL_HOSTS and parts.scheme == "https" and parts.port in (None, 443))
        valid = valid and not parts.username and not parts.password and not parts.query and not parts.fragment
    except ValueError:
        valid = False
    if not valid:
        raise NetworkPolicyError("CN 演示版仅允许已配置的国内模型接口或本机模型。请选 DeepSeek、智谱或配置已批准的国内服务。")


def check_data_url(url: str) -> None:
    if not is_cn():
        return
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        allowed = any(host == root or host.endswith("." + root) for root in CN_DATA_HOSTS)
        valid = parts.scheme == "https" and parts.port in (None, 443)
        valid = valid and not parts.username and not parts.password and allowed
    except ValueError:
        valid = False
    if not valid:
        raise NetworkPolicyError("CN 模式已阻止非白名单数据源。请使用国内已批准服务或上传本地数据，禁止改用其他工具绕过。")


def data_request(method: str, url: str, **kwargs):
    """在发请求前检查，并逐跳检查重定向，避免跳转绕过白名单。"""
    import requests
    if not is_cn():
        return requests.request(method, url, **kwargs)
    kwargs.pop("allow_redirects", None)
    for _ in range(6):
        check_data_url(url)
        response = requests.request(method, url, allow_redirects=False, **kwargs)
        if response.status_code not in (301, 302, 303, 307, 308):
            return response
        location = response.headers.get("Location")
        response.close()
        if not location:
            raise NetworkPolicyError("数据源返回了无效的重定向。")
        url = urljoin(url, location)
        # 不把原 URL 的坐标、查询参数和认证信息带到重定向目标。
        for key in ("params", "auth", "cookies", "headers"):
            kwargs.pop(key, None)
        if response.status_code == 303 or (response.status_code in (301, 302) and method.upper() == "POST"):
            method = "GET"
            kwargs.pop("data", None)
            kwargs.pop("json", None)
    raise NetworkPolicyError("数据源重定向次数过多。")
