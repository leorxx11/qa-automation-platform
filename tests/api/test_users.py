import allure
import pytest
from jsonschema import validate

from utils.schemas import USER_SCHEMA

pytestmark = [pytest.mark.api, allure.epic("接口自动化"), allure.feature("用户 Users")]


@allure.story("查询")
@allure.title("查询用户列表，每个用户字段符合契约且 ID 唯一")
@allure.severity(allure.severity_level.CRITICAL)
def test_list_users(api):
    resp = api.get("/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 10
    for user in users:
        validate(user, USER_SCHEMA)
    assert len({u["id"] for u in users}) == len(users)


@allure.story("关联查询")
@allure.title("用户的文章都属于该用户")
def test_user_posts_belong_to_user(api):
    user = api.get("/users/3").json()
    posts = api.get(f"/users/{user['id']}/posts").json()
    assert posts
    assert all(p["userId"] == user["id"] for p in posts)


@allure.story("关联查询")
@allure.title("用户待办中已完成数量不超过总数")
def test_user_todos_completed_count(api):
    todos = api.get("/users/1/todos").json()
    completed = [t for t in todos if t["completed"]]
    with allure.step(f"共 {len(todos)} 条待办，已完成 {len(completed)} 条"):
        assert 0 < len(completed) <= len(todos)
