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
        return cursor.fetchone()[0].decode(cls.__encoding)

    @classmethod
    def decrypt(cls, pwd, cursor):
        querry = "SELECT AES_DECRYPT(%s, %s);"
        param = (bytearray(pwd, cls.__encoding), cls.__key)
        cursor.execute(querry, param)
        return cursor.fetchone()[0].decode(cls.__encoding)


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
        querry = f"SELECT password FROM users WHERE username='{username}';"
        cls.__cursor.execute(querry)
        pwd = cls.__cursor.fetchone()[0]

        if password == cls.__secure.decrypt(pwd, cls.__cursor):
            return True
        else:
            return False
    
    @classmethod
    def get_files(cls, id_file=None):

        if id_file:
            querry = f"SELECT name, date, duraton, path, fs FROM FILES WHERE id_file={id_file};"
        else:
            querry = "SELECT id_file, name, date, duration, path, fs FROM FILES;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

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
    def get_categories(cls):
        querry = f"SELECT id_species, english_name FROM SPECIES"

        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
    
   
        

def main():
    # first_name = "titi" 
    # last_name = "titi"
    # username = "titi"
    # email = "titi@titi.com" 
    # password= "tito"

    username = "cassiafa"
    password = "admin"
    test = Database()
    test.open_connexion()
    print(test.check_user(username, password))
    # test.add_user(first_name, last_name, username, email, password)
    test.close_connexion()



if __name__ == "__main__":
    main()