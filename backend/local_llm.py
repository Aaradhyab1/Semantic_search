import os
from ctransformers import AutoModelForCausalLM

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(CURRENT_DIR, "models", "mistral-7b-instruct-v0.1.Q4_K_M.gguf")

def load_model():
    print(f"DEBUG: Loading Local Model from {MODEL_PATH}...")
    if not os.path.exists(MODEL_PATH):
        print(f"CRITICAL ERROR: Model not found at {MODEL_PATH}")
        return None

    try:
        llm = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            model_type="mistral",
            gpu_layers=0, 
            context_length=2048
        )
        print("✅ Local Model Loaded Successfully!")
        return llm
    except Exception as e:
        print(f"FAILED to load model: {e}")
        return None

llm = load_model()

def get_ai_summary(query: str, search_results: list) -> str:
    if not llm:
        return "Error: Local AI model is not loaded."

    context_parts = []
    for i, res in enumerate(search_results):
        # Limit chunk size to fit in local memory context
        clean_chunk = res['text'].replace("\n", " ").strip()[:1000]
        context_parts.append(f"[Source {i+1}]: {clean_chunk}")

    context_text = "\n\n".join(context_parts)

    prompt = f"""[INST] You are a helpful Professor. Answer the Student's Question using ONLY the Context below.
    
    RULES:
    1. Fix broken words (e.g., read "greedyield" as "greedy yield").
    2. Answer in short, clear bullet points.
    3. If the answer is not in the Context, say "I don't know".
    
    Context:
    {context_text}

    Student Question: {query}
    [/INST]"""

    print("Generating answer locally...")
    response = llm(prompt, max_new_tokens=512, temperature=0.2)
    
    return response