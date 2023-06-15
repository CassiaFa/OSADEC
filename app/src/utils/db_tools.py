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
    __join = False

    @classmethod
    def open_connexion(cls):
        """
        This class method opens a connection to a MySQL database and returns an instance of a cursor that can be used to 
        execute SQL commands. It takes no parameters. It connects to the database using the class variables __USER, 
        __PWD, __HOST, __PORT, and __DB. If the cursor is already initialized, it does not try to connect again.
        """
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
        """
        Closes the connection to the database and sets the cursor object to None.

        :param cls: the class object.
        :return: None
        """
        cls.__cursor.close()
        cls.__bdd.close()
        cls.__cursor = None
    
    @classmethod
    def add_user(cls, gender, first_name, last_name, username, email, password):
        """
        Adds a new user to the database with the specified gender, first name, last name,
        username, email, and password. The password is encrypted using the secure encryption
        provided by the class. The function does not return anything.

        Args:
            gender (str): A string representing the gender of the user.
            first_name (str): A string representing the first name of the user.
            last_name (str): A string representing the last name of the user.
            username (str): A string representing the username of the user.
            email (str): A string representing the email of the user.
            password (str): A string representing the password of the user.
        """

        password = cls.__secure.encrypt(password, cls.__cursor)
        querry = "INSERT INTO users (gender, first_name, last_name, username, email, password) VALUES (%s, %s, %s, %s, %s, %s);"
        param = (gender, first_name, last_name, username, email, password)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()

    @classmethod
    def check_user(cls, username, password):
        """
        Check if the provided username and password match a user in the database.

        Args:
            username (str): The username of the user to check.
            password (str): The password of the user to check.

        Returns:
            dict: The user dictionary if the username and password match, False otherwise.
        """

        querry = f"SELECT * FROM users WHERE username='{username}';"
        cls.__cursor.execute(querry)

        user = cls.__cursor.fetchone()
        if user:
            if password == cls.__secure.decrypt(user['password'], cls.__cursor):
                return user
            else:
                return None
        else:
            return None
    
    @classmethod
    def get_files(cls, id_file=None, time_min=None, time_max=None, name=None):
        """
        A class method that retrieves files from the FILES table in the database.

        Args:
            id_file (int, optional): The id of the file to retrieve.
            time_min (str, optional): The minimum date of files to retrieve.
            time_max (str, optional): The maximum date of files to retrieve.
            name (str, optional): The name of the file to retrieve.

        Returns:
            list[dict]: A list of dict if there are multiple, or a dict if there is only one.
        """


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
        """
        A class method that retrieves detections from the DETECTIONS table in the database.

        Args:
            id_file (int, optional): An optional integer representing the id of the file to filter the detections by.
            time_min (str, optional): An optional string representing the minimum time to filter the detections by.
            time_max (str, optional): An optional string representing the maximum time to filter the detections by.

        Returns:
            list[dict]: A list of dict containing the start and stop times of each detection, and the id of the detected species.
        """

        if id_file:
            if time_min and time_max:
                querry = f"SELECT start, stop, id_species, confidence FROM DETECTIONS WHERE id_file={id_file} AND START>='{time_min}' AND STOP<='{time_max}';"
            elif time_min:
                querry = f"SELECT start, stop, id_species, confidence FROM DETECTIONS WHERE id_file={id_file} AND START>='{time_min}';"
            elif time_max:
                querry = f"SELECT start, stop, id_species, confidence FROM DETECTIONS WHERE id_file={id_file} AND STOP<='{time_max}';"
            else:
                querry = f"SELECT start, stop, id_species, confidence FROM DETECTIONS WHERE id_file={id_file};"
        else:
            querry = "SELECT start, stop, id_file, id_species, confidence FROM DETECTIONS;"
        
        cls.__cursor.execute(querry)

        result = cls.__cursor.fetchall()

        return result
    
    @classmethod
    def get_projects(cls, name=None, depth=None, lat=None, long=None):
        """
        Retrieves projects from the database based on optional filters.

        Args:
            name (str, optional): String representing the name of the project to retrieve.
            depth (int, optional): Integer representing the depth of the project to retrieve.
            lat (float, optional): Float representing the latitude of the project to retrieve.
            long (float, optional): Float representing the longitude of the project to retrieve.

        Returns:
            list[dict]: A list of dictionaries representing the retrieved projects, or a dictionary representing a 
            single project if only one is retrieved.
        """

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
        """
        Inserts a new project in the PROJECTS table with the given name, depth, latitude, and longitude.

        Args:
            name (str): The name of the project to insert.
            depth (float): The depth of the project to insert.
            lat (float): The latitude of the project to insert.
            long (float): The longitude of the project to insert.

        Returns:
            None
        """
        
        querry = "INSERT INTO PROJECTS (name, depth, latitude, longitude) VALUES (%s, %s, %s, %s);"
        param = (name, depth, lat, long)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()

    @classmethod
    def check_database(cls):
        """
        This is a class method that checks if there are tables in the database and if they are empty.
        
        Returns:
            bool : True if there are tables in the database and they are not empty, otherwise it prints an error message.
        """
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
        """
        Inserts a new file into the FILES table given its name, date, duration, fs, path,
        and id_project.

        Args:
            name (str): The name of the file.
            date (str): The date when the file was created.
            duration (int): The duration of the file in seconds.
            fs (str): The file system format of the file.
            path (str): The path of the file.
            id_project (int): The id of the project that the file belongs to.

        Returns:
            None
        """

        querry = "INSERT INTO FILES (name, date, duration, fs, path, id_project) VALUES (%s, %s, %s, %s, %s, %s);"
        param = (name, date, duration, fs, path, id_project)
        cls.__cursor.execute(querry, param)
        cls.__bdd.commit()


    @classmethod
    def add_detection(cls, start, stop, confidence, id_species, id_file):
        """
        Adds a new detection to the database.

        Args:
            start (int): Start time of the detection.
            stop (int): Stop time of the detection.
            confidence (float): Confidence level of the detection.
            id_species (int): ID of the species detected.
            id_file (int): ID of the file containing the detection.

        Returns:
            None
        """

        querry = "INSERT INTO DETECTIONS (start, stop, confidence ,id_file, id_species) VALUES (%s, %s, %s, %s, %s);"
        param = (start, stop, float(confidence), id_file, id_species)
        cls.__cursor.execute(querry, param)        
        cls.__bdd.commit()
    
    @classmethod
    def get_all_info(cls, file_name):
        """
        Retrieves all information about a file, the project and the detection corresponding to it.
        
        Args:
            file_name (str): The name of the file.

        Returns:
            dict: A dictionary containing the information about the file, the project and the detection
        """
        # querry = "SELECT @@GLOBAL.sql_mode;"
        # cls.__cursor.execute(querry)
        # test = cls.__cursor.fetchall
        if not cls.__join:
            cls.__cursor.execute("SET GLOBAL sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));")
            cls.__join = True

        querry = f" SELECT PROJECTS.name AS p_name, PROJECTS.depth, PROJECTS.latitude, PROJECTS.longitude, FILES.name, FILES.date, FILES.fs, FILES.duration, SPECIES.english_name AS s_name, COUNT(*) AS nb_detections \
                    FROM FILES \
                    INNER JOIN DETECTIONS ON FILES.id_file = DETECTIONS.id_file \
                    INNER JOIN PROJECTS ON FILES.id_project = PROJECTS.id_project \
                    INNER JOIN SPECIES ON DETECTIONS.id_species = SPECIES.id_species \
                    WHERE FILES.name='{file_name}'\
                    GROUP BY DETECTIONS.id_species;"
        cls.__cursor.execute(querry)
        result = cls.__cursor.fetchall()
        
        return result
   
        

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