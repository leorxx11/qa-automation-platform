import os

import allure
import pytest
from playwright.sync_api import Page, expect

from utils.aigen import API_BASE_URL, AiGenClient

WEB_BASE_URL = os.getenv("AIGEN_WEB_BASE_URL", "http://localhost:4173")

# 首页会并发请求多个列表接口，默认 5 秒在慢环境下偏紧
expect.set_options(timeout=15_000)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page: Page):
    yield
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        allure.attach(page.screenshot(full_page=True), name="失败截图", attachment_type=allure.attachment_type.PNG)


@pytest.fixture
def web_url() -> str:
    return WEB_BASE_URL


@pytest.fixture
def login_as(page: Page):
    """把接口登录得到的会话 Cookie 注入浏览器，省去每条用例走一遍登录页。"""

    def inject(client: AiGenClient) -> Page:
        session = client.session.cookies.get("SESSION")
        page.context.add_cookies([{"name": "SESSION", "value": session, "url": API_BASE_URL}])
        return page

    return inject
