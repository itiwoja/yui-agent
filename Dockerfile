FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
# Cloud Run が PORT を注入するため shell 形式で展開する
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
