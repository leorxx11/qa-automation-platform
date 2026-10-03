import json
import re
import time

import allure
import pytest

from utils.aigen import MOCK_FILES, MOCK_FINAL_TEXT, AiGenClient, error, ok

pytestmark = [pytest.mark.api, allure.epic("ai-gen-web 接口"), allure.feature("AI 对话生成")]

PREVIEW_TIMEOUT = 300


def history_records(client: AiGenClient, app_id: str, **params) -> list[dict]:
    return ok(client.history(app_id, **params))["records"]


@allure.story("流式生成")
@allure.title("SSE 输出格式正确：逐段 JSON 包装，以 done 事件结束")
@allure.severity(allure.severity_level.BLOCKER)
def test_chat_stream(user: AiGenClient, app_id):
    result = user.chat(app_id, "做一个咖啡店官网")

    assert result.status_code == 200
    assert result.content_type.startswith("text/event-stream")
    assert result.events[-1] == ("done", "")
    for event, data in result.events[:-1]:
        assert event == "message"
        assert set(json.loads(data)) == {"d"}

    content = result.content
    for path in MOCK_FILES:
        assert f"[工具调用] 写入文件 {path}" in content
    assert content.count("[选择工具] 写入文件") == len(MOCK_FILES)
    assert content.endswith(MOCK_FINAL_TEXT)


@allure.story("对话历史")
@allure.title("一轮对话后保存用户消息和 AI 回复，按时间倒序返回")
@allure.severity(allure.severity_level.CRITICAL)
def test_history_saved(user: AiGenClient, app_id):
    user.chat(app_id, "第一轮：做一个咖啡店官网")

    records = history_records(user, app_id)
    assert [r["messageType"] for r in records] == ["ai", "user"]
    assert records[1]["message"] == "第一轮：做一个咖啡店官网"
    assert "[工具调用] 写入文件 package.json" in records[0]["message"]
    assert records[0]["message"].endswith(MOCK_FINAL_TEXT)


@allure.story("对话历史")
@allure.title("第二轮对话会把上一轮内容作为上下文发给模型")
def test_chat_memory(user: AiGenClient, app_id, mock_llm_requests):
    marker = f"记忆标记-{app_id}"
    user.chat(app_id, f"{marker}：做一个咖啡店官网")
    user.chat(app_id, "第二轮：把主色调改成绿色")

    second_round = [
        r for r in mock_llm_requests()
        if r["messages"][-1]["role"] == "user" and r["messages"][-1]["content"] == "第二轮：把主色调改成绿色"
    ]
    assert len(second_round) == 1
    messages = second_round[0]["messages"]
    assert messages[0]["role"] == "system"
    assert any(m["role"] == "user" and marker in m["content"] for m in messages[1:-1])


@allure.story("对话历史")
@allure.title("游标分页：用最后一条的 createTime 加载更早的记录")
def test_history_cursor(user: AiGenClient, app_id):
    user.chat(app_id, "第一轮")
    # createTime 精度为秒，两轮之间隔开 1 秒，保证游标边界明确
    time.sleep(1.1)
    user.chat(app_id, "第二轮")

    first = history_records(user, app_id, pageSize=2)
    assert [r["message"] for r in first if r["messageType"] == "user"] == ["第二轮"]

    older = history_records(user, app_id, pageSize=2, lastCreateTime=first[-1]["createTime"])
    assert [r["messageType"] for r in older] == ["ai", "user"]
    assert older[1]["message"] == "第一轮"
    assert history_records(user, app_id, pageSize=2, lastCreateTime=older[-1]["createTime"]) == []


@allure.story("对话历史")
@allure.title("对话历史分页参数校验：pageSize={size}")
@pytest.mark.parametrize("size", [0, 51])
def test_history_page_size(user: AiGenClient, app_id, size):
    error(user.history(app_id, pageSize=size), 40000, "每页数量必须在 1-50 之间")


@allure.story("对话历史")
@allure.title("对话历史仅创建者和管理员可见")
def test_history_visibility(user: AiGenClient, other_user: AiGenClient, admin: AiGenClient, app_id):
    user.chat(app_id, "做一个咖啡店官网")

    error(other_user.history(app_id), 40101)
    assert len(history_records(admin, app_id)) == 2

    page = ok(admin.post("/chatHistory/admin/list/page/vo", json={"pageNum": 1, "pageSize": 10, "appId": app_id}))
    assert [r["messageType"] for r in page["records"]] == ["ai", "user"]


