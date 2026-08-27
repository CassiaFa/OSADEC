# syntax=docker/dockerfile:1

FROM python:3.11

WORKDIR /osadec

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y

RUN mkdir ./bucket ./tmp

# Pin the build tooling: mmcv-full 1.7.1 builds from source (no wheel for py3.11)
# and its setup.py imports pkg_resources, which recent setuptools no longer expose.
RUN pip install --upgrade "pip<24.1" "setuptools<70" wheel

# CPU build of torch/vision/audio (must be installed before mmcv-full is compiled)
RUN pip install "numpy<2" && \
    pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt requirements.txt

# Compile mmcv-full against the already-installed torch, without build isolation
# so it can see torch/numpy/setuptools from this environment.
RUN pip install --no-build-isolation "mmcv-full==1.7.1"

RUN pip install -r requirements.txt

COPY app.py app.py

COPY src src

COPY static static

COPY templates templates

COPY .env .env

EXPOSE 5000

# Start via app.py so socketio.run() drives the server (websocket / progress bar).
# `flask run` would ignore SocketIO and listen on the wrong port.
CMD ["python", "app.py"]
