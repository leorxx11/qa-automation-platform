import allure
import pytest
from jsonschema import validate

from utils.schemas import POST_SCHEMA

pytestmark = [pytest.mark.api, allure.epic("接口自动化"), allure.feature("文章 Posts")]


@allure.story("查询")
@allure.title("查询文章列表，共 100 条且字段符合契约")
@allure.severity(allure.severity_level.CRITICAL)
def test_list_posts(api):
    resp = api.get("/posts")
    assert resp.status_code == 200
    posts = resp.json()
    assert len(posts) == 100
    for post in posts:
        validate(post, POST_SCHEMA)


@allure.story("查询")
@allure.title("按 ID 查询文章：id={post_id}")
@pytest.mark.parametrize("post_id", [1, 50, 100])
def test_get_post_by_id(api, post_id):
    resp = api.get(f"/posts/{post_id}")
    assert resp.status_code == 200
    post = resp.json()
    validate(post, POST_SCHEMA)
    assert post["id"] == post_id


@allure.story("查询")
@allure.title("查询不存在的文章返回 404")
def test_get_missing_post(api):
    resp = api.get("/posts/99999")
    assert resp.status_code == 404
    assert resp.json() == {}


@allure.story("查询")
@allure.title("按 userId 过滤文章：userId={user_id}")
@pytest.mark.parametrize("user_id", [1, 5, 10])
def test_filter_posts_by_user(api, user_id):
    resp = api.get("/posts", params={"userId": user_id})
    assert resp.status_code == 200
    posts = resp.json()
    assert posts, "过滤结果不应为空"
    assert {p["userId"] for p in posts} == {user_id}


@allure.story("新增")
@allure.title("创建文章返回 201 并回显请求数据")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_post(api):
    payload = {"title": "CI 自动化测试", "body": "由 self-hosted runner 执行", "userId": 1}
    resp = api.post("/posts", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    validate(created, POST_SCHEMA)
    for key, value in payload.items():
        assert created[key] == value


@allure.story("修改")
@allure.title("PUT 全量更新文章")
def test_update_post(api):
    payload = {"id": 1, "title": "已更新", "body": "全量替换", "userId": 1}
    resp = api.put("/posts/1", json=payload)
    assert resp.status_code == 200
    assert resp.json() == payload


@allure.story("修改")
@allure.title("PATCH 只更新标题，其余字段保持不变")
def test_patch_post_title(api):
    original = api.get("/posts/1").json()
    resp = api.patch("/posts/1", json={"title": "只改标题"})
    assert resp.status_code == 200
    patched = resp.json()
    assert patched["title"] == "只改标题"
    assert patched["body"] == original["body"]


@allure.story("删除")
@allure.title("删除文章返回 200")
def test_delete_post(api):
    resp = api.delete("/posts/1")
    assert resp.status_code == 200
