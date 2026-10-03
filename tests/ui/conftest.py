import allure
import pytest

from pages.todo_page import TodoPage


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page):
    # 依赖 page，因此会在 page 关闭之前执行清理
    yield
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        allure.attach(
            page.screenshot(full_page=True),
            name="失败截图",
            attachment_type=allure.attachment_type.PNG,
        )


@pytest.fixture
def todo(page, base_url) -> TodoPage:
    return TodoPage(page).open(base_url)
