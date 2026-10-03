"""ai-gen-web 测试的公共工具：业务客户端、SSE 解析、数据库连接。"""
import json
import os
import uuid
from dataclasses import dataclass

import allure
import pymysql
import requests

from utils.api_client import ApiClient

API_BASE_URL = os.getenv("AIGEN_API_BASE_URL", "http://localhost:8123/api")
MOCK_LLM_URL = os.getenv("AIGEN_MOCK_LLM_URL", "http://127.0.0.1:18080")
DEFAULT_PASSWORD = "Passw0rd123"

# 与 mock_llm/server.py 中写入的文件、结束语保持一致
MOCK_FILES = ["package.json", "vite.config.js", "index.html", "src/main.js", "src/App.vue"]
MOCK_FINAL_TEXT = "项目已生成完毕：包含入口页面、根组件与 Vite 配置。"


def unique_account(prefix: str = "qa") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def db_connect() -> pymysql.Connection:
    return pymysql.connect(
        host=os.getenv("AIGEN_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("AIGEN_DB_PORT", "3306")),
        user=os.environ["AIGEN_DB_USER"],
        password=os.environ["AIGEN_DB_PASSWORD"],
        database="ai_gen_web",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


@dataclass
class SseResult:
    status_code: int
    content_type: str
    events: list[tuple[str, str]]
    raw: str

    @property
    def content(self) -> str:
        return "".join(json.loads(data)["d"] for event, data in self.events if event == "message")


def parse_sse(text: str) -> list[tuple[str, str]]:
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        event, data = "message", []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data.append(line[len("data:"):])
        events.append((event, "\n".join(data)))
    return events


class AiGenClient(ApiClient):
    """带登录态（Cookie）的 ai-gen-web 客户端，每个实例代表一个浏览器会话。"""

    def __init__(self, base_url: str = API_BASE_URL):
        super().__init__(base_url, timeout=30)
        self.account: str | None = None

    def register(self, account: str, password: str = DEFAULT_PASSWORD, check: str | None = None):
        return self.post("/user/register", json={
            "userAccount": account,
            "userPassword": password,
            "checkPassword": password if check is None else check,
        })

    def login(self, account: str, password: str = DEFAULT_PASSWORD):
        resp = self.post("/user/login", json={"userAccount": account, "userPassword": password})
        self.account = account
        return resp

    def add_app(self, init_prompt: str) -> str:
        return ok(self.post("/app/add", json={"initPrompt": init_prompt}))

    def chat(self, app_id: str, message: str) -> SseResult:
        with allure.step(f"SSE 对话 appId={app_id}"):
            resp = self.session.get(
                f"{self.base_url}/app/chat/gen/code",
                params={"appId": app_id, "message": message},
                headers={"Accept": "text/event-stream"},
                timeout=180,
            )
            resp.encoding = "utf-8"
            allure.attach(resp.text, name="SSE 原始响应", attachment_type=allure.attachment_type.TEXT)
            return SseResult(resp.status_code, resp.headers.get("Content-Type", ""), parse_sse(resp.text), resp.text)

    def history(self, app_id: str, **params):
        return self.get(f"/chatHistory/app/{app_id}", params=params)


def ok(resp: requests.Response):
    body = resp.json()
    assert resp.status_code == 200, resp.text
    assert body["code"] == 0, body
    return body["data"]


def error(resp: requests.Response, code: int, message: str | None = None) -> dict:
    body = resp.json()
    assert body["code"] == code, body
    assert body["data"] is None, body
    if message is not None:
        assert body["message"] == message, body
    return body