@allure.story("流式生成")
@allure.title("只有创建者能与应用对话，其他人的请求被拒绝且不写入历史")
def test_chat_other_users_app(user: AiGenClient, other_user: AiGenClient, app_id, mock_llm_requests):
    before = len(mock_llm_requests())
    result = other_user.chat(app_id, "改一下别人的应用")
    assert result.status_code != 200 or json.loads(result.raw)["code"] == 40101
    assert ("done", "") not in result.events
    assert history_records(user, app_id) == []
    assert len(mock_llm_requests()) == before


@allure.story("流式生成")
@allure.title("未登录不能对话")
def test_chat_requires_login(anon: AiGenClient, app_id):
    result = anon.chat(app_id, "做一个网站")
    assert result.status_code != 200 or json.loads(result.raw)["code"] == 40100
    assert ("done", "") not in result.events


@allure.story("流式生成")
@allure.title("SSE 接口出错时，浏览器能拿到业务错误码")
@pytest.mark.xfail(
    strict=True,
    reason="已知缺陷：EventSource 只接受 text/event-stream，BaseResponse 无法按该类型输出，"
    "后端返回 HTTP 500 空响应，前端拿不到 40100/40101 等错误信息",
)
def test_chat_error_is_readable(anon: AiGenClient, app_id):
    result = anon.chat(app_id, "做一个网站")
    assert result.status_code == 200
    assert json.loads(result.raw)["code"] == 40100


@allure.story("流式生成")
@allure.title("模型调用失败时，失败信息也记录到对话历史")
def test_chat_model_failure(user: AiGenClient, app_id):
    user.chat(app_id, "MOCK_ERROR 触发模型失败")

    records = history_records(user, app_id)
    assert [r["messageType"] for r in records] == ["ai", "user"]
    assert records[0]["message"].startswith("AI回复失败")


@allure.story("删除应用")
@allure.title("删除应用时一并删除其对话历史")
def test_delete_app_removes_history(user: AiGenClient, app_id, db):
    user.chat(app_id, "做一个咖啡店官网")
    ok(user.post("/app/delete", json={"id": app_id}))

    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM chat_history WHERE appId = %s AND isDelete = 0", (app_id,))
        assert cur.fetchone()["n"] == 0


@allure.story("预览与部署")
@allure.title("生成后自动构建 Vue 工程，可通过静态资源地址预览，并可部署")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.slow
def test_preview_and_deploy(user: AiGenClient, anon: AiGenClient, app_id):
    user.chat(app_id, "做一个咖啡店官网")

    preview = f"/static/vue_project_{app_id}/dist/index.html"
    with allure.step("等待后台 npm install && build 完成"):
        deadline = time.time() + PREVIEW_TIMEOUT
        while (resp := anon.session.get(f"{anon.base_url}{preview}", timeout=10)).status_code != 200:
            assert time.time() < deadline, "预览构建超时"
            time.sleep(3)
    assert resp.headers["Content-Type"].startswith("text/html")
    assert '<div id="app"></div>' in resp.text

    url = ok(user.post("/app/deploy", json={"appId": app_id}))
    key = re.fullmatch(r"http://localhost:8080/([0-9a-zA-Z]{6})", url).group(1)
    app = ok(user.get("/app/get/vo", params={"id": app_id}))
    assert app["deployKey"] == key
    assert app["deployedTime"] is not None

    with allure.step("再次部署沿用同一个 deployKey"):
        assert ok(user.post("/app/deploy", json={"appId": app_id})) == url


@allure.story("预览与部署")
@allure.title("部署失败：{case}")
@pytest.mark.parametrize("case", ["还没有生成代码", "部署别人的应用"])
def test_deploy_failed(user: AiGenClient, other_user: AiGenClient, app_id, case):
    if case == "还没有生成代码":
        error(user.post("/app/deploy", json={"appId": app_id}), 40400, "应用代码不存在，请先生成代码")
    else:
        error(other_user.post("/app/deploy", json={"appId": app_id}), 40101)
