"""TodoMVC 页面对象（Page Object Model）。"""
import allure
from playwright.sync_api import Locator, Page


class TodoPage:
    def __init__(self, page: Page):
        self.page = page
        self.new_todo = page.get_by_placeholder("What needs to be done?")
        self.items = page.get_by_test_id("todo-item")
        self.titles = page.get_by_test_id("todo-title")
        self.count = page.get_by_test_id("todo-count")

    def open(self, base_url: str) -> "TodoPage":
        with allure.step("打开 TodoMVC"):
            self.page.goto(f"{base_url.rstrip('/')}/")
        return self

    def add(self, *texts: str) -> None:
        for text in texts:
            with allure.step(f"新增待办：{text}"):
                self.new_todo.fill(text)
                self.new_todo.press("Enter")

    def item(self, index: int) -> Locator:
        return self.items.nth(index)

    def toggle(self, index: int) -> None:
        with allure.step(f"勾选第 {index + 1} 条"):
            self.item(index).get_by_role("checkbox").check()

    def edit(self, index: int, text: str) -> None:
        with allure.step(f"编辑第 {index + 1} 条为：{text}"):
            self.item(index).dblclick()
            editor = self.item(index).get_by_role("textbox", name="Edit")
            editor.fill(text)
            editor.press("Enter")

    def delete(self, index: int) -> None:
        with allure.step(f"删除第 {index + 1} 条"):
            item = self.item(index)
            item.hover()
            item.get_by_role("button", name="Delete").click()

    def filter(self, name: str) -> None:
        with allure.step(f"切换筛选：{name}"):
            self.page.get_by_role("link", name=name).click()

    def clear_completed(self) -> None:
        with allure.step("清除已完成"):
            self.page.get_by_role("button", name="Clear completed").click()
