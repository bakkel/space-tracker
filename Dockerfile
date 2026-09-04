FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir sgp4

COPY server.py .
COPY static/ static/

ENV PYTHONUNBUFFERED=1

EXPOSE 8082

CMD ["python3", "server.py"]
