FROM python:3.12-slim

WORKDIR /app

COPY backend/general_physician/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/

EXPOSE 8000

CMD ["uvicorn", "backend.cardiology.main:app", "--host", "0.0.0.0", "--port", "8000"]
