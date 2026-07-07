FROM python:3.10-slim

WORKDIR /code

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Hugging Face Spaces dynamically assign the PORT variable, usually 7860
# Uvicorn will bind to this port
CMD ["sh", "-c", "uvicorn scripts.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
