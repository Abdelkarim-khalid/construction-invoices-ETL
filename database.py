from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLITE_FILE_NAME = "construction_system.db"
DATABASE_URL = f"sqlite:///{SQLITE_FILE_NAME}"

# إعداد المحرك (connect_args مهمة عشان SQLite يقبل تعدد الـ Threads)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# دالة مساعدة للحصول على جلسة داتابيز لكل Request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
