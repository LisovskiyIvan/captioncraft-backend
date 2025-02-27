# crud.py
from sqlalchemy.orm import Session
from models import User

def create_user(db: Session, email: str, password: str, free_tier: bool):
    db_user = User(email=email, password=password, free_tier=free_tier)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
