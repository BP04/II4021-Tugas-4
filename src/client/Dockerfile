FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY data /app/data

ENV PYTHONPATH=/app/src
ENV SERVER_URL=http://server:5000

ENTRYPOINT ["python", "-m", "client.main"]
