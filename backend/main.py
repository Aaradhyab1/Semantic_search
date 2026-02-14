import os
import shutil
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
from .local_llm import get_ai_summary

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- 1. JWT & AI CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    context_parts = []
    for i, res in enumerate(search_results):
        # We limit each chunk to 2500 chars to avoid overflowing the token limit
        clean_chunk = res['text'].replace("\n", " ").strip()[:2500]
        context_parts.append(f"--- SOURCE {i+1} ({res['source']}) ---\n{clean_chunk}")
    
    context_text = "\n\n".join(context_parts)
    
    system_prompt = """
    You are a professional Engineering Professor. 
    Your goal is to answer the Student's Question using ONLY the provided Study Notes.
    
    STRICT RULES:
    1.  **Answer Directly:** Start with the answer. Do not say "Here is the answer".
    2.  **No Hallucinations:** If the answer is not in the notes, say "I couldn't find that specific information in the uploaded notes."
    3.  **Clean Up:** Ignore messy OCR text like "9122024", headers, or page numbers.
    4.  **Formatting:** - Use **Bold** for key terms.
        - Use bullet points for lists.
        - Keep paragraphs short (3-4 sentences).
    5.  **Citations:** End key points with [Source X].
    """

    # 3. Call Groq API
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": f"STUDY NOTES:\n{context_text}\n\nSTUDENT QUESTION: {query}",
                }
            ],
            model="llama3-8b-8192", # Fast and smart
            temperature=0.3,        # Low temperature = Less gibberish
            max_tokens=1024,
        )

        return chat_completion.choices[0].message.content

    except RateLimitError:
        return "⚠️ System is busy (Rate Limit Reached). Please wait 30 seconds and try again."
    except Exception as e:
        print(f"Groq API Error: {e}")
        return "Sorry, I encountered an error generating the response."

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
    # 1. Retrieve Raw Chunks (Limit to 3 for local speed)
    search_results = vector_store.search(data.query, top_k=3)
    
    if not search_results:
        return {
            "user": current_user, 
            "ai_answer": "No relevant notes found.", 
            "matches": []
        }

    # 2. GENERATE: Use Local Llama/Mistral
    # We pass the query and results to the function in local_llm.py
    ai_answer = get_ai_summary(data.query, search_results)

    # 3. Clean up References for Frontend
    seen_sources = set()
    unique_matches = []
    for match in search_results:
        if match['source'] not in seen_sources:
            unique_matches.append(match)
            seen_sources.add(match['source'])

    return {
        "user": current_user,
        "ai_answer": ai_answer,
        "matches": unique_matches 
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