"""OpenAI 兼容的 mock 大模型，供 ai-gen-web 的自动化测试使用。

行为固定、可预期：
- 每轮对话按顺序发起 writeFile 工具调用，每次写一个文件，写出一个最小的 Vite + Vue 工程
- 文件写完后返回一段结束语
- 用户消息包含 MOCK_ERROR 时返回 500，用于验证失败分支
- 非流式请求返回标准的 chat.completion：创建应用时的智能路由固定选 VUE_PROJECT，
  与上面写出的 Vue 工程一致；工作流里的代码质检、图片规划返回能解析的最小 JSON

调试接口：
- GET  /__requests  返回收到的全部请求体
- POST /__reset     清空请求记录
"""
import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

FINAL_TEXT = "项目已生成完毕：包含入口页面、根组件与 Vite 配置。"

# 非流式请求按系统提示词识别调用方，返回对应的固定答案
STRUCTURED_REPLIES = [
    ("代码生成方案路由器", "VUE_PROJECT"),
    ("代码质量检查专家", json.dumps({"isValid": True, "errors": [], "suggestions": []})),
    ("图片收集规划师", json.dumps(
        {"contentImageTasks": [], "illustrationTasks": [], "diagramTasks": [], "logoTasks": []})),
]

PROJECT_FILES = [
    (
        "package.json",
        json.dumps(
            {
                "name": "mock-generated-app",
                "private": True,
                "type": "module",
                "scripts": {"build": "vite build"},
                "dependencies": {"vue": "^3.5.0"},
                "devDependencies": {"vite": "^7.1.0", "@vitejs/plugin-vue": "^6.0.0"},
            },
            indent=2,
        ),
    ),
    (
        "vite.config.js",
        "import { defineConfig } from 'vite'\n"
        "import vue from '@vitejs/plugin-vue'\n\n"
        "export default defineConfig({\n  base: './',\n  plugins: [vue()],\n})\n",
    ),
    (
        "index.html",
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n  <meta charset="UTF-8" />\n'
        "  <title>Mock App</title>\n</head>\n<body>\n"
        '  <div id="app"></div>\n  <script type="module" src="/src/main.js"></script>\n'
        "</body>\n</html>\n",
    ),
    (
        "src/main.js",
        "import { createApp } from 'vue'\nimport App from './App.vue'\n\ncreateApp(App).mount('#app')\n",
    ),
    (
        "src/App.vue",
        '<template>\n  <h1 class="title">Hello from mock LLM</h1>\n</template>\n\n'
        "<style>\n.title { color: #3b82f6; }\n</style>\n",
    ),
]

_requests: list[dict] = []
_lock = Lock()


def _chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "mock",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _tool_call_chunks(path: str, content: str) -> list[dict]:
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    arguments = json.dumps({"relativeFilePath": path, "content": content}, ensure_ascii=False)
    chunks = [
        _chunk({"role": "assistant", "content": None, "tool_calls": [
            {"index": 0, "id": call_id, "type": "function",
             "function": {"name": "writeFile", "arguments": ""}},
        ]})
    ]
    for part in _split(arguments, 40):
        chunks.append(_chunk({"tool_calls": [{"index": 0, "function": {"arguments": part}}]}))
    chunks.append(_chunk({}, "tool_calls"))
    return chunks


def _text_chunks(text: str) -> list[dict]:
    chunks = [_chunk({"role": "assistant", "content": ""})]
    chunks += [_chunk({"content": part}) for part in _split(text, 6)]
    chunks.append(_chunk({}, "stop"))
    return chunks


def _next_file(messages: list[dict]) -> tuple[str, str] | None:
    """本轮还没写的下一个文件，全部写完返回 None。"""
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    written = sum(1 for m in messages[last_user:] if m["role"] == "tool")
    return PROJECT_FILES[written] if written < len(PROJECT_FILES) else None


def _plan_response(messages: list[dict]) -> list[dict]:
    next_file = _next_file(messages)
    if next_file:
        return _tool_call_chunks(*next_file)
    return _text_chunks(FINAL_TEXT)


def _completion(body: dict) -> dict:
    """非流式请求的完整响应。"""
    messages = body["messages"]
    system = "".join(_user_text(m) for m in messages if m["role"] == "system")
    reply = next((text for marker, text in STRUCTURED_REPLIES if marker in system), None)
    next_file = None if reply is not None or not body.get("tools") else _next_file(messages)
    if next_file:
        path, content = next_file
        arguments = json.dumps({"relativeFilePath": path, "content": content}, ensure_ascii=False)
        message = {"role": "assistant", "content": None, "tool_calls": [
            {"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
             "function": {"name": "writeFile", "arguments": arguments}},
        ]}
        finish_reason = "tool_calls"
    else:
        message = {"role": "assistant", "content": FINAL_TEXT if reply is None else reply}
        finish_reason = "stop"
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "mock",
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


def _user_text(message: dict) -> str:
    content = message["content"]
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[mock-llm] {self.command} {self.path} {args[1] if len(args) > 1 else ''}", flush=True)

    def _send_json(self, status: int, body) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/__requests":
            with _lock:
                self._send_json(200, list(_requests))
        elif self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/__reset":
            with _lock:
                _requests.clear()
            self._send_json(200, {"status": "ok"})
            return
        if not self.path.endswith("/chat/completions"):
            self._send_json(404, {"error": "not found"})
            return

        with _lock:
            _requests.append(body)
        messages = body["messages"]
        user_messages = [m for m in messages if m["role"] == "user"]
        if "MOCK_ERROR" in _user_text(user_messages[-1]):
            self._send_json(500, {"error": {"message": "mock upstream failure", "type": "server_error"}})
            return

        if not body.get("stream"):
            self._send_json(200, _completion(body))
            return
        chunks = _plan_response(messages)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
        if body.get("stream_options", {}).get("include_usage"):
            usage = {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            self.wfile.write(f"data: {json.dumps({'id': 'chatcmpl-mock', 'object': 'chat.completion.chunk', 'model': 'mock', 'choices': [], 'usage': usage})}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[mock-llm] listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
