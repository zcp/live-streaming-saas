# app/core/test_db.py
from sqlalchemy import text
from app.core.database import engine

def test_db_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("数据库连接成功！")
            return True
    except Exception as e:
        print(f"数据库连接失败：{str(e)}")
        return False

if __name__ == "__main__":
    test_db_connection()
    # 在 Python 交互式环境中测试
    from app.core.database import Base
    from sqlalchemy import create_engine
    from app.models.stream import *
    from app.models.playback import *
    from app.models.storage import *
    from app.models.monitoring import *

    # 创建所有表
    engine = create_engine("postgresql://postgres:324zq999@localhost:5432/livestream_saas")
    Base.metadata.create_all(engine)