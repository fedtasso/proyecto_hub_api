DROP DATABASE proyecto_hub

CREATE DATABASE IF NOT EXISTS proyecto_hub;
USE proyecto_hub;


CREATE TABLE usuarios(
    `id` INT NOT NULL AUTO_INCREMENT,
    `nombre` VARCHAR(50) NOT NULL,
    `apellido` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) UNIQUE,
    `password` CHAR(60),
    `usuario_created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `usuario_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);



CREATE TABLE informacion(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario` INT, 
    `informacion_adicional` TEXT,
    `image` VARCHAR(255),
    `informacion_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);


CREATE TABLE perfiles(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario` INT, 
    `perfil` VARCHAR (50),
    `perfil_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE lenguajes(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario` INT, 
    `lenguaje` VARCHAR (50),
    `nivel` INT,
    `lenguaje_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);


-- Añadir restricciones de clave foránea

ALTER TABLE informacion 
ADD CONSTRAINT fk_informacion_usuarios 
FOREIGN KEY (usuario) REFERENCES usuarios(id)  ON DELETE CASCADE;

ALTER TABLE perfiles 
ADD CONSTRAINT fk_perfiles_usuarios 
FOREIGN KEY (usuario) REFERENCES usuarios(id)  ON DELETE CASCADE;

ALTER TABLE lenguajes 
ADD CONSTRAINT fk_lenguajes_usuarios 
FOREIGN KEY (usuario) REFERENCES usuarios(id) ON DELETE CASCADE;


-- Pruebas
INSERT INTO `usuarios` VALUES (0,'Federico',  'Tasso', 'fedtasso@gmail.com','abcd1234', NOW(), NOW()),
(0,'Bautista',  'Nar', 'bauti@gmail.com','abcd1234', NOW(), NOW());

SELECT * FROM usuarios;


