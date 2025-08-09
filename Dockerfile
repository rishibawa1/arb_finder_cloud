FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default config runs mock once. For live mode, ensure config.yaml has use_mock_data: false
CMD ["python", "main.py"]
