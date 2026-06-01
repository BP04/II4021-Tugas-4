FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY data /app/data

ENV PYTHONPATH=/app/src

EXPOSE 5000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "5000"]
