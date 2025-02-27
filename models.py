# models.py
from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from pydantic import BaseModel

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String, index=True)
    free_tier = Column(Boolean, index=True, default=False)




class UserCreate(BaseModel):
    email: str
    password: str
