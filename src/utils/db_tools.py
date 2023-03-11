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

    # def __init__(self) -> None:
    #     load_dotenv()
    #     self.__key = os.getenv('ENCRYPT_KEY')
    #     self.__encoding = os.getenv('ENCODING')
    
    # def encrypt(self, txt:str, cursor):
    #     querry = "SELECT AES_ENCRYPT(%s, %s);"
    #     param = (txt, self.__key)
    #     cursor.execute(querry, param)
    #     return cursor.fetchone()[0].decode(self.__encoding)

    # def decrypt(self, pwd, cursor):
    #     querry = "SELECT AES_DECRYPT(%s, %s);"
    #     param = (bytearray(pwd, self.__encoding), self.__key)
    #     cursor.execute(querry, param)
    #     return cursor.fetchone()[0].decode(self.__encoding)

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

            cls.__cursor = cls.__bdd.cursor()
    
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
    def get_detections(cls, id_file=None):

        if id_file:
            querry += f"SELECT start, stop, id_species FROM DETECTIONS WHERE id_file={id_file};"
        else:
            querry = "SELECT start, stop, id_species FROM DETECTIONS;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
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