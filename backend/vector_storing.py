import os
import faiss
import pickle
import numpy as np
from .embeddings import embed_texts 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data") 
INDEX_FILE = os.path.join(DATA_DIR, "faiss_index.bin")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.pkl")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class VectorStore:
    def __init__(self):
        self.dimension = 384 
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = [] 
        
        if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
            print(f"Loading existing index from {INDEX_FILE}...")
            self.index = faiss.read_index(INDEX_FILE)
            with open(METADATA_FILE, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            print("No existing index found. Starting fresh.")

    def add(self, chunks, embeddings, filename):
        if not chunks:
            return
            
        vector_data = np.array(embeddings).astype('float32')
        self.index.add(vector_data)
        
      
        for chunk in chunks:
            self.metadata.append({
                "text": chunk,
                "source": filename
            })
            
        
        print(f"Saving {len(chunks)} chunks to disk...")
        faiss.write_index(self.index, INDEX_FILE)
        with open(METADATA_FILE, "wb") as f:
            pickle.dump(self.metadata, f)
        print("✅ Index Saved Successfully.")

    def search(self, query_text, top_k=3):
    
        print(f"Searching for: {query_text}")
        query_embedding = embed_texts([query_text])[0]
        
        search_vector = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(search_vector, top_k)
        
        results = []
        found_indices = indices[0]
        found_distances = distances[0]

        for i, idx in enumerate(found_indices):
            if idx != -1 and idx < len(self.metadata):
                result = self.metadata[idx]
                score = found_distances[i]
                print(f"Match found: '{result['source']}' (Distance: {score:.4f})")
                results.append(result)
        
        return results

vector_store = VectorStore()