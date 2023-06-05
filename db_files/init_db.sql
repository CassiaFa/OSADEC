CREATE DATABASE IF NOT EXISTS `DATA` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;

USE `DATA`;

CREATE TABLE `FILES` (
  `id_file` int AUTO_INCREMENT,
  `name` varchar(50),
  `date` datetime,
  `duration` int,
  `fs` int,
  `path` varchar(100),
  `id_project` int,
  PRIMARY KEY (`id_file`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `DETECTIONS` (
  `id_detection` int AUTO_INCREMENT,
  `start` datetime,
  `stop` datetime,
  `confidence` float,
  `id_file` int,
  `id_species` int,
  PRIMARY KEY (`id_detection`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `PROJECTS` (
  `id_project` int AUTO_INCREMENT,
  `name` varchar(100) UNIQUE,
  `depth` int,
  `latitude` float(10,6),
  `longitude` float(10,6),
  PRIMARY KEY (`id_project`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `SPECIES` (
  `id_species` int AUTO_INCREMENT,
  `abbreviation` varchar(5),
  `latin_name` varchar(100),
  `english_name` varchar(100),
  PRIMARY KEY (`id_species`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `users` (
    `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `gender` VARCHAR(10) NOT NULL, 
    `first_name` VARCHAR(255) NOT NULL, 
    `last_name` VARCHAR(255) NOT NULL, 
    `username` VARCHAR(255) NOT NULL UNIQUE,
    `email` VARCHAR(200) NOT NULL, 
    `password` VARCHAR(32) NOT NULL, 
    `registration_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE `FILES` ADD FOREIGN KEY (`id_project`) REFERENCES `PROJECTS` (`id_project`);
ALTER TABLE `DETECTIONS` ADD FOREIGN KEY (`id_species`) REFERENCES `SPECIES` (`id_species`);
ALTER TABLE `DETECTIONS` ADD FOREIGN KEY (`id_file`) REFERENCES `FILES` (`id_file`);