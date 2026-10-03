"""ai-gen-web 前端的页面对象（Page Object Model）。"""
import allure
from playwright.sync_api import Locator, Page


class BasePage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def goto(self, path: str) -> None:
        self.page.goto(f"{self.base_url}{path}")

    def toast(self, text: str) -> Locator:
        return self.page.locator(".ant-message").get_by_text(text)

    @property
    def header_user(self) -> Locator:
        return self.page.locator(".global-header .user-info")


class AuthPage(BasePage):
    @property
    def submit(self) -> Locator:
        return self.page.locator("#userRegisterPage, #userLoginPage").locator("button[type=submit]")

    def register(self, account: str, password: str, check: str | None = None) -> None:
        with allure.step(f"注册账号 {account}"):
            self.goto("/user/register")
            self.page.get_by_placeholder("请输入账号").fill(account)
            self.page.get_by_placeholder("请输入密码").fill(password)
            self.page.get_by_placeholder("请确认密码").fill(password if check is None else check)
            self.submit.click()

    def login(self, account: str, password: str) -> None:
        with allure.step(f"登录账号 {account}"):
            self.goto("/user/login")
            self.page.get_by_placeholder("请输入账号").fill(account)
            self.page.get_by_placeholder("请输入密码").fill(password)
            self.submit.click()


class HomePage(BasePage):
    def open(self) -> "HomePage":
        with allure.step("打开首页"):
            self.goto("/")
        return self

    def create_app(self, prompt: str) -> None:
        with allure.step(f"输入需求并开始创作：{prompt}"):
            self.page.locator("#creation-prompt").fill(prompt)
            self.page.get_by_role("button", name="开始创作").click()

    def app_card(self, app_name: str) -> Locator:
        return self.page.locator(".app-card").filter(has=self.page.get_by_role("heading", name=app_name))


class ChatPage(BasePage):
    @property
    def messages(self) -> Locator:
        return self.page.locator(".message-list")

    @property
    def status(self) -> Locator:
        return self.page.locator(".workspace-status")

    @property
    def preview(self) -> Locator:
        return self.page.locator("iframe")


class UserManagePage(BasePage):
    def open(self) -> "UserManagePage":
        with allure.step("打开用户管理页"):
            self.goto("/admin/userManage")
        return self

    def search(self, account: str) -> None:
        with allure.step(f"按账号搜索 {account}"):
            self.page.get_by_placeholder("输入账号").fill(account)
            self.page.locator("#userManagePage button[type=submit]").click()

    @property
    def rows(self) -> Locator:
        return self.page.locator(".ant-table-tbody tr.ant-table-row")
