USE `DATA`;

LOAD DATA INFILE '/var/lib/mysql-files/species.csv'
INTO TABLE SPECIES
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n' (abbreviation, latin_name, english_name);

LOAD DATA INFILE '/var/lib/mysql-files/projects.csv'
INTO TABLE PROJECTS
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n' (name, depth, latitude,longitude);

LOAD DATA INFILE '/var/lib/mysql-files/files.csv' 
INTO TABLE FILES 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n' (name, date, duration, fs, path, id_project);

LOAD DATA INFILE '/var/lib/mysql-files/detections.csv' 
INTO TABLE DETECTIONS
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n' (start, stop, id_file, id_species);