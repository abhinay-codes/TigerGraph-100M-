import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import uvicorn
import pyTigerGraph as tg
import chromadb
from bert_score import score as bert_score_fn
import warnings
from download_db import download_and_extract_db

warnings.filterwarnings("ignore")

# Trigger DB download if it's missing (for HF Spaces)
download_and_extract_db()

app = FastAPI(title="Financial Corporate GraphRAG")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the current directory to serve index.html and static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Configuration (These should be set in environment variables tomorrow)
TG_HOST = os.environ.get("TG_HOST", "https://your-savanna-url.tigergraph.cloud")
TG_USERNAME = os.environ.get("TG_USERNAME", "tigergraph")
TG_PASSWORD = os.environ.get("TG_PASSWORD", "your_password")
TG_GRAPH = "FinancialGraph"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class QueryRequest(BaseModel):
    query: str
    company: str = None
    tg_host: str = None
    tg_token: str = None
    tg_graph: str = None
    gemini_api_key: str = None

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/basic_rag")
async def execute_basic_rag(req: QueryRequest):
    api_key = req.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key missing")
    os.environ["GEMINI_API_KEY"] = api_key
        
    try:
        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        if not os.path.exists(db_path):
            raise HTTPException(status_code=500, detail="Vector DB not built yet.")
            
        client_db = chromadb.PersistentClient(path=db_path)
        collection = client_db.get_collection(name="sec_filings")
        # In enterprise RAG, 15-20 chunks are typically required to cover enough semantic ground for complex queries.
        results = collection.query(query_texts=[req.query], n_results=15)
        
        chunks = results['documents'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        
        context_parts = ["[Retrieved context - top-3 chunks from vector store]"]
        for i, (chunk, dist, meta) in enumerate(zip(chunks, distances, metadatas)):
            sim = max(0.0, 1.0 - (dist / 2.0))
            context_parts.append(f"Chunk {i+1} (similarity {sim:.2f}) [Company: {meta.get('company')}]: {chunk}")
            
        retrieved_context = "\n\n".join(context_parts)
        
        genai_client = genai.Client()
        prompt = f"You are a helpful assistant. Use the retrieved context below to answer the question accurately. Keep your answer concise (1-2 sentences maximum) so it does not get cut off.\n\nContext:\n{retrieved_context}\n\nQuestion: {req.query}"
        
        response = genai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        
        try:
            in_tokens = response.usage_metadata.prompt_token_count
            out_tokens = response.usage_metadata.candidates_token_count
        except:
            in_tokens = out_tokens = 0
        
        try:
            _, _, F1 = bert_score_fn([response.text], [retrieved_context], lang="en", verbose=False)
            bert_score_f1 = float(F1.item())
        except Exception as e:
            print(f"BERTScore Error: {e}")
            bert_score_f1 = 0.0
        
        return {
            "answer": response.text, 
            "context_used": retrieved_context,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "bert_score": bert_score_f1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag")
async def execute_graph_rag(req: QueryRequest):
    api_key = req.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key missing")
    os.environ["GEMINI_API_KEY"] = api_key
        
    try:
        # Use UI provided values or fallback to env
        host = req.tg_host or TG_HOST
        token = req.tg_token or os.environ.get("TG_TOKEN", "")
        graph = req.tg_graph or TG_GRAPH
        
        # Step 0: Extract the true company name using an Agentic LLM call
        client = genai.Client()
        extracted_company = req.company
        if len(req.query.split()) > 3: # If it's a sentence instead of just a name
            try:
                extraction_prompt = f"Extract ONLY the exact primary company name from this query. Preserve exact spelling and punctuation (e.g. if it says 'INC.', keep the period). Do not include any other words. Query: '{req.query}'"
                extract_resp = client.models.generate_content(model='gemini-2.5-flash', contents=extraction_prompt)
                extracted_company = extract_resp.text.strip().strip(",?\"'")
                print(f"Agent extracted company name: {extracted_company}")
            except Exception as e:
                print(f"Extraction failed: {e}")
                pass
        
        # Step 1: Connect to TigerGraph using the Savanna API Key
        conn = tg.TigerGraphConnection(host=host, graphname=graph, apiToken=token)
        
        # Step 2: Extract Graph Context based on user query
        try:
            # Pass the EXACT company name to TigerGraph to perfectly traverse the edges (using 'question' param to match installed query)
            graph_context_raw = conn.runInstalledQuery("get_company_context", {"question": extracted_company})
            graph_context_str = json.dumps(graph_context_raw, indent=2)
        except Exception as query_err:
            if "not found" in str(query_err).lower() or "404" in str(query_err):
                return {"answer": "Error: Your query is not installed yet! Go to GraphStudio, click the 'Up Arrow' button next to Queries to install it.", "context_used": ""}
            raise query_err
        
        # (Simulation is now disabled since the database is live)
        # graph_context = f"Company: {req.company} has OWNS relationships with 3 Subsidiaries. FACES_RISK from Supply Chain Disruptions. COMPETES_WITH 5 market leaders."

        # Step 3: Pass Graph Context + Query to Gemini
        client = genai.Client()
        prompt = f"""
        You are an elite Financial AI Assistant running on top of TigerGraph.
        Answer the user's query using the verified Graph Database Context below.
        
        User Query: {req.query}
        
        TigerGraph Context:
        {graph_context_str}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        try:
            in_tokens = response.usage_metadata.prompt_token_count
            out_tokens = response.usage_metadata.candidates_token_count
        except:
            in_tokens = out_tokens = 0
            
        try:
            _, _, F1 = bert_score_fn([response.text], [graph_context_str], lang="en", verbose=False)
            bert_score_f1 = float(F1.item())
        except Exception as e:
            print(f"BERTScore Error: {e}")
            bert_score_f1 = 0.0
            
        return {
            "answer": response.text, 
            "context_used": graph_context_str,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "bert_score": bert_score_f1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting GraphRAG Backend on port 8000...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
