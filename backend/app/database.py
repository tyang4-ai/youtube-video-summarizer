from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

def create_db_engine(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    return engine

SessionLocal = None

def init_db(url: str):
    global SessionLocal
    engine = create_db_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return engine

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
