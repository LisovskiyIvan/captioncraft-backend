# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from pydantic import validator

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    free_tier = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    videos = relationship("Video", back_populates="user")
    statistics = relationship("UserStatistics", back_populates="user", uselist=False)
    subscriptions = relationship("Subscription", back_populates="user")

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    filename = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String, default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="videos")
    subtitles = relationship("Subtitle", back_populates="video")

class Subtitle(Base):
    __tablename__ = 'subtitles'
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey('videos.id'))
    filename = Column(String)
    language = Column(String, default="ru")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    video = relationship("Video", back_populates="subtitles")

class UserStatistics(Base):
    __tablename__ = 'user_statistics'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    videos_processed = Column(Integer, default=0)
    total_video_duration = Column(Float, default=0.0)  # в секундах
    last_activity = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="statistics")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    price = Column(Float)
    description = Column(Text)
    max_videos = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic модели для API
class UserCreate(BaseModel):
    email: str
    password: str
    username: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    free_tier: bool
    created_at: datetime
    videos_count: Optional[int] = 0
    is_premium: Optional[bool] = None

    class Config:
        orm_mode = True
        
    @validator('is_premium', always=True)
    def set_is_premium(cls, v, values):
        # Если is_premium не задан, вычисляем его на основе free_tier
        if v is None and 'free_tier' in values:
            return not values['free_tier']
        return v

class VideoCreate(BaseModel):
    title: str

class VideoResponse(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class SubtitleResponse(BaseModel):
    id: int
    filename: str
    language: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserStatisticsResponse(BaseModel):
    videos_processed: int
    total_video_duration: float
    last_activity: datetime
    
    class Config:
        orm_mode = True

class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    max_videos: int
    
    class Config:
        orm_mode = True

class SubscriptionResponse(BaseModel):
    id: int
    plan: SubscriptionPlanResponse
    start_date: datetime
    end_date: datetime
    is_active: bool
    
    class Config:
        orm_mode = True
