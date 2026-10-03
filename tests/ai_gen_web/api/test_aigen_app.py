import allure
import pytest
from jsonschema import validate

from utils.aigen import AiGenClient, error, ok
from utils.schemas import AIGEN_APP_VO_SCHEMA, aigen_page_schema

pytestmark = [pytest.mark.api, allure.epic("ai-gen-web 接口"), allure.feature("应用管理")]

GOOD_APP_PRIORITY = 99


def my_apps(client: AiGenClient, **query) -> dict:
    return ok(client.post("/app/my/list/page/vo", json={"pageNum": 1, "pageSize": 20, **query}))


@allure.story("创建应用")
@allure.title("创建应用：名称取 initPrompt 前 12 个字符，类型为 vue_project")
@allure.severity(allure.severity_level.BLOCKER)
def test_add_app(user: AiGenClient):
    prompt = "做一个咖啡店官网，展示品牌故事与招牌饮品"
    app_id = user.add_app(prompt)

    app = ok(user.get("/app/get/vo", params={"id": app_id}))
    validate(app, AIGEN_APP_VO_SCHEMA)
    assert app["appName"] == prompt[:12]
    assert app["initPrompt"] == prompt
    assert app["codeGenType"] == "vue_project"
    assert app["priority"] == 0
    assert app["deployKey"] is None
    assert app["user"]["userAccount"] == user.account


@allure.story("创建应用")
@allure.title("创建应用参数校验：{case}")
@pytest.mark.parametrize("case, prompt", [("initPrompt 为空", ""), ("initPrompt 全是空白", "   ")])
def test_add_app_blank_prompt(user: AiGenClient, case, prompt):
    error(user.post("/app/add", json={"initPrompt": prompt}), 40000, "初始化 prompt 不能为空")


@allure.story("创建应用")
@allure.title("未登录不能创建应用")
def test_add_app_requires_login(anon: AiGenClient):
    error(anon.post("/app/add", json={"initPrompt": "做个网站"}), 40100)


@allure.story("我的应用")
@allure.title("我的应用只返回自己的，支持按名称模糊搜索")
@allure.severity(allure.severity_level.CRITICAL)
def test_my_apps(user: AiGenClient, other_user: AiGenClient):
    blog = user.add_app("个人博客：记录读书笔记")
    shop = user.add_app("花店小程序落地页")
    other_user.add_app("个人博客：别人的")

    page = my_apps(user)
    validate(page, aigen_page_schema(AIGEN_APP_VO_SCHEMA))
    assert {r["id"] for r in page["records"]} == {blog, shop}

    page = my_apps(user, appName="博客")
    assert [r["id"] for r in page["records"]] == [blog]


@allure.story("我的应用")
@allure.title("每页最多 20 条：{endpoint}")
@pytest.mark.parametrize("endpoint", ["/app/my/list/page/vo", "/app/good/list/page/vo"])
def test_page_size_limit(user: AiGenClient, endpoint):
    error(user.post(endpoint, json={"pageNum": 1, "pageSize": 21}), 40000, "每页最多查询 20 个应用")


@allure.story("修改应用")
@allure.title("创建者可以修改应用名称")
def test_update_own_app(user: AiGenClient, app_id):
    ok(user.post("/app/update", json={"id": app_id, "appName": "新的名字"}))
    assert ok(user.get("/app/get/vo", params={"id": app_id}))["appName"] == "新的名字"


@allure.story("修改应用")
@allure.title("修改应用失败：{case}")
@pytest.mark.parametrize("case", ["修改别人的应用", "应用不存在"])
def test_update_app_failed(user: AiGenClient, other_user: AiGenClient, app_id, case):
    if case == "修改别人的应用":
        error(other_user.post("/app/update", json={"id": app_id, "appName": "改别人的"}), 40101)
        assert ok(user.get("/app/get/vo", params={"id": app_id}))["appName"] != "改别人的"
    else:
        error(user.post("/app/update", json={"id": 1, "appName": "x"}), 40400)


@allure.story("删除应用")
@allure.title("创建者删除应用后不可再查询")
@allure.severity(allure.severity_level.CRITICAL)
def test_delete_own_app(user: AiGenClient, app_id):
    assert ok(user.post("/app/delete", json={"id": app_id})) is True
    error(user.get("/app/get/vo", params={"id": app_id}), 40400)
    assert my_apps(user)["records"] == []


@allure.story("删除应用")
@allure.title("不能删除别人的应用，管理员可以")
def test_delete_app_permissions(user: AiGenClient, other_user: AiGenClient, admin: AiGenClient, app_id):
    error(other_user.post("/app/delete", json={"id": app_id}), 40101)
    ok(user.get("/app/get/vo", params={"id": app_id}))

    assert ok(admin.post("/app/delete", json={"id": app_id})) is True
    error(user.get("/app/get/vo", params={"id": app_id}), 40400)


@allure.story("精选应用")
@allure.title("管理员设为精选后，未登录用户可在精选列表看到")
@allure.severity(allure.severity_level.CRITICAL)
def test_good_apps(admin: AiGenClient, anon: AiGenClient, app_id):
    def good_ids() -> set[str]:
        page = ok(anon.post("/app/good/list/page/vo", json={"pageNum": 1, "pageSize": 20}))
        return {r["id"] for r in page["records"]}

    assert app_id not in good_ids()
    ok(admin.post("/app/admin/update", json={"id": app_id, "priority": GOOD_APP_PRIORITY, "appName": "精选作品"}))

    assert app_id in good_ids()
    app = ok(admin.get("/app/admin/get/vo", params={"id": app_id}))
    assert app["priority"] == GOOD_APP_PRIORITY
    assert app["appName"] == "精选作品"


@allure.story("管理员")
@allure.title("管理员按用户分页查询应用")
def test_admin_list_apps(admin: AiGenClient, user: AiGenClient, app_id):
    user_id = ok(user.get("/user/get/login"))["id"]
    page = ok(admin.post("/app/admin/list/page/vo", json={"pageNum": 1, "pageSize": 50, "userId": user_id}))
    validate(page, aigen_page_schema(AIGEN_APP_VO_SCHEMA))
    assert [r["id"] for r in page["records"]] == [app_id]
