#!/bin/sh


if [ -d "./app/bucket" ]; then
    echo "Bucket already exists"
else
    mkdir "./app/bucket"
    echo "Bucket created"
fi

if [ -d "./app/tmp" ]; then
    echo "Tmp folder already exists"
else
    mkdir "./app/tmp"
    echo "Tmp folder created"
fi

if [ -f "./app/.env" ]; then
    
    if grep -q "ENCRYPT_KEY" ./app/.env; then
        echo "Key already exists"
    else
        e_key=`tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_{|}~' </dev/urandom | head -c 20`
        echo "ENCRYPT_KEY=${e_key}" >> ./app/.env
        echo "Key created"
    fi

    if grep -q "ENCODING" ./app/.env; then
        echo "Encoding already exists"
    else
        echo "ENCODING=latin-1" >> ./app/.env
        echo "Encoding created"
    fi

    if grep -q "SOCKET_KEY" ./app/.env; then
        echo "Socket Key already exists"
    else
        s_key=`tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_{|}~' </dev/urandom | head -c 10`
        echo "SOCKET_KEY=${s_key}" >> ./app/.env
        echo "Socket key created"
    fi

    if grep -q "UPLOAD_FOLDER" ./app/.env; then
        echo "Upload folder variable already exists"
    else
        echo "UPLOAD_FOLDER=./bucket" >> ./app/.env
        echo "Upload folder created"
    fi

else
    touch "./app/.env"
    e_key=`tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_{|}~' </dev/urandom | head -c 20`
    echo "ENCRYPT_KEY=${e_key}" >> "./app/.env"
    echo "ENCODING=latin-1" >> "./app/.env"
    s_key=`tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_{|}~' </dev/urandom | head -c 10`
    echo "SOCKET_KEY=${s_key}" >> ./app/.env
    echo "UPLOAD_FOLDER=./bucket" >> "./app/.env"

    echo "Env file created"
fi


MODEL_FILE="./app/models/latest_lowfreq_faster-rcnn.pth"
MODEL_ID="1j5GnQtjiScio7wB8TSN31St-v6pgmPOo"

# Only download the model weights if they are missing. A previous version of this
# script re-ran the download every time and could overwrite a valid file with a
# Google Drive error page, then abort the whole script.
if [ -s "$MODEL_FILE" ]; then
    echo "Model weights already present"
else
    echo "Downloading model weights ..."
    wget --no-check-certificate \
        "https://drive.usercontent.google.com/download?id=${MODEL_ID}&export=download&confirm=t" \
        -O "$MODEL_FILE" \
        || echo "WARNING: model download failed. Put the .pth file at $MODEL_FILE manually."
fi

if docker compose version >/dev/null 2>&1; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo "To access the app, visit http://localhost:5000"