FROM python:3.12-alpine

RUN apk add --no-cache git

WORKDIR /app

RUN git clone https://github.com/arinadi/nanoFinBot . \
    && pip install --no-cache-dir -e . \
    && adduser -D -H nanofinbot \
    && mkdir -p /config /data \
    && chown -R nanofinbot:nanofinbot /config /data /app

ENV XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data

USER nanofinbot

VOLUME ["/config", "/data"]

ENTRYPOINT ["nfb"]
CMD ["run"]
