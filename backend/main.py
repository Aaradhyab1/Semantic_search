import os
import shutil
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Header, Depends, HTTPException, status
from pathlib import Path
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv

from . import models
from .database import engine, get_db, Base
from .file_parser import extract_text
from .preprocessing import clean_text
from .chunking import chunk_text
from .embeddings import embed_texts
from .vector_storing import vector_store

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- 1. JWT & AI CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- 2. AUTHENTICATION HELPERS ---
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- 3. PYDANTIC MODELS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class SearchQuery(BaseModel):
    query: str

# --- 4. RAG GENERATION LOGIC ---
def get_ai_answer(query: str, search_results: list):
    """
    Constructs a prompt with retrieved context and generates a clean, pointer-based response.
    """
    context_parts = []
    for i, res in enumerate(search_results):
        context_parts.append(f"[Source {i+1}: {res['source']}]\n{res['text']}")
    
    context_text = "\n\n".join(context_parts)
    
    # Structured prompt for cleaner, pointer-based output
    prompt = f"""
    SYSTEM: You are a professional academic assistant. Answer the user's question clearly.
    TASK: Use ONLY the provided Study Notes to answer.
    
    OUTPUT FORMAT:
    - Use clean bullet points (pointers).
    - Use bold headers for different sections.
    - Ignore administrative noise (dates like 9122024, slide numbers, headers).
    - Provide a concise summary first, followed by detailed pointers.

    CITATION RULE: Cite every fact using [Source X].

    STUDY NOTES CONTEXT:
    {context_text}

    USER QUESTION: {query}
    """
    
    try:
        # Initialize the model directly here to avoid configuration mismatches
        ai_model = genai.GenerativeModel('gemini-1.5-flash')
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Log the error for debugging
        print(f"AI Error: {str(e)}")
        return "The AI is currently processing your request. Please try your query again in a moment."

# --- 5. ROUTES ---

@app.post("/signup")
def signup(data: LoginRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken, homie!")
    new_user = models.User(username=data.username, hashed_password=hash_password(data.password))
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"message": "User created successfully!"}

@app.post("/login")
async def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        return {"error": "Invalid credentials"}
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/search")
async def search_notes(data: SearchQuery, current_user: str = Depends(get_current_user)):
    search_results = vector_store.search(data.query, top_k=5)
    
    if not search_results:
        return {"ai_answer": "No relevant matches found. Upload more notes!", "matches": []}

    ai_answer = get_ai_answer(data.query, search_results)

    return {
        "user": current_user,
        "ai_answer": ai_answer,
        "matches": search_results 
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    user_folder = UPLOAD_DIR / current_user
    user_folder.mkdir(exist_ok=True)
    file_path = user_folder / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    raw_text = extract_text(file) 
    cleaned_text = clean_text(raw_text)
    chunks = chunk_text(cleaned_text)
    embeddings = embed_texts(chunks)
    
    vector_store.add(chunks, embeddings, filename=file.filename)
        
    return {"filename": file.filename, "chunks_created": len(chunks)}

@app.get("/my-files")
def list_files(current_user: str = Depends(get_current_user)):
    user_folder = UPLOAD_DIR / current_user
    if not user_folder.exists():
        return {"files": []}
    files = [f.name for f in user_folder.iterdir() if f.is_file()]
    return {"files": files}

@app.get("/")
def home():
    return {"message": "System Online"}