FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY src/ .

EXPOSE 8000

CMD ["hypercorn", "scheduled_payments.app:app", "--bind", "0.0.0.0:8000"]