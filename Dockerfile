FROM ubuntu
FROM python:3.11-slim

RUN groupadd --gid 2000 node && useradd --uid 2000 --gid node --shell /bin/bash --create-home node

USER 2000

WORKDIR /app

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot/bot.py"]