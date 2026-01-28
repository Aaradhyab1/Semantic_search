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

# Configure the SDK with the API key
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
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
    Constructs a prompt with retrieved context and generates a clean response.
    """
    context_parts = []
    for i, res in enumerate(search_results):
        # We label the source clearly so the AI can clean the "shabby" raw text
        context_parts.append(f"--- STUDY MATERIAL {i+1} (Source: {res['source']}) ---\n{res['text']}")
    
    context_text = "\n\n".join(context_parts)
    
    # Strict prompt to eliminate "shabby" noise like '9122024' or course codes
    prompt = f"""
    SYSTEM: You are a professional Engineering Professor. 
    TASK: Answer the student's question based ONLY on the provided Study Notes.
    
    STRICT CLEANING RULES:
    1. REMOVE NOISE: Ignore slide headers, university names, course codes, and timestamps like '9122024'.
    2. STRUCTURE: Use clean, short bullet points (pointers) for clarity.
    3. FORMATTING: **Bold** key technical concepts.
    4. HEADERS: Use '###' for major conceptual sections.
    5. CITE: End every point with its source number, e.g., [Source 1].

    STUDY NOTES:
    {context_text}

    STUDENT QUESTION: {query}
    """
    
    models_to_try = ['gemini-2.0-flash', 'gemini-2.0-flash-exp']
    
    for model_name in models_to_try:
        try:
            print(f"Attempting generation with {model_name}...")
            model = genai.GenerativeModel(model_name=model_name)
            
            response = model.generate_content(
                prompt,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            error_msg = str(e)
            print(f"Error with {model_name}: {error_msg}")
            if "429" in error_msg and model_name != models_to_try[-1]:
                print("Rate limit hit. Switching to fallback model...")
                continue
                
            if "429" in error_msg:
                 return "⚠️ AI Rate Limit Exceeded. You represent the Free Tier! Please wait ~30 seconds and try again."
            
            return f"AI Logic Error: {error_msg}. (Ensure your API key is correct)."
            
    return "The AI retrieved relevant data but could not generate a clean summary."

# --- 5. ROUTES ---

@app.post("/signup")
def signup(data: LoginRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken!")
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
        return {"ai_answer": "No relevant matches found. Try uploading more detailed notes!", "matches": []}

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
    
    # Add to FAISS with the filename for source tracking
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