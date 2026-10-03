"""重建 ai-gen-web 的测试库并清空 Redis，保证每次运行都从干净状态开始。

用法：python scripts/ai_gen_web/reset_env.py <ai-gen-web>/sql/create_table.sql
连接参数取自环境变量 AIGEN_DB_* / AIGEN_REDIS_*。
"""
import os
import re
import sys

import pymysql
import redis


def sql_statements(path: str) -> list[str]:
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"^\s*(#|--).*$", "", text, flags=re.MULTILINE)
    return [s.strip() for s in text.split(";") if s.strip()]


def main(sql_path: str) -> None:
    conn = pymysql.connect(
        host=os.environ.get("AIGEN_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("AIGEN_DB_PORT", "3306")),
        user=os.environ["AIGEN_DB_USER"],
        password=os.environ["AIGEN_DB_PASSWORD"],
        autocommit=True,
    )
    with conn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS ai_gen_web")
        for statement in sql_statements(sql_path):
            cur.execute(statement)
        cur.execute("SHOW TABLES FROM ai_gen_web")
        tables = sorted(row[0] for row in cur.fetchall())
    conn.close()

    redis.Redis(
        host=os.environ.get("AIGEN_REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("AIGEN_REDIS_PORT", "6379")),
    ).flushdb()
    print(f"database rebuilt: {', '.join(tables)}; redis flushed")


if __name__ == "__main__":
    main(sys.argv[1])
