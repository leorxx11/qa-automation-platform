import re

import allure
import pytest
from playwright.sync_api import Page, expect

from pages.ai_gen_web.pages import AuthPage, ChatPage, HomePage, UserManagePage
from utils.aigen import DEFAULT_PASSWORD, MOCK_FINAL_TEXT, AiGenClient, ok, unique_account

pytestmark = [pytest.mark.ui, allure.epic("ai-gen-web UI"), allure.feature("前端主流程")]

PREVIEW_TIMEOUT_MS = 300_000


@allure.story("注册与登录")
@allure.title("在页面上注册新账号并登录，顶栏显示用户名")
@allure.severity(allure.severity_level.BLOCKER)
def test_register_and_login(page: Page, web_url):
    auth = AuthPage(page, web_url)
    account = unique_account("ui")

    auth.register(account, DEFAULT_PASSWORD)
    expect(auth.toast("注册成功")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/user/login$"))

    auth.login(account, DEFAULT_PASSWORD)
    expect(auth.toast("登录成功")).to_be_visible()
    expect(auth.header_user).to_contain_text(account)


@allure.story("注册与登录")
@allure.title("密码错误时提示登录失败")
def test_login_failed(page: Page, web_url):
    auth = AuthPage(page, web_url)
    auth.login(unique_account("ui"), DEFAULT_PASSWORD)
    expect(auth.toast("登录失败：用户不存在或密码错误")).to_be_visible()
    expect(auth.header_user).to_have_count(0)


@allure.story("创作")
@allure.title("首页输入需求创建应用，自动开始生成并展示预览")
@allure.severity(allure.severity_level.BLOCKER)
@pytest.mark.slow
def test_create_app_and_generate(login_as, user: AiGenClient, web_url):
    page = login_as(user)
    HomePage(page, web_url).open().create_app("做一个咖啡店官网，展示招牌饮品")

    expect(page).to_have_url(re.compile(r"/app/chat/\d+$"))
    chat = ChatPage(page, web_url)
    expect(chat.messages).to_contain_text("做一个咖啡店官网，展示招牌饮品")
    expect(chat.messages).to_contain_text("[工具调用] 写入文件 package.json", timeout=60_000)
    expect(chat.messages).to_contain_text(MOCK_FINAL_TEXT, timeout=60_000)

    with allure.step("等待后台构建完成，预览加载生成的页面"):
        expect(chat.status).to_have_text("预览就绪", timeout=PREVIEW_TIMEOUT_MS)
        expect(page.frame_locator("iframe").get_by_text("Hello from mock LLM")).to_be_visible()


@allure.story("创作")
@allure.title("首页「我的作品」列出自己创建的应用")
def test_my_works(login_as, user: AiGenClient, web_url):
    user.add_app("花店落地页，突出节日花束")
    page = login_as(user)
    home = HomePage(page, web_url).open()
    expect(home.app_card("花店落地页，突出节日花束")).to_be_visible()


@allure.story("权限")
@allure.title("普通用户访问管理页会被拦截并跳到登录页")
def test_admin_page_blocked(login_as, user: AiGenClient, web_url):
    page = login_as(user)
    manage = UserManagePage(page, web_url).open()
    expect(manage.toast("没有权限访问该页面")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/user/login\?redirect=/admin/userManage$"))


@allure.story("权限")
@allure.title("管理员在用户管理页按账号搜索用户")
def test_admin_search_user(login_as, admin: AiGenClient, user: AiGenClient, web_url):
    page = login_as(admin)
    manage = UserManagePage(page, web_url).open()
    manage.search(user.account)
    expect(manage.rows).to_have_count(1)
    expect(manage.rows.first).to_contain_text(user.account)
