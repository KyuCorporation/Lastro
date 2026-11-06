FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"
COPY . .
ENV PYTHONPATH=/srv
CMD ["python", "-m", "lastro_pipeline.cli", "--help"]
