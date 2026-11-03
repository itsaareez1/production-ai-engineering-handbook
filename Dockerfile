# Listing 44.1 (part 1 of 2). Local environment for Atlas:
# container build. Chapter 44, Environments and Deployment.
#
# Reviewed for correctness (build order, user, health check) and
# validated for structure; build it with:
#   docker compose build && docker compose up
# This file is an exact copy of ./Dockerfile at the repository root,
# which is the one Compose builds.

FROM python:3.12-slim
WORKDIR /app
# Install third-party dependencies first so this layer is cached
# until requirements.txt changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Copy the source, then install the local package (source must exist
# first).
COPY pyproject.toml ./
COPY atlas ./atlas
RUN pip install --no-cache-dir --no-deps .
# Run as an unprivileged user; the image contains no secrets.
RUN useradd --uid 1000 --no-create-home atlas
USER atlas
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; \
  sys.exit(0 if urllib.request.urlopen( \
  'http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "atlas.api:app", "--host", "0.0.0.0", "--port", "8000"]
