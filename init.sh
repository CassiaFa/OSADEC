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
    echo "UPLOAD_FOLDER=./bucket" >> "./app/.env"

    echo "Env file created"
fi

docker-compose up -d

address=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' osadec)

echo "To access the app, visit http://$address:5000"