FROM python:3.12-alpine

WORKDIR /app

COPY pyproject.toml README.md ./
COPY nanofinbot ./nanofinbot
RUN pip install --no-cache-dir . \
    && adduser -D -H nanofinbot \
    && mkdir -p /config /data \
    && chown -R nanofinbot:nanofinbot /config /data

ENV XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data

USER nanofinbot

VOLUME ["/config", "/data"]

ENTRYPOINT ["nfb"]
CMD ["run"]
