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

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/rag")
async def execute_graph_rag(req: QueryRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API Key missing")
        
    try:
        # Use UI provided values or fallback to env
        host = req.tg_host or TG_HOST
        token = req.tg_token or "22s_qfLJ_rekK2RnwQJSdRDGXlLHZXibJyZ7FvB0"
        graph = req.tg_graph or TG_GRAPH
        
        # Step 0: Extract the true company name using an Agentic LLM call
        client = genai.Client()
        extracted_company = req.company
        if len(req.query.split()) > 3: # If it's a sentence instead of just a name
            try:
                extraction_prompt = f"Extract ONLY the primary company name from this query. Do not include any other words. Query: '{req.query}'"
                extract_resp = client.models.generate_content(model='gemini-2.5-flash', contents=extraction_prompt)
                extracted_company = extract_resp.text.strip()
                print(f"Agent extracted company name: {extracted_company}")
            except Exception as e:
                print(f"Extraction failed: {e}")
                pass
        
        # Step 1: Connect to TigerGraph using the Savanna API Key
        conn = tg.TigerGraphConnection(host=host, graphname=graph, apiToken=token)
        
        # Step 2: Extract Graph Context based on user query
        try:
            graph_context = conn.runInstalledQuery("get_company_context", {"company_name": extracted_company})
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
        {graph_context}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return {"answer": response.text, "context_used": graph_context}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting GraphRAG Backend on port 8000...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
