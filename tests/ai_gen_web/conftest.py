from collections.abc import Callable

import pytest
import requests

from utils.aigen import MOCK_LLM_URL, AiGenClient, db_connect, ok, unique_account


def pytest_collection_modifyitems(items):
    for item in items:
        if "/ai_gen_web/" in str(item.fspath):
            item.add_marker(pytest.mark.ai_gen_web)


@pytest.fixture(scope="session")
def db():
    conn = db_connect()
    yield conn
    conn.close()


@pytest.fixture
def anon() -> AiGenClient:
    return AiGenClient()


@pytest.fixture
def new_user() -> Callable[..., AiGenClient]:
    """注册并登录一个新用户，返回其会话。"""

    def make(prefix: str = "qa") -> AiGenClient:
        client = AiGenClient()
        account = unique_account(prefix)
        ok(client.register(account))
        ok(client.login(account))
        return client

    return make


@pytest.fixture
def user(new_user) -> AiGenClient:
    return new_user("user")


@pytest.fixture
def other_user(new_user) -> AiGenClient:
    return new_user("other")


@pytest.fixture
def admin(new_user, db) -> AiGenClient:
    client = new_user("admin")
    # 后端每次请求都会从数据库重新读取登录用户，改库后无需重新登录
    with db.cursor() as cur:
        cur.execute("UPDATE user SET userRole = 'admin' WHERE userAccount = %s", (client.account,))
    return client


@pytest.fixture
def app_id(user) -> str:
    return user.add_app("做一个咖啡店官网，展示品牌故事与招牌饮品")


@pytest.fixture
def mock_llm_requests() -> Callable[[], list[dict]]:
    return lambda: requests.get(f"{MOCK_LLM_URL}/__requests", timeout=5).json()
