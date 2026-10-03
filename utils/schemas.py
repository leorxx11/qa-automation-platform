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
