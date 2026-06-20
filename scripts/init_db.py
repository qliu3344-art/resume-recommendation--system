"""初始化数据库：建库 + 建表。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pymysql
from app.config import settings
from app.database import engine, Base
from app.models import resume, job  # noqa: F401 确保模型注册


def create_database():
    """创建数据库（如果不存在）。"""
    conn = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DB}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"✅ 数据库 `{settings.MYSQL_DB}` 已就绪")
    finally:
        conn.close()


def create_tables():
    """创建所有表。"""
    Base.metadata.create_all(bind=engine)
    print("✅ 所有表已创建")


if __name__ == "__main__":
    create_database()
    create_tables()
    print("🎉 数据库初始化完成")
