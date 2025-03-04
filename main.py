from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request, Form
from fastapi.responses import JSONResponse
from tempfile import NamedTemporaryFile
import shutil
import os
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from subs import create_shorts_video, extract_audio_from_video
import uuid
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash, SECRET_KEY, ALGORITHM
)
from datetime import timedelta
from database import engine, Base, SessionLocal, reset_database, update_schema
from sqlalchemy.orm import Session
from user import create_user, get_user, get_user_by_email, get_user_statistics
from models import (
    UserCreate, User, SubscriptionPlan,
    UserResponse, UserStatisticsResponse
)
import base64
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import logging
from jose import jwt, JWTError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173/*").split(","),
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allow all headers; adjust as needed
)

# Создаем таблицы в базе данных при запуске приложения
@app.on_event("startup")
def startup():
    # Безопасно обновляем схему базы данных без потери данных
    update_schema()
    
    # Создаем базовые планы подписки
    with SessionLocal() as db:
        if db.query(SubscriptionPlan).count() == 0:
            logger.info("Creating default subscription plans...")
            basic_plan = SubscriptionPlan(
                name="Базовый",
                price=0.0,
                description="До 5 видео в месяц, базовое распознавание речи",
                max_videos=5
            )
            premium_plan = SubscriptionPlan(
                name="Премиум",
                price=999.0,
                description="Неограниченное количество видео, улучшенное распознавание речи",
                max_videos=-1  # -1 означает неограниченное количество
            )
            db.add_all([basic_plan, premium_plan])
            db.commit()
            logger.info("Default subscription plans created successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    # Создаем пользователя
    new_user = create_user(db, user)
    
    return new_user

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user(db=db, user_id=user_id)

@app.post("/login")
async def simple_login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "free_tier": user.free_tier
        }
    }

@app.post("/generate/videoandaudio")
async def upload_files(request: Request, video: UploadFile = File(...), audio: UploadFile = File(...), vosk: str = "vosk-model-small-en-us-0.15", db: Session = Depends(get_db)):
    token = request.headers.get("Authorization").split(" ")[1]
    user = await get_current_user(db=db, token=token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    name = str(uuid.uuid4()) + '.mp4'
    try:
        print(f"Received video file: {video.filename} with content type {video.content_type}")
        print(f"Received audio file: {audio.filename} with content type {audio.content_type}")

        with NamedTemporaryFile(delete=False, suffix=".mp4") as video_tempfile:
            shutil.copyfileobj(video.file, video_tempfile)
            video_temp_path = video_tempfile.name

        with NamedTemporaryFile(delete=False, suffix=".wav") as audio_tempfile:
            shutil.copyfileobj(audio.file, audio_tempfile)
            audio_temp_path = audio_tempfile.name

        try:
            create_shorts_video(video_temp_path, audio_temp_path, vosk, name)
        except Exception as e:
            print(f"Error during video creation: {e}")
            raise HTTPException(status_code=500, detail=f"Video creation failed: {e}")

        if not os.path.exists(name):
            raise HTTPException(status_code=500, detail="Output video file was not created.")

        with open(name, "rb") as file:
            video_data = base64.b64encode(file.read()).decode('utf-8')
        return JSONResponse(content={"video": video_data, "name": name})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    finally:
        if os.path.exists(video_temp_path):
            os.remove(video_temp_path)
        if os.path.exists(audio_temp_path):
            os.remove(audio_temp_path)
        if os.path.exists(name):
            os.remove(name)

@app.post("/generate/video")
async def upload_files_without_audio(request: Request, video: UploadFile = File(...), vosk: str = "vosk-model-small-en-us-0.15", db: Session = Depends(get_db)):
    token = request.headers.get("Authorization").split(" ")[1]
    user = await get_current_user(db=db, token=token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    base_name = str(uuid.uuid4())
    name = base_name + '.mp4'
    audio = base_name + '.wav'
    srt = base_name + '.srt'
    try:
        print(f"Received video file: {video.filename} with content type {video.content_type}")

        with NamedTemporaryFile(delete=False, suffix=".mp4") as video_tempfile:
            shutil.copyfileobj(video.file, video_tempfile)
            video_temp_path = video_tempfile.name

        try:
            extract_audio_from_video(video_temp_path, audio)
            create_shorts_video(video_temp_path, audio, vosk, name, srt)
        except Exception as e:
            print(f"Error during video creation: {e}")
            raise HTTPException(status_code=500, detail=f"Video creation failed: {e}")

        if not os.path.exists(name):
            raise HTTPException(status_code=500, detail="Output video file was not created.")

        with open(name, "rb") as file:
            video_data = base64.b64encode(file.read()).decode('utf-8')
        return JSONResponse(content={"video": video_data, "name": name})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    finally:
        if os.path.exists(video_temp_path):
            os.remove(video_temp_path)
        if os.path.exists(name):
            os.remove(name)
        if os.path.exists(audio):
            os.remove(audio)

@app.get("/user/statistics", response_model=UserStatisticsResponse)
async def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stats = get_user_statistics(db, current_user.id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Статистика не найдена"
        )
    return stats

class TokenRequest(BaseModel):
    token: str

@app.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Получает профиль текущего пользователя на основе JWT токена.
    
    Токен должен быть передан в заголовке Authorization в формате:
    Bearer <token>
    
    Функция get_current_user извлекает email из токена и находит 
    соответствующего пользователя в базе данных.
    """
    return current_user

@app.post("/profile/token", response_model=UserResponse)
async def get_profile_by_token(token_request: TokenRequest, db: Session = Depends(get_db)):
    """
    Получает профиль пользователя на основе JWT токена, переданного в теле запроса.
    
    Принимает JSON с полем token, содержащим JWT токен.
    Извлекает email из токена и находит соответствующего пользователя в базе данных.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token_request.token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

