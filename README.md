<div align="center">
  <img src="https://www.tigergraph.com/wp-content/uploads/2023/11/TigerGraph-Logo-Orange-Black.png" alt="TigerGraph Logo" width="300" />
  <h1>🚀 Financial Corporate GraphRAG</h1>
  <p><b>Massive-scale, graph-powered retrieval-augmented generation built for the TigerGraph Hackathon</b></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
  [![TigerGraph](https://img.shields.io/badge/TigerGraph-Cloud-orange.svg)](https://www.tigergraph.com/)
  [![Gemini API](https://img.shields.io/badge/Gemini-2.5%20Flash-green.svg)](https://deepmind.google/technologies/gemini/)
  [![Tokens Processed](https://img.shields.io/badge/Tokens-105M+-red.svg)](#-the-100m-token-benchmark)
</div>

---

## 📖 Table of Contents
- [What is this?](#-what-is-this)
- [The 100M+ Token Benchmark](#-the-100m-token-benchmark)
- [System Architecture](#-system-architecture)
- [Advanced Graph Schema](#-advanced-graph-schema)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Database Setup](#1-database-setup-tigergraph)
  - [2. Backend Setup](#2-backend-setup-fastapi)
  - [3. Frontend Dashboard](#3-frontend-dashboard)
- [The Magic Query (GSQL)](#-the-magic-query-gsql)

---

## 💡 What is this?
Traditional RAG (Retrieval-Augmented Generation) struggles with complex, multi-hop financial queries because it relies on flat vector similarity. 

**This project solves that.** We built an enterprise-grade GraphRAG pipeline that ingests SEC EDGAR 10-K financial filings, extracts intricate corporate relationships (competitors, subsidiaries, risk factors) using **Gemini 2.5 Flash**, and stores them securely in **TigerGraph**. 

The result? An AI that can answer complex questions like: *"What supply chain risks does Apple face, and which of their competitors are exposed to the exact same risks?"*

---

## 🏆 The 100M+ Token Benchmark
To prove real-world viability and satisfy the Hackathon's elite tier requirements, this project was successfully scaled and tested on over 100 million tokens of raw financial data.

<details>
<summary><b>Click here to view official benchmark metrics</b></summary>
<br>

* **Dataset Source:** `winterForestStump/10-K_sec_filings` (HuggingFace)
* **Total Tokens Processed:** `105,001,658` tokens
* **Total Documents:** `8,417` SEC 10-K Filings
* **Tokenizer API:** Official Gemini `countTokens` endpoint via the new `google-genai` SDK.
* *(See `scripts/benchmark_report.txt` for the official verification logs).*

</details>

---

## 🧠 System Architecture

Our data flows through a highly optimized, asynchronous Python pipeline before being served to the end user.

```mermaid
graph TD
    A[("SEC 10-K Filings")] -->|"extract_graph.py"| B("Gemini 2.5 Flash API")
    B -->|"Structured JSON Extraction"| C["vertices.csv and edges.csv"]
    C -->|"schema_and_load.gsql"| D[("TigerGraph Savanna")]
    D -->|"query.gsql Traversal"| E["Deep Context"]
    F["Web Dashboard UI"] -->|"Query"| G["FastAPI Backend"]
    G -->|"Requests Context"| D
    E --> G
    G -->|"Context + Query"| H{"Gemini 2.5 Flash"}
    H -->|"Smart RAG Answer"| F
```

---

## 🕸️ Advanced Graph Schema
We designed a bespoke TigerGraph schema natively tailored for the corporate financial ecosystem.

### **Vertices (Nodes)**
* 🏢 `Company` 
* 👔 `Executive`
* ⚠️ `RiskFactor`
* 🏢 `Subsidiary`

### **Edges (Relationships)**
* 🤝 `EMPLOYS` (Company -> Executive)
* 📉 `FACES_RISK` (Company -> RiskFactor)
* 🔗 `OWNS` (Company -> Subsidiary)
* ⚔️ `COMPETES_WITH` (Company -> Company)

---

## ⚡ Quick Start Guide

### 1. Database Setup (TigerGraph)
1. Open **TigerGraph GraphStudio** (Local Docker or Savanna Cloud).
2. Run the DDL script in `schema_and_load.gsql` to initialize the vertex and edge types.
3. Map the generated `vertices.csv` and `edges.csv` to the schema and run the load job.
4. Install the advanced graph traversal query found in `query.gsql`.

### 2. Backend Setup (FastAPI)
Ensure you have your environment variables set correctly:
```bash
export TG_HOST="https://your-savanna-url.tigergraph.cloud"
export TG_USERNAME="tigergraph"
export TG_PASSWORD="your_password"
export GEMINI_API_KEY="your_api_key"
```

Install dependencies and boot the backend server:
```bash
pip install -r scripts/requirements.txt
python scripts/app.py
```

### 3. Frontend Dashboard
Navigate to `http://localhost:8000` in your browser. Type a financial query into the UI and watch the GraphRAG dynamically pull context from TigerGraph and generate a highly intelligent answer!

---

## 🧙‍♂️ The Magic Query (GSQL)
The secret sauce of this project is our custom GSQL query (`query.gsql`). 
Instead of a basic 1-hop lookup, it utilizes a **Multi-Hop Reverse Traversal Algorithm**. It starts at a target company, finds all of their mapped Risk Factors, and then traverses *backwards* to find every single competitor that shares those exact same risks, delivering unparalleled market insight to the Gemini LLM.

**Raw Dataset:** [Click here to download the 472MB financial_corpus.json](https://1drv.ms/u/c/b35b4e95396fabd0/IQD6XfBvvXImQo5CVNARUo6GAdvPLwGuadlgCY3F_HMEapI?e=xDVOeu)
---
*Built with ❤️ for the TigerGraph Hackathon.*
