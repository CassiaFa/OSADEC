<!-- insert logo below-->
<p align="center">
  <picture>
  <source media="(prefers-color-scheme: dark)" srcset="./app/static/images/logo_white.png">
  <img alt="OSADEC logo" src="./app/static/images/logo.png" width="250">
  </picture>
</p>

___

**O**cean **S**ound **A**ssistant for **DE**tection and **C**lassification (OSADEC) is a open-source project to help in labbelling marine mammal calls in records.

## Get started

Clone the GitHub repository in your computer, and open a terminal in the folder.

Execute this  commande to initialize the aplication (this may take several minutes) :
```
sh init.sh
```

## Check manualy the database validity

If you want to check the database validity, you must first access the application's docker terminal : 

```
docker exec -it osadec bash
```

And execute this command :

```
python src/utils/db_tools.py
```

You should normally get :

```
Test database connexion ... ok ✅
Checking data ... ok ✅
The database is connected ✅
```

You can now exit the docker's terminal with 
```
exit
```