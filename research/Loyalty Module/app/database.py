from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL

# isolation_level READ COMMITTED (Postgres default) + SELECT ... FOR UPDATE row
# locks in services.py is what makes concurrent earn/redeem calls on the same
# wallet serialize correctly instead of racing.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
