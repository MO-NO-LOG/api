FROM ghcr.io/astral-sh/uv:alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN uv sync --frozen --no-cache

EXPOSE 80

ENTRYPOINT ["uv", "run", "main.py"]
CMD ["server", "--host", "0.0.0.0", "--port", "80"]
