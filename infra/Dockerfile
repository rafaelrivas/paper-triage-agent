FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY agent/ /app/agent/
COPY environment/ /app/environment/

ENV PAPERS_DIR=/papers
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
