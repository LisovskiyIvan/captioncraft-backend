# crud.py
from sqlalchemy.orm import Session
from models import User, UserCreate, UserStatistics, Video

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    """
    Получает пользователя по email
    """
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Получаем количество видео пользователя
        videos_count = db.query(Video).filter(Video.user_id == user.id).count()
        # Добавляем это поле к объекту пользователя
        setattr(user, 'videos_count', videos_count)
    
    return user

def create_user(db: Session, user: UserCreate):
    # Импортируем здесь, чтобы избежать циклического импорта
    from auth import get_password_hash
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        password=hashed_password,
        username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Создаем статистику для пользователя
    user_stats = UserStatistics(user_id=db_user.id)
    db.add(user_stats)
    db.commit()
    
    return db_user

def get_user_statistics(db: Session, user_id: int):
    return db.query(UserStatistics).filter(UserStatistics.user_id == user_id).first()

def update_user_statistics(db: Session, user_id: int, video_duration: float = 0):
    stats = get_user_statistics(db, user_id)
    if stats:
        stats.videos_processed += 1
        stats.total_video_duration += video_duration
        db.commit()
        db.refresh(stats)
    return stats
