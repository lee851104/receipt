# The demo server in one image (design D14): no GPU, the database and the models in volumes, no private files.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/app.db \
    CATEGORY_MODEL_DIR=/models/category
COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-docker.txt
# Only what the service runs: never the repository root, which holds private data on a developer's computer.
COPY configs ./configs
COPY src ./src
EXPOSE 8000
CMD ["python", "-m", "src.api.container"]
