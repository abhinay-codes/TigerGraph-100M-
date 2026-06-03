import os
import json
import csv
import time
import asyncio
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Define the structured output schema for Gemini
class Vertex(BaseModel):
    id: str = Field(description="The unique identifier or name of the entity.")
    type: str = Field(description="Must be one of: Company, Executive, RiskFactor, Subsidiary")

class Edge(BaseModel):
    source: str = Field(description="The id of the source vertex.")
    target: str = Field(description="The id of the target vertex.")
    type: str = Field(description="Must be one of: EMPLOYS, FACES_RISK, OWNS, COMPETES_WITH")

class GraphExtraction(BaseModel):
    vertices: list[Vertex]
    edges: list[Edge]

# Setup Gemini Client (Async)
if "GEMINI_API_KEY" not in os.environ:
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    exit(1)

client = genai.Client()

async def process_document(doc, sem):
    """
    Process a single document through Gemini 1.5 Flash to extract graph entities.
    Uses a semaphore to limit concurrent API calls and prevent 429 errors.
    """
    async with sem:
        text = doc.get("text", "")
        company = doc.get("company", "Unknown")
        
        # If the text is too large, we truncate it for extraction to save costs 
        # (For 100M tokens, we might process full texts, but let's limit to 15k chars per doc for the demo)
        text_chunk = text[:15000] 
        
        prompt = f"""
        Analyze the following SEC 10-K filing excerpt for {company}.
        Extract all relevant entities (Company, Executive, RiskFactor, Subsidiary) and their relationships (EMPLOYS, FACES_RISK, OWNS, COMPETES_WITH).
        
        Text excerpt:
        {text_chunk}
        """
        
        try:
            # Note: We use the async client `client.aio`
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GraphExtraction,
                    temperature=0.1
                )
            )
            
            # The response text will be a JSON string conforming to the GraphExtraction schema
            return json.loads(response.text)
            
        except Exception as e:
            print(f"Error extracting graph for {company}: {e}")
            return None

async def main():
    input_file = "financial_corpus.jsonl"
    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found. Run count_tokens.py first.")
        return

    # Prepare CSV writers
    vertices_file = open("vertices.csv", "w", newline="", encoding="utf-8")
    edges_file = open("edges.csv", "w", newline="", encoding="utf-8")
    
    v_writer = csv.writer(vertices_file)
    e_writer = csv.writer(edges_file)
    
    # Write headers
    v_writer.writerow(["v_id", "v_type"])
    e_writer.writerow(["source", "target", "e_type"])
    
    # Read corpus
    print("Loading corpus...")
    docs = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            docs.append(json.loads(line))
            if len(docs) >= 50:
                break
            
    print(f"Loaded {len(docs)} documents for extraction.")
    
    # We use a Semaphore to allow max 5 concurrent requests to Gemini to respect standard tier rate limits
    sem = asyncio.Semaphore(5)
    
    # Batch processing
    BATCH_SIZE = 50
    total_vertices = 0
    total_edges = 0
    
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1} ({len(batch)} docs)...")
        
        tasks = [process_document(doc, sem) for doc in batch]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if not result:
                continue
                
            # Write vertices
            for v in result.get("vertices", []):
                # Basic cleaning
                v_id = v.get("id", "").strip().replace("\n", " ")
                v_type = v.get("type", "Unknown")
                if v_id:
                    v_writer.writerow([v_id, v_type])
                    total_vertices += 1
                    
            # Write edges
            for e in result.get("edges", []):
                source = e.get("source", "").strip().replace("\n", " ")
                target = e.get("target", "").strip().replace("\n", " ")
                e_type = e.get("type", "Unknown")
                if source and target:
                    e_writer.writerow([source, target, e_type])
                    total_edges += 1
                    
        # Flush to disk periodically
        vertices_file.flush()
        edges_file.flush()
        
        # Sleep slightly between batches to cool down rate limits
        await asyncio.sleep(2)
        
    vertices_file.close()
    edges_file.close()
    
    print("\n--- GRAPH EXTRACTION COMPLETE ---")
    print(f"Total Vertices Extracted: {total_vertices:,}")
    print(f"Total Edges Extracted: {total_edges:,}")
    print("Saved to vertices.csv and edges.csv")
    print("Ready for TigerGraph Bulk Loading!")

if __name__ == "__main__":
    asyncio.run(main())
