FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir discord.py-self aiohttp aiofiles flask flask-cors

COPY discord_listener.py server.py start.py ./

RUN mkdir -p gex_images

EXPOSE 5000

CMD ["python3", "start.py"]
