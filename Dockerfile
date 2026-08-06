FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

EXPOSE 8080

# Railway injects $PORT; fall back to 8080 to match the previous deployment.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
