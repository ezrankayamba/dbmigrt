FROM python:3.11-slim

# pymssql needs libssl at runtime; its aarch64 wheel bundles FreeTDS.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "click>=8.1" "SQLAlchemy>=2.0" "PyMySQL>=1.1" "pymssql>=2.2"

COPY runner/run_test.py /run_test.py
WORKDIR /work
ENTRYPOINT ["python", "/run_test.py"]
