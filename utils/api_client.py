"""带 Allure 步骤与附件记录的 HTTP 客户端。"""
import json

import allure
import requests


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json; charset=UTF-8"})

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        with allure.step(f"{method.upper()} {path}"):
            if "json" in kwargs:
                allure.attach(
                    json.dumps(kwargs["json"], ensure_ascii=False, indent=2),
                    name="请求体",
                    attachment_type=allure.attachment_type.JSON,
                )
            resp = self.session.request(method, url, **kwargs)
            allure.attach(
                f"{resp.status_code} {resp.reason}\n耗时: {resp.elapsed.total_seconds() * 1000:.0f} ms",
                name="响应状态",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(resp.text, name="响应体", attachment_type=allure.attachment_type.JSON)
            return resp

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
