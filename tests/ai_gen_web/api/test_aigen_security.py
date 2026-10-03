import http.client
from urllib.parse import urlsplit

import allure
import pytest

from utils.aigen import API_BASE_URL, AiGenClient, ok

pytestmark = [pytest.mark.api, allure.epic("ai-gen-web 接口"), allure.feature("安全")]


@allure.story("排序参数")
@allure.title("合法的 sortField 按指定字段排序")
@pytest.mark.parametrize("order", ["ascend", "descend"])
def test_sort_field_valid(user: AiGenClient, order):
    apps = [user.add_app("bbb 应用"), user.add_app("aaa 应用"), user.add_app("ccc 应用")]
    page = ok(user.post("/app/my/list/page/vo", json={
        "pageNum": 1, "pageSize": 20, "sortField": "appName", "sortOrder": order,
    }))
    expected = [apps[1], apps[0], apps[2]]
    assert [r["id"] for r in page["records"]] == (expected if order == "ascend" else expected[::-1])


@allure.story("排序参数")
@allure.title("sortField 不应原样拼进 SQL：{endpoint}")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：sortField 未做白名单校验，直接拼进 ORDER BY；"
    "传入非法字符时数据库报语法错误（返回 50000），说明存在 SQL 注入风险",
)
@pytest.mark.parametrize("endpoint", ["/app/good/list/page/vo", "/app/my/list/page/vo"])
def test_sort_field_not_concatenated(user: AiGenClient, endpoint):
    user.add_app("用于排序校验的应用")
    body = user.post(endpoint, json={"pageNum": 1, "pageSize": 10, "sortField": "appName`"}).json()
    # 期望：非法字段被拒绝（40000）或被忽略（0），而不是触发数据库错误
    assert body["code"] in (0, 40000), body


@allure.story("跨域")
@allure.title("不信任的 Origin 不应被允许携带 Cookie 跨域访问")
@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：allowedOriginPatterns(\"*\") + allowCredentials(true)，任意 Origin 都会被原样放行；"
    "Cookie 的 SameSite=Lax 降低了实际风险，但配置本身过宽",
)
def test_cors_untrusted_origin(anon: AiGenClient):
    origin = "https://untrusted.example"
    resp = anon.request("OPTIONS", "/user/get/login", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
    })
    assert resp.headers.get("Access-Control-Allow-Origin") != origin


@allure.story("敏感信息")
@allure.title("管理员查询用户详情不应返回密码哈希")
@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：/user/get 直接返回 User 实体，包含 userPassword（MD5 + 固定盐）",
)
def test_admin_get_user_hides_password(admin: AiGenClient, user: AiGenClient):
    user_id = ok(user.get("/user/get/login"))["id"]
    data = ok(admin.get("/user/get", params={"id": user_id}))
    assert "userPassword" not in data


@allure.story("静态资源")
@allure.title("静态资源路径不能跳出生成目录：{path}")
@pytest.mark.parametrize("path", [
    "/static/x/..%2f..%2f..%2fpom.xml",
    "/static/x/%2e%2e/%2e%2e/%2e%2e/pom.xml",
])
def test_static_path_confined(path):
    # requests/urllib3 会解码 %2e 并折叠 ../，这里用 http.client 原样发送路径
    base = urlsplit(API_BASE_URL)
    conn = http.client.HTTPConnection(base.hostname, base.port, timeout=10)
    conn.request("GET", f"{base.path}{path}")
    resp = conn.getresponse()
    body = resp.read().decode(errors="replace")
    conn.close()
    allure.attach(f"{resp.status} {resp.reason}\n\n{body[:2000]}", name="响应", attachment_type=allure.attachment_type.TEXT)
    assert resp.status in (400, 404)
    assert "<project" not in body
