# Deploy in local

The OSADEC's database was developped in a docker contnair, in order to deploy it in local it's nessesary to install docker in you device.

## Install Docker Engine on Ubuntu
___
The commands below were extracted from the tutorial of official docker docs ([here](https://docs.docker.com/engine/install/ubuntu/)). You can follow the official tutorial for more explainations.

### **Uninstall old versions**

```
sudo apt-get remove docker docker-engine docker.io containerd runc
```

### **Install using apt repository**

1. Update the apt package index and install packages to allow apt to use a repository over HTTPS:
```
sudo apt-get update

sudo apt-get install ca-certificates curl gnupg
```

2. Add Docker's official GPG key:
```
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

3. Use the following command to set up the repository:
```
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

4. Update the apt package index:
```
sudo apt-get update
```

5. Install Docker Engine, containerd, and Docker Compose.
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```


*In order to manage Docker as a non-root user please continue [this tutorial](https://docs.docker.com/engine/install/linux-postinstall/). We consider you do that, else don't forget to use the sudo command.*


## Deploy the database image
___

Considering you are in the OSADEC folder, to build and run the database execute :
```
docker-compose up -d
```
## Create a virtual environnement
___

In order to securise your python installation we recommand to create a virtual environnement (here we name it *".venv"*, you can name it like you want):

```
python -m venv .venv
```

Activate the environnement (linux):
```
. .venv/bin/activate
```

Install all package that are necessary to use the application:
```
pip install -r requirements.txt
```

Now you can check if the database is correctly running:
```
python ./src/utils/db_tools.py
```