from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    full_name = Column(String)
    is_subscribed = Column(Boolean, default=False)
    is_participated = Column(Boolean, default=False)

class Contest(Base):
    __tablename__ = 'contests'
    
    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=True)
    winner_id = Column(Integer, nullable=True)

engine = create_engine('sqlite:///contest.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()