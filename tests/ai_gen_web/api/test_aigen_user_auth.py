import allure
import pytest
from jsonschema import validate

from utils.aigen import AiGenClient, error, ok, unique_account
from utils.schemas import AIGEN_LOGIN_USER_SCHEMA

pytestmark = [pytest.mark.api, allure.epic("ai-gen-web 接口"), allure.feature("注册与登录")]


@allure.story("注册")
@allure.title("注册成功后可以用该账号登录")
@allure.severity(allure.severity_level.BLOCKER)
def test_register_and_login(anon: AiGenClient):
    account = unique_account()
    user_id = ok(anon.register(account))

    data = ok(anon.login(account))
    validate(data, AIGEN_LOGIN_USER_SCHEMA)
    assert data["id"] == user_id
    assert data["userAccount"] == account
    assert data["userName"] == account
    assert data["userRole"] == "user"


@allure.story("注册")
@allure.title("注册参数校验：{case}")
@pytest.mark.parametrize(
    "case, account, password, check, message",
    [
        ("账号为空", "", "Passw0rd123", "Passw0rd123", "参数为空"),
        ("密码为空", "qa_blank_pwd", "", "", "参数为空"),
        ("账号 3 位", "abc", "Passw0rd123", "Passw0rd123", "账号长度必须大于4个字符"),
        ("密码 7 位", "qa_short_pwd", "1234567", "1234567", "密码长度必须在8-16个字符之间"),
        ("密码 17 位", "qa_long_pwd", "1" * 17, "1" * 17, "密码长度必须在8-16个字符之间"),
        ("两次密码不一致", "qa_mismatch", "Passw0rd123", "Passw0rd124", "两次输入的密码不一致"),
    ],
)
def test_register_validation(anon: AiGenClient, case, account, password, check, message):
    error(anon.register(account, password, check), 40000, message)


@allure.story("注册")
@allure.title("注册边界值可通过：{case}")
@pytest.mark.parametrize(
    "case, account, password",
    [
        ("账号 4 位", lambda: unique_account()[-4:], "Passw0rd123"),
        ("密码 8 位", unique_account, "12345678"),
        ("密码 16 位", unique_account, "1234567890abcdef"),
    ],
)
def test_register_boundaries(anon: AiGenClient, case, account, password):
    acc = account()
    ok(anon.register(acc, password))
    ok(anon.login(acc, password))


@allure.story("注册")
@allure.title("重复账号不能注册")
def test_register_duplicate(anon: AiGenClient):
    account = unique_account()
    ok(anon.register(account))
    error(anon.register(account), 40000, "账号已存在")


@allure.story("登录")
@allure.title("登录失败：{case}")
@pytest.mark.parametrize("case", ["密码错误", "账号不存在"])
def test_login_failed(anon: AiGenClient, case):
    account = unique_account()
    if case == "密码错误":
        ok(anon.register(account))
        resp = anon.login(account, "WrongPass999")
    else:
        resp = anon.login(account)
    error(resp, 40000, "用户不存在或密码错误")
    error(anon.get("/user/get/login"), 40100)


@allure.story("登录态")
@allure.title("未登录获取当前用户返回 40100")
def test_get_login_user_requires_login(anon: AiGenClient):
    error(anon.get("/user/get/login"), 40100, "未登录")


@allure.story("登录态")
@allure.title("登录后可获取当前用户，Cookie 为 HttpOnly")
def test_get_login_user(user: AiGenClient):
    data = ok(user.get("/user/get/login"))
    validate(data, AIGEN_LOGIN_USER_SCHEMA)
    assert data["userAccount"] == user.account

    cookie = next(c for c in user.session.cookies if c.name == "SESSION")
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cookie.path == "/api"


@allure.story("登录态")
@allure.title("注销后登录态失效，重复注销返回 50001")
def test_logout(user: AiGenClient):
    assert ok(user.post("/user/logout")) is True
    error(user.get("/user/get/login"), 40100)
    error(user.post("/user/logout"), 50001)
