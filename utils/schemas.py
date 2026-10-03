"""接口响应的 JSON Schema，用于契约校验。"""

POST_SCHEMA = {
    "type": "object",
    "required": ["userId", "id", "title", "body"],
    "properties": {
        "userId": {"type": "integer", "minimum": 1},
        "id": {"type": "integer", "minimum": 1},
        "title": {"type": "string", "minLength": 1},
        "body": {"type": "string"},
    },
}

USER_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "username", "email", "address", "company"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "username": {"type": "string"},
        "email": {"type": "string", "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
        "address": {
            "type": "object",
            "required": ["city", "geo"],
            "properties": {
                "city": {"type": "string"},
                "geo": {
                    "type": "object",
                    "required": ["lat", "lng"],
                },
            },
        },
        "company": {"type": "object", "required": ["name"]},
    },
}


# —— ai-gen-web ——
# 后端把 Long 序列化成字符串，避免前端精度丢失
_ID = {"type": "string", "pattern": r"^[1-9][0-9]*$"}
_DATETIME = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"}
_NULLABLE_STR = {"type": ["string", "null"]}

AIGEN_USER_VO_SCHEMA = {
    "type": "object",
    "required": ["id", "userAccount", "userName", "userRole", "createTime"],
    # 不允许出现额外字段，用来保证 userPassword 等敏感字段不会被返回
    "additionalProperties": False,
    "properties": {
        "id": _ID,
        "userAccount": {"type": "string"},
        "userName": _NULLABLE_STR,
        "userAvatar": _NULLABLE_STR,
        "userProfile": _NULLABLE_STR,
        "userRole": {"enum": ["user", "admin"]},
        "createTime": _DATETIME,
    },
}

AIGEN_LOGIN_USER_SCHEMA = {
    **AIGEN_USER_VO_SCHEMA,
    "required": AIGEN_USER_VO_SCHEMA["required"] + ["updateTime"],
    "properties": {**AIGEN_USER_VO_SCHEMA["properties"], "updateTime": _DATETIME},
}

AIGEN_APP_VO_SCHEMA = {
    "type": "object",
    "required": ["id", "appName", "initPrompt", "codeGenType", "priority", "userId", "createTime", "user"],
    "additionalProperties": False,
    "properties": {
        "id": _ID,
        "appName": {"type": "string"},
        "cover": _NULLABLE_STR,
        "initPrompt": {"type": "string", "minLength": 1},
        "codeGenType": {"enum": ["html", "multi_file", "vue_project"]},
        "deployKey": {"type": ["string", "null"], "pattern": r"^[0-9a-zA-Z]{6}$"},
        "deployedTime": {"anyOf": [_DATETIME, {"type": "null"}]},
        "priority": {"type": "integer"},
        "userId": _ID,
        "createTime": _DATETIME,
        "updateTime": _DATETIME,
        "user": AIGEN_USER_VO_SCHEMA,
    },
}


def aigen_page_schema(item_schema: dict) -> dict:
    return {
        "type": "object",
        "required": ["records", "pageNumber", "pageSize", "totalRow"],
        "properties": {
            "records": {"type": "array", "items": item_schema},
            "pageNumber": {"type": ["string", "integer"]},
            "pageSize": {"type": ["string", "integer"]},
            "totalRow": {"type": ["string", "integer"]},
        },
    }
