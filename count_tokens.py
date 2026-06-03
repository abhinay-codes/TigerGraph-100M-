import os
import json
import time
from datasets import load_dataset
from google import genai

def main():
    if "GEMINI_API_KEY" not in os.environ:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Please set it before running this script.")
        return

    client = genai.Client()
    
    TARGET_TOKENS = 105_000_000
    current_tokens = 0
    document_count = 0
    
    output_file = "financial_corpus.jsonl"
    
    print(f"Starting token counting using Gemini 'countTokens' API...")
    print(f"Targeting {TARGET_TOKENS:,} tokens.")
    
    # Resume Logic
    if os.path.exists(output_file):
        print(f"Found existing {output_file}. Resuming...")
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                current_tokens += data.get("tokens", 0)
                document_count += 1
        print(f"Resumed from {document_count} documents with {current_tokens:,} tokens.")
    
    if current_tokens >= TARGET_TOKENS:
        print("Target already reached!")
        return

    start_time = time.time()
    splits = ['001', '002', '003', '004', '005']
    
    docs_to_skip = document_count
    
    with open(output_file, 'a', encoding='utf-8') as f:
        for split_id in splits:
            if current_tokens >= TARGET_TOKENS:
                break
                
            print(f"Loading split {split_id}...")
            try:
                dataset = load_dataset('winterForestStump/10-K_sec_filings', split=split_id, streaming=True)
            except Exception as e:
                print(f"Error loading dataset split {split_id}: {e}")
                continue
                
            for row in dataset:
                # Fast forward
                if docs_to_skip > 0:
                    docs_to_skip -= 1
                    continue
                    
                if current_tokens >= TARGET_TOKENS:
                    break
                    
                company = row.get("company_name", "Unknown Company")
                year = str(row.get("filing_date", "Unknown Year"))[:4] if row.get("filing_date") else "Unknown Year"
                
                text_sections = []
                if row.get("Business"): text_sections.append(str(row["Business"]))
                if row.get("Risk Factors"): text_sections.append(str(row["Risk Factors"]))
                
                for k, v in row.items():
                    if "Management" in k and "Discussion" in k and v:
                        text_sections.append(str(v))
                
                combined_text = "\n\n".join(text_sections).strip()
                
                if not combined_text:
                    continue
                    
                try:
                    response = client.models.count_tokens(
                        model='gemini-2.5-flash',
                        contents=combined_text
                    )
                    tokens = response.total_tokens
                    
                    corpus_item = {
                        "company": company,
                        "year": year,
                        "text": combined_text,
                        "tokens": tokens
                    }
                    f.write(json.dumps(corpus_item) + "\n")
                    f.flush()
                    
                    current_tokens += tokens
                    document_count += 1
                    
                    if document_count % 10 == 0:
                        print(f"Processed {document_count} documents. Total Tokens: {current_tokens:,}")
                        
                except Exception as e:
                    print(f"API Error counting tokens for {company}: {e}")
                    time.sleep(1) # Backoff

    elapsed = time.time() - start_time
    
    print("\n--- TOKEN COUNTING COMPLETE ---")
    print(f"Total Tokens: {current_tokens:,}")
    print(f"Total Documents: {document_count}")
    print(f"Time Taken for this run: {elapsed:.2f} seconds")
    print(f"Corpus saved to: {output_file}")
    
    report = f"""TigerGraph Hackathon Benchmark Report
-----------------------------------
Dataset: winterForestStump/10-K_sec_filings (SEC 10-K Filings)
Total Tokens: {current_tokens:,}
Total Documents: {document_count}

Tokenizer Documentation:
As per the hackathon requirements, the dataset size was measured using the official Gemini API (`countTokens` endpoint) via the `google-genai` Python SDK. 
The underlying tokenizer utilized by the API is the official Gemini SentencePiece tokenizer, ensuring exact alignment with the model's actual token usage for processing.
"""
    with open("benchmark_report.txt", "w") as f:
        f.write(report)
        
    print("benchmark_report.txt generated successfully!")

if __name__ == "__main__":
    main()
