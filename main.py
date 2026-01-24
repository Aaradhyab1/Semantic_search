import os
import shutil
from fastapi import FastAPI, UploadFile, File, Header # Added Header to imports
from pathlib import Path
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import models
from database import engine, get_db, Base
from sqlalchemy.orm import Session

# 1. JWT Configuration
SECRET_KEY = "super-secret-homie-key" # In real life, hide this in .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Tells FastAPI where to find the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# 2. Function to generate the token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
app = FastAPI()
# This creates the .db file and all tables defined in models.py
Base.metadata.create_all(bind=engine)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  #hashing starts and next two defs 


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# In a real app, this would be in your SQLite database
# I'm hashing 'password123' here
fake_users_db = {
    "homie_123": {
        "username": "homie_123",
        "hashed_password": hash_password("password123") 
    }
}

UPLOAD_DIR = Path("uploads")   #creating the folder upload(manually ho sakta?) 
UPLOAD_DIR.mkdir(exist_ok=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class SearchQuery(BaseModel):
    query: str


# 2. Mock function (This represents your friend's AI logic)
def friend_ai_logic(user_query: str, user_id: str):
    # This is where the Sentence-Transformers and FAISS will eventually live
    return [
        {"text": f"Found a match for '{user_query}' in your notes!", "score": 0.95},
        {"text": "Another relevant section from your PDF.", "score": 0.82}
    ]

@app.post("/signup")
def signup(data: LoginRequest, db: Session = Depends(get_db)):
    # 1. Check if user already exists
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken, homie!")

    # 2. Create new user with hashed password
    new_user = models.User(
        username=data.username,
        hashed_password=hash_password(data.password)
    )

    # 3. Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully! You can now log in."}

@app.post("/login")
async def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Look for the user in the database
    user = db.query(models.User).filter(models.User.username == data.username).first()
    
    if not user:
        return {"error": "User not found"}
    
    # Verify the password against the database record
    if not verify_password(data.password, user.hashed_password):
        return {"error": "Invalid password"}
    
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@app.get("/test-hash")
def test_hash(pw: str):
    return {"original": pw, "hashed": hash_password(pw)}


@app.post("/search")
async def search_notes(
    data: SearchQuery, 
    current_user: str = Depends(get_current_user) # The lock is now active!
):
    results = friend_ai_logic(data.query, current_user)
    
    return {
        "user": current_user,
        "query_received": data.query,
        "matches": results
    }

@app.get("/")
def home():
    return {"message": "System Online: Smart Notes Backend is running!"}

@app.post("/upload")                                 #upload xd
async def upload_file(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user) # Logic updated to use the token
):
    
    user_folder = UPLOAD_DIR / current_user     #dope shit- uploads file in the already created folder
    user_folder.mkdir(exist_ok=True)

    file_path = user_folder / file.filename     #esssentailly defines the destiantion
    
    
    with open(file_path, "wb") as buffer:      #open blank file + puts data in it
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "user": current_user,
        "filename": file.filename,
        "message": f"File uploaded successfully to {current_user}'s folder",
        "path": str(file_path)
    }

@app.get("/my-files")
def list_files(current_user: str = Depends(get_current_user)):
    user_folder = UPLOAD_DIR / current_user
    
    # Check if the folder exists, if not, they haven't uploaded anything
    if not user_folder.exists():
        return {"user": current_user, "files": [], "message": "No files found. Upload something, homie!"}
    
    # List all files in their private folder
    files = [f.name for f in user_folder.iterdir() if f.is_file()]
    
    return {
        "user": current_user,
        "file_count": len(files),
        "files": files
    }