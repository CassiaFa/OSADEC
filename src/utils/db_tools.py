import os
from dotenv import load_dotenv
import mysql.connector as mysqlpy


class Encryptor():

    load_dotenv()
    __key = os.getenv('ENCRYPT_KEY')
    __encoding = os.getenv('ENCODING')
    
    @classmethod
    def encrypt(cls, txt:str, cursor):
        querry = "SELECT AES_ENCRYPT(%s, %s);"
        param = (txt, cls.__key)
        cursor.execute(querry, param)
        return list(cursor.fetchone().values())[0].decode(cls.__encoding)

    @classmethod
    def decrypt(cls, pwd, cursor):
        querry = "SELECT AES_DECRYPT(%s, %s);"
        param = (bytearray(pwd, cls.__encoding), cls.__key)
        cursor.execute(querry, param)
        return list(cursor.fetchone().values())[0].decode(cls.__encoding)
    

class Database():

    __USER = 'root'
    __PWD = 'godofdb29'
    __HOST = 'db'
    __PORT = '3306'
    __DB = 'DATA' #'USER_DB'
    __cursor = None
    __secure = Encryptor()

    @classmethod
    def open_connexion(cls):
        if not cls.__cursor:
            cls.__bdd = mysqlpy.connect(
                                        user = cls.__USER,
                                        password = cls.__PWD,
                                        host = cls.__HOST,
                                        port = cls.__PORT,
                                        database = cls.__DB
                                        )

            cls.__cursor = cls.__bdd.cursor(dictionary=True)
    
    @classmethod
    def close_connexion(cls):
        cls.__cursor.close()
        cls.__bdd.close()
        cls.__cursor = None
    
    @classmethod
    def add_user(cls, gender, first_name, last_name, username, email, password):
        password = cls.__secure.encrypt(password, cls.__cursor)
        querry = "INSERT INTO users (gender, first_name, last_name, username, email, password) VALUES (%s, %s, %s, %s, %s, %s);"
        param = (gender, first_name, last_name, username, email, password)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()

    @classmethod
    def check_user(cls, username, password):
        querry = f"SELECT * FROM users WHERE username='{username}';"
        cls.__cursor.execute(querry)

        user = cls.__cursor.fetchone()

        if password == cls.__secure.decrypt(user['password'], cls.__cursor):
            return user
        else:
            return False

    
    @classmethod
    def get_files(cls, id_file=None, time_min=None, time_max=None, name=None):

        if id_file:
            if time_min and time_max:
                querry = f"SELECT name, date, duration, path, fs FROM FILES WHERE id_file={id_file} AND date>='{time_min}' AND date<='{time_max}';"
            elif time_min:
                querry = f"SELECT name, date, duration, path, fs FROM FILES WHERE id_file={id_file} AND date>='{time_min}';"
            elif time_max:
                querry = f"SELECT name, date, duration, path, fs FROM FILES WHERE id_file={id_file} AND date<='{time_max}';"
            else:
                querry = f"SELECT name, date, duration, path, fs FROM FILES WHERE id_file={id_file};"
        elif name:
            if time_min and time_max:
                querry = f"SELECT id_file, date, duration, path, fs FROM FILES WHERE name='{name}' AND date>='{time_min}' AND date<='{time_max}';"
            elif time_min:
                querry = f"SELECT id_file, date, duration, path, fs FROM FILES WHERE name='{name}' AND date>='{time_min}';"
            elif time_max:
                querry = f"SELECT id_file, date, duration, path, fs FROM FILES WHERE name='{name}' AND date<='{time_max}';"
            else:
                querry = f"SELECT id_file, date, duration, path, fs FROM FILES WHERE name='{name}';"
        else:
            if time_min and time_max:
                querry = f"SELECT id_file, name, date, duration, path, fs FROM FILES WHERE date>='{time_min}' AND date<='{time_max}';"
            elif time_min:
                querry = f"SELECT id_file, name, date, duration, path, fs FROM FILES WHERE date>='{time_min}';"
            elif time_max:
                querry = f"SELECT id_file, name, date, duration, path, fs FROM FILES WHERE date<='{time_max}';"
            else:
                querry = "SELECT id_file, name, date, duration, path, fs FROM FILES;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()
        
        # return first element if there is only one, otherwise return list
        if len(result) == 1:
            return result[0]
        else:
            return result

    
    @classmethod
    def get_detections(cls, id_file=None, time_min=None, time_max=None):

        if id_file:
            if time_min and time_max:
                querry = f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file} AND START>='{time_min}' AND STOP<='{time_max}';"
            elif time_min:
                querry = f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file} AND START>='{time_min}';"
            elif time_max:
                querry = f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file} AND STOP<='{time_max}';"
            else:
                querry = f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file};"
        else:
            querry = "SELECT start, stop, id_file, id_species FROM DETECTIONS;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
    
    @classmethod
    def get_projects(cls, name=None, depth=None, lat=None, long=None):
        if name:
            querry = f"SELECT * FROM PROJECTS WHERE name='{name}';"
        elif depth:
            querry = f"SELECT * FROM PROJECTS WHERE depth={depth};"
        elif lat:
            querry = f"SELECT * FROM PROJECTS WHERE latitude={lat};"
        elif long:
            querry = f"SELECT * FROM PROJECTS WHERE longitude={long};"
        else:
            querry = "SELECT * FROM PROJECTS;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        # return first element if there is only one, otherwise return list
        if len(result) == 1:
            return result[0]
        else:
            return result

    @classmethod
    def add_project(cls, name, depth, lat, long):
        querry = "INSERT INTO PROJECTS (name, depth, latitude, longitude) VALUES (%s, %s, %s, %s);"
        param = (name, depth, lat, long)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()

    @classmethod
    def check_database(cls):
        querry = "SHOW TABLES;"
        cls.__cursor.execute(querry)
        
        if not cls.__cursor.fetchall():
            return print("No tables in database")
        
        querry = "SELECT * FROM DETECTIONS;"
        cls.__cursor.execute(querry)
        
        if not cls.__cursor.fetchall():
            return print("Tables are empty")

        return True


    
    @classmethod
    def get_categories(cls, id_species=None, english_name=None, latin_name=None):
        
        if id_species:
            querry = f"SELECT id_species, english_name FROM SPECIES WHERE id_species={id_species};"
        elif english_name:
            querry = f"SELECT id_species, english_name FROM SPECIES WHERE english_name='{english_name}';"
        elif latin_name:
            querry = f"SELECT id_species, english_name FROM SPECIES WHERE latin_name='{latin_name}';"
        else:
            querry = "SELECT id_species, english_name FROM SPECIES"

        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        if len(result) == 1:
            return result[0]
        else:
            return result
    

    @classmethod
    def add_file(cls, name, date, duration, fs, path, id_project):
        querry = "INSERT INTO FILES (name, date, duration, fs, path, id_project) VALUES (%s, %s, %s, %s, %s, %s);"
        param = (name, date, duration, fs, path, id_project)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()


    @classmethod
    def add_detection(cls, start, stop, confidence, id_species, id_file):
        querry = "INSERT INTO DETECTIONS (start, stop, confidence ,id_file, id_species) VALUES (%s, %s, %s, %s, %s);"
        param = (start, stop, float(confidence), id_file, id_species)
        cls.__cursor.execute(querry, param)        
        cls.__bdd.commit()
    
   
        

def main():

    print("Test database connexion ... ", end="\r")
    try:
        Database.open_connexion()
        print("Test database connexion ... ok ✅")
        print("Checking data ...", end="\r")
    except Exception as e:
        print("Test database connexion ... no ❌")
        print("The database is not connected ❌")
        print(e)
    
    
    if Database.check_database() is True:
        print("Checking data ... ok ✅")
        print("The database is connected ✅")
    else:
        print("Checking data ... no ❌")
        print("The database is not connected ❌")
    
    Database.close_connexion()



if __name__ == "__main__":
    main()