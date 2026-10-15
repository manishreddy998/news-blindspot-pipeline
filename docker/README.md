`no-gcp-key` is an empty placeholder. docker-compose mounts it at /secrets/gcp.json when GCP_KEY_PATH is not set, so DuckDB runs work without a key.
