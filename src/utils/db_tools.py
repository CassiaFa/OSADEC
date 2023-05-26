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
    __HOST = 'localhost'
    __PORT = '3307'
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
    def get_files(cls, id_file=None):

        if id_file:
            querry = f"SELECT name, date, path FROM FILES WHERE id_file={id_file};"
        else:
            querry = "SELECT name, date, path FROM FILES;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
    
    @classmethod
    def get_detections(cls, id_file=None):

        if id_file:
            querry = f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file};"
        else:
            querry = "SELECT start, stop, id_species FROM DETECTIONS;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
    
    @classmethod
    def get_projects(cls, name=None, depth=None, lat=None, long=None):
        if name:
            querry = f"SELECT * FROM projects WHERE name='{name}';"
        elif depth:
            querry = f"SELECT * FROM projects WHERE depth={depth};"
        elif lat:
            querry = f"SELECT * FROM projects WHERE lat={lat};"
        elif long:
            querry = f"SELECT * FROM projects WHERE long={long};"
        else:
            querry = "SELECT * FROM projects;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        # return first element if there is only one, otherwise return list
        if len(result) == 1:
            return result[0]
        else:
            return result

    @classmethod
    def add_project(cls, name, depth, lat, long):
        querry = "INSERT INTO projects (name, depth, lat, long) VALUES (%s, %s, %s, %s);"
        param = (name, depth, lat, long)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()


    @classmethod
    def add_file(cls, name, date, duration, fs, path, id_project):
        querry = "INSERT INTO files (name, date, duration, fs, path, id_project) VALUES (%s, %s, %s, %s, %s, %s);"
        param = (name, date, duration, fs, path, id_project)
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


    # def __init__(self) -> None:

    #     self.__USER = 'root'
    #     self.__PWD = 'root'
    #     self.__HOST = 'localhost'
    #     self.__PORT = '3306'
    #     self.__DB = 'USER_DB'
    #     self.__cursor = None
    #     self.__secure = Encryptor()

    # def open_connexion(self):
    #     if not self.__cursor:
    #         self.__bdd = mysqlpy.connect(
    #                                     user = self.__USER,
    #                                     password = self.__PWD,
    #                                     host = self.__HOST,
    #                                     port = self.__PORT,
    #                                     database = self.__DB
    #                                     )

    #         self.__cursor = self.__bdd.cursor()
    
    # def close_connexion(self):
    #     self.__cursor.close()
    #     self.__bdd.close()
    #     self.__cursor = None
    
    # def add_user(self, first_name, last_name, username, email, password):
    #     password = self.__secure.encrypt(password, self.__cursor)
    #     querry = "INSERT INTO users (first_name, last_name, username, email, password) VALUES (%s, %s, %s, %s, %s);"
    #     param = (first_name, last_name, username, email, password)
    #     self.__cursor.execute(querry, param)
    #     self.__bdd.commit()

    # def check_user(self, username, password):
    #     querry = f"SELECT password FROM users WHERE username='{username}';"
    #     self.__cursor.execute(querry)
    #     pwd = self.__cursor.fetchone()[0]

    #     if password == self.__secure.decrypt(pwd, self.__cursor):
    #         return True
    #     else:
    #         return False


    # def test(self, txt):
    #     toto = self.__secure.encrypt(txt, self.__cursor)
    #     print(toto)

        

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