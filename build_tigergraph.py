import os
import json
import pyTigerGraph as tg
import pandas as pd
from dotenv import load_dotenv

# Load variables from the .env file in the parent directory
load_dotenv("../.env")

TG_HOST = os.environ.get("TG_HOST")
TG_SECRET = os.environ.get("TG_SECRET")
TG_GRAPH = os.environ.get("TG_GRAPH", "FinancialGraph")

print(f"Connecting to TigerGraph at {TG_HOST}...")

# Initialize connection (graphname="" for global schema changes)
conn = tg.TigerGraphConnection(host=TG_HOST, gsqlSecret=TG_SECRET)
token_response = conn.getToken(TG_SECRET)
token = token_response[0]
print("Authenticated successfully. Token generated.")

print("\n[1/3] Building Global Schema (this may take a minute)...")
schema_gsql = f"""
CREATE VERTEX Company (PRIMARY_ID id STRING, name STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE VERTEX Document (PRIMARY_ID id STRING, text_content STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE DIRECTED EDGE HAS_DOCUMENT (FROM Company, TO Document)

CREATE GRAPH {TG_GRAPH} (Company, Document, HAS_DOCUMENT)
"""

try:
    print(conn.gsql(schema_gsql))
except Exception as e:
    print("Schema may already exist. Proceeding...")

# Re-connect specifically to the graph
conn.graphname = TG_GRAPH

print("\n[2/3] Preparing to load data from financial_corpus.jsonl...")
companies_data = []
docs_data = []
edges_data = []

with open("financial_corpus.jsonl", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if not line.strip(): continue
        data = json.loads(line)
        company = data.get("company", "Unknown").strip()
        text = data.get("text", "")
        doc_id = f"doc_{i}"
        
        companies_data.append({"id": company, "name": company})
        docs_data.append({"id": doc_id, "text_content": text})
        edges_data.append({"source": company, "target": doc_id})

print(f"Loaded {len(docs_data)} documents from JSONL.")

# Deduplicate companies
companies_df = pd.DataFrame(companies_data).drop_duplicates(subset=["id"])
docs_df = pd.DataFrame(docs_data)
edges_df = pd.DataFrame(edges_data)

print(f"Upserting {len(companies_df)} Companies to TigerGraph...")
for i in range(0, len(companies_df), 1000):
    conn.upsertVertexDataFrame(companies_df.iloc[i:i+1000], vertexType="Company", v_id="id")

print(f"Upserting {len(docs_df)} Documents to TigerGraph... (This might take a few minutes)")
for i in range(0, len(docs_df), 500): # Smaller chunks for documents because of large text
    conn.upsertVertexDataFrame(docs_df.iloc[i:i+500], vertexType="Document", v_id="id")

print(f"Upserting {len(edges_df)} Relationships (Edges) to TigerGraph...")
edges_list = [(row["source"], row["target"]) for _, row in edges_df.iterrows()]
for i in range(0, len(edges_list), 1000):
    chunk = edges_list[i:i+1000]
    conn.upsertEdges(sourceVertexType="Company", edgeType="HAS_DOCUMENT", targetVertexType="Document", edges=chunk)
    
print("Data loaded successfully!")

print("\n[3/3] Installing GSQL Query 'get_company_context'...")
query_gsql = f"""
USE GRAPH {TG_GRAPH}
CREATE OR REPLACE QUERY get_company_context(STRING question) FOR GRAPH {TG_GRAPH} {{
  SetAccum<STRING> @@context;
  
  # Very simple keyword search across companies
  Seed = {{Company.*}};
  
  TargetCompanies = SELECT s FROM Seed:s 
                    WHERE question LIKE ("%" + s.name + "%");
                    
  Docs = SELECT d FROM TargetCompanies:s -(HAS_DOCUMENT:e)- Document:d
         ACCUM @@context += d.text_content;
         
  PRINT @@context as results;
}}
INSTALL QUERY get_company_context
"""
print("Running GSQL Query installation (this usually takes 2-3 minutes)...")
try:
    print(conn.gsql(query_gsql))
except Exception as e:
    print(f"Query installation error: {e}")

print("\n" + "="*50)
print("ALL DONE! TigerGraph is now fully operational.")
print("="*50)
print("IMPORTANT: Copy this Bearer Token to use in your Dashboard:")
print(f"{token}")
print("="*50)
