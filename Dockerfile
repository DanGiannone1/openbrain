FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev \
    && useradd -m -u 1000 mcp \
    && chown -R mcp:mcp /app

USER mcp

ENV PYTHONPATH=/app/src
ENV PORT=8000
EXPOSE 8000

CMD ["uv", "run", "python", "-m", "openbrain", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
