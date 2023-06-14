# syntax=docker/dockerfile:1

FROM python:3.11

WORKDIR /osadec

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir ./bucket ./tmp

RUN pip install --upgrade pip

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY app.py app.py

COPY src src

COPY static static

COPY templates templates

COPY .env .env

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]