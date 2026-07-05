import json
import os
import chromadb
from tqdm import tqdm

DB_DIR = "./chroma_db"
CORPUS_FILE = "financial_corpus.jsonl"
LIMIT = 1000  # We process a subset of 1000 chunks for the local demo to avoid hours of CPU embedding time

def build_vector_db():
    print("Initializing ChromaDB (this may download the embedding model if first run)...")
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(name="sec_filings")

    print(f"Loading up to {LIMIT} documents from {CORPUS_FILE}...")
    documents = []
    metadatas = []
    ids = []

    count = 0
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                # Filter out very short or empty chunks
                text = data.get('text', '').strip()
                if len(text) < 50:
                    continue
                    
                documents.append(text)
                metadatas.append({
                    "company": data.get('company', 'Unknown'), 
                    "year": data.get("year", "Unknown")
                })
                ids.append(f"doc_{count}")
                count += 1
                
                if count >= LIMIT:
                    break
            except Exception as e:
                print(f"Error parsing line: {e}")
                continue

    print(f"Adding {count} documents to Vector Store (this will automatically generate embeddings)...")
    batch_size = 100
    for i in tqdm(range(0, len(documents), batch_size)):
        collection.add(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )

    print("\n✅ Vector database built successfully! Ready for Basic RAG.")

if __name__ == "__main__":
    if not os.path.exists(CORPUS_FILE):
        print(f"Error: {CORPUS_FILE} not found. Please ensure it's in the same directory.")
    else:
        build_vector_db()
