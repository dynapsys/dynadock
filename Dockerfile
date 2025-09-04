# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
#  DynaDock – Container image for running the CLI inside Docker / CI pipelines
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/yourusername/dynadock" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="DynaDock" \
      org.opencontainers.image.description="Dynamic Docker Compose orchestrator with automatic port allocation and TLS"

# ------------------------------------------------------------
# Install lightweight build tools and the *uv* package manager
# ------------------------------------------------------------
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends curl ca-certificates gcc git \
    && rm -rf /var/lib/apt/lists/*

# Install *uv* (fast drop-in replacement for pip / virtualenv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.cargo/bin/uv /usr/local/bin/uv
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy immutable project metadata first to leverage Docker cache
COPY pyproject.toml README.md ./

# Install runtime dependencies
RUN uv pip install --no-cache-dir --system --require-hashes -e .

# Copy project source
COPY src/ src/

ENTRYPOINT ["dynadock"]
CMD ["--help"]
