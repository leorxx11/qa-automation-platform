import os

import pytest

from utils.api_client import ApiClient


@pytest.fixture(scope="session")
def api() -> ApiClient:
    base_url = os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com")
    return ApiClient(base_url)
