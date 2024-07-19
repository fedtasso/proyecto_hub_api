-- DROP DATABASE proyecto_hub

CREATE DATABASE IF NOT EXISTS proyecto_hub;
USE proyecto_hub;


CREATE TABLE usuarios(
    `id` int NOT NULL AUTO_INCREMENT,
    `nombre` VARCHAR(50) NOT NULL,
    `apellido` VARCHAR(50) NOT NULL,
    `email` VARCHAR(50) UNIQUE,
    `contraseña` VARCHAR(20),
    `fecha_registro` DATETIME,
    PRIMARY KEY (`id`)
);

INSERT INTO `usuarios` VALUES (0, 'Federico',  'Tasso', 'fedtasso@gmail.com','abcd1234','6-7-2024 00:00:00'),
(0, 'Bautista',  'Nar', 'bauti@gmail.com','abcd1234','7-7-2024 00:00:00');



SELECT * FROM usuarios;
SELECT * FROM usuarios where nombre = "Federico" AND apellido = "Tasso";

