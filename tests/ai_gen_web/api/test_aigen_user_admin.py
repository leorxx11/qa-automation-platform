import allure
import pytest
from jsonschema import validate

from utils.aigen import AiGenClient, error, ok, unique_account
from utils.schemas import AIGEN_USER_VO_SCHEMA, aigen_page_schema

pytestmark = [pytest.mark.api, allure.epic("ai-gen-web 接口"), allure.feature("权限与用户管理")]

ADMIN_ENDPOINTS = [
    ("POST", "/user/add", {"userAccount": "qa_noauth"}),
    ("GET", "/user/get?id=1", None),
    ("POST", "/user/delete", {"id": 1}),
    ("POST", "/user/update", {"id": 1, "userName": "x"}),
    ("POST", "/user/list/page/vo", {"pageNum": 1, "pageSize": 10}),
    ("POST", "/app/admin/delete", {"id": 1}),
    ("POST", "/app/admin/update", {"id": 1, "priority": 99}),
    ("POST", "/app/admin/list/page/vo", {"pageNum": 1, "pageSize": 10}),
    ("GET", "/app/admin/get/vo?id=1", None),
    ("POST", "/chatHistory/admin/list/page/vo", {"pageNum": 1, "pageSize": 10}),
]
ENDPOINT_IDS = [f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ENDPOINTS]


@allure.story("接口鉴权")
@allure.title("普通用户调用管理员接口返回 40101：{method} {path}")
@pytest.mark.parametrize("method, path, body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_user_forbidden_on_admin_endpoints(user: AiGenClient, method, path, body):
    error(user.request(method, path, json=body), 40101, "无权限")


@allure.story("接口鉴权")
@allure.title("未登录调用管理员接口返回 40100：{method} {path}")
@pytest.mark.parametrize("method, path, body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_anonymous_on_admin_endpoints(anon: AiGenClient, method, path, body):
    error(anon.request(method, path, json=body), 40100, "未登录")


@allure.story("用户管理")
@allure.title("管理员创建的用户可用默认密码 12345678 登录")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_add_user(admin: AiGenClient):
    account = unique_account("added")
    user_id = ok(admin.post("/user/add", json={"userAccount": account, "userName": "新同事"}))

    client = AiGenClient()
    data = ok(client.login(account, "12345678"))
    assert data["id"] == user_id
    assert data["userName"] == "新同事"


@allure.story("用户管理")
@allure.title("管理员按账号分页查询，结果不包含密码")
def test_admin_list_users(admin: AiGenClient, user: AiGenClient):
    page = ok(admin.post("/user/list/page/vo", json={"pageNum": 1, "pageSize": 10, "userAccount": user.account}))
    validate(page, aigen_page_schema(AIGEN_USER_VO_SCHEMA))
    assert [r["userAccount"] for r in page["records"]] == [user.account]


@allure.story("用户管理")
@allure.title("管理员修改用户信息后立即生效")
def test_admin_update_user(admin: AiGenClient, user: AiGenClient):
    user_id = ok(user.get("/user/get/login"))["id"]
    ok(admin.post("/user/update", json={"id": user_id, "userName": "改过的昵称", "userProfile": "测试简介"}))

    data = ok(user.get("/user/get/login"))
    assert data["userName"] == "改过的昵称"
    assert data["userProfile"] == "测试简介"


@allure.story("用户管理")
@allure.title("管理员删除用户后，该用户已有会话失效且无法再登录")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_delete_user(admin: AiGenClient, user: AiGenClient):
    user_id = ok(user.get("/user/get/login"))["id"]
    assert ok(admin.post("/user/delete", json={"id": user_id})) is True

    error(user.get("/user/get/login"), 40100)
    error(AiGenClient().login(user.account), 40000, "用户不存在或密码错误")


@allure.story("用户管理")
@allure.title("查询不存在的用户返回 40400")
def test_admin_get_missing_user(admin: AiGenClient):
    error(admin.get("/user/get", params={"id": 1}), 40400)
