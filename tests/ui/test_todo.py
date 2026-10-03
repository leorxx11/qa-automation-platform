import allure
import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.ui, allure.epic("UI 自动化"), allure.feature("TodoMVC")]


@allure.story("新增")
@allure.title("新增一条待办")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_todo(todo):
    todo.add("写自动化用例")
    expect(todo.titles).to_have_text(["写自动化用例"])
    expect(todo.count).to_have_text("1 item left")


@allure.story("新增")
@allure.title("新增多条待办，计数同步更新")
def test_add_multiple_todos(todo):
    todo.add("接口测试", "UI 测试", "生成报告")
    expect(todo.titles).to_have_text(["接口测试", "UI 测试", "生成报告"])
    expect(todo.count).to_have_text("3 items left")


@allure.story("完成")
@allure.title("完成待办后，按 Active / Completed 筛选")
@allure.severity(allure.severity_level.CRITICAL)
def test_complete_and_filter(todo):
    todo.add("接口测试", "UI 测试")
    todo.toggle(0)
    expect(todo.count).to_have_text("1 item left")

    todo.filter("Active")
    expect(todo.titles).to_have_text(["UI 测试"])

    todo.filter("Completed")
    expect(todo.titles).to_have_text(["接口测试"])


@allure.story("完成")
@allure.title("清除已完成的待办")
def test_clear_completed(todo):
    todo.add("接口测试", "UI 测试")
    todo.toggle(1)
    todo.clear_completed()
    expect(todo.titles).to_have_text(["接口测试"])


@allure.story("编辑")
@allure.title("双击编辑待办内容")
def test_edit_todo(todo):
    todo.add("写用例")
    todo.edit(0, "写并调试用例")
    expect(todo.titles).to_have_text(["写并调试用例"])


@allure.story("删除")
@allure.title("删除待办")
def test_delete_todo(todo):
    todo.add("接口测试", "UI 测试")
    todo.delete(0)
    expect(todo.titles).to_have_text(["UI 测试"])
    expect(todo.count).to_have_text("1 item left")
