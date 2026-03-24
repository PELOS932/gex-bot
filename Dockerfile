FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir discord.py-self aiohttp aiofiles flask flask-cors

COPY discord_listener.py server.py start.sh ./
RUN chmod +x start.sh

RUN mkdir -p gex_images

EXPOSE 5000

CMD ["./start.sh"]
