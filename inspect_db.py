import chromadb
import sys

def search_db(query):
    # Connect to the local database
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="sec_filings")
    
    print(f"\n--- Searching Vector DB for: '{query}' ---")
    print("-" * 50)
    
    # Perform a similarity search
    results = collection.query(
        query_texts=[query],
        n_results=2 # Get top 2 results
    )
    
    chunks = results['documents'][0]
    distances = results['distances'][0]
    
    for i, (chunk, dist) in enumerate(zip(chunks, distances)):
        # Convert L2 distance to a simple similarity percentage
        similarity = max(0.0, (1.0 - (dist / 2.0))) * 100
        print(f"\nResult {i+1} (Similarity: {similarity:.1f}%):")
        print(f"{chunk[:300]}...") # Print first 300 characters
        
    print("\n" + "-" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_db(" ".join(sys.argv[1:]))
    else:
        # Default test query
        search_db("What are the main supply chain risks and disruptions?")
