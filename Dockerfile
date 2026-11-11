FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pulso ./pulso
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "pulso.api:app", "--host", "0.0.0.0", "--port", "8000"]
