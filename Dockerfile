FROM python:3.12-alpine

WORKDIR /app

COPY pyproject.toml README.md ./
COPY nanofinbot ./nanofinbot
RUN pip install --no-cache-dir .

ENV XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data

VOLUME ["/config", "/data"]

ENTRYPOINT ["nfb"]
