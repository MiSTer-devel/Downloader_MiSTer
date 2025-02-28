FROM arm32v7/python:3.9-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev wget tar python3.9-dev patchelf upx-ucl \
    && python3.9 -m pip install nuitka

WORKDIR /app
COPY downloader /app/downloader/
COPY __main__.py commit.py /app/

ENV CFLAGS="-Os -march=armv7-a"
RUN nuitka --lto=no --follow-imports \
    --remove-output \
    --include-module=_json \
    --python-flag=no_site \
    --python-flag=-OO \
    --jobs=$(nproc) \
    --include-package=downloader __main__.py

RUN upx --best __main__.bin

CMD ["cat", "__main__.bin"]
