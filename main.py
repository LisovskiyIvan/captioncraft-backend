from email.mime import base
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request, Form
from fastapi.responses import JSONResponse
from tempfile import NamedTemporaryFile
import shutil
import os
from fastapi.middleware.cors import CORSMiddleware
from subs import create_shorts_video, extract_audio_from_video
import uuid
from fastapi.security import OAuth2PasswordRequestForm
from auth import  authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from datetime import timedelta
from database import engine, Base, SessionLocal, database
from sqlalchemy.orm import Session
from user import create_user, get_user
from models import UserCreate
import base64



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins; replace with a list of specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allow all headers; adjust as needed
)

@app.on_event("startup")
async def startup():
    await database.connect()
    Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register")
async def create(user: UserCreate,db: Session = Depends(get_db)):
    oldUser = get_user(db, user.email)
    if oldUser:
         raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = create_user(db=db, email=user.email, password=get_password_hash(user.password), free_tier=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"token": access_token, "token_type": "bearer"} 

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user(db=db, user_id=user_id)


@app.post("/login")
async def login_for_access_token(user: UserCreate, db: Session = Depends(get_db)):
    user = authenticate_user(db, user.email, user.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"token": access_token, "token_type": "bearer"}


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







