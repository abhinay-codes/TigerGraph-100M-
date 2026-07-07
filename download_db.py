import os
import zipfile
import urllib.request

DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
# You must set DB_ZIP_URL as an environment variable in Hugging Face!
ZIP_URL = os.environ.get("DB_ZIP_URL", "")

def download_and_extract_db():
    if os.path.exists(DB_DIR):
        print("ChromaDB already exists locally. Skipping download.")
        return
        
    if not ZIP_URL:
        print("Warning: DB_ZIP_URL is not set. Cannot download Vector DB.")
        return

    print(f"Downloading ChromaDB ZIP from {ZIP_URL}...")
    zip_path = "chroma_db.zip"
    
    try:
        urllib.request.urlretrieve(ZIP_URL, zip_path)
        print("Download complete. Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.dirname(__file__) or ".")
        print("Extraction complete. ChromaDB is ready.")
        os.remove(zip_path)
    except Exception as e:
        print(f"Failed to download or extract DB: {e}")

if __name__ == "__main__":
    download_and_extract_db()
