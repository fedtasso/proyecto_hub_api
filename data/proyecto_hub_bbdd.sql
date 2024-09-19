-- DROP DATABASE proyecto_hub

CREATE DATABASE IF NOT EXISTS proyecto_hub;
USE proyecto_hub;


CREATE TABLE usuarios(
    `id` INT NOT NULL AUTO_INCREMENT,
    `nombre` VARCHAR(50) NOT NULL,
    `apellido` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) UNIQUE,
    `password` VARCHAR(128),
    `usuario_created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `usuario_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);



CREATE TABLE informacion(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario_id` INT, 
    `informacion_adicional` TEXT,
    `image` VARCHAR(255),
    -- `image_id` INT,
    -- `hash_archivo` VARCHAR(255),
    `informacion_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

-- CREATE TABLE imagenes(
--     `id` INT NOT NULL AUTO_INCREMENT,
--     `image_id` INT,     
--     `file_path` VARCHAR(255),
--     `hash_archivo` VARCHAR(255),
--     `image_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     PRIMARY KEY (`id`)
-- );

CREATE TABLE perfiles(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario_id` INT, 
    `perfil` VARCHAR (50),
    `perfil_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE tecnologias(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario_id` INT, 
    `tecnologia` VARCHAR (50),
    `tecnologia_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE roles_usuarios(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario_id` INT, 
    `rol_id` INT,
    `rol_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE roles(
    `id` INT NOT NULL AUTO_INCREMENT,
    `rol` VARCHAR (50) NOT NULL,         
    PRIMARY KEY (`id`)
);

CREATE TABLE usuarios_proyectos(
    `id` INT NOT NULL AUTO_INCREMENT,
    `usuario_id` INT, 
    `proyecto_id` INT,
    `proyecto_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE proyectos(
    `id` INT NOT NULL AUTO_INCREMENT,
    `titulo` VARCHAR (50) NOT NULL, 
    `descripcion` TEXT,
    `url_deploy` VARCHAR (255),
    `url_repository` VARCHAR (255),
    `tecnologia` Varchar (50),
    `estado` VARCHAR (10),
    PRIMARY KEY (`id`)
);


-- Añadir restricciones de clave foránea

ALTER TABLE informacion 
ADD CONSTRAINT fk_informacion_usuarios 
FOREIGN KEY (usuario_id) REFERENCES usuarios(id)  ON DELETE CASCADE;

-- ALTER TABLE informacion 
-- ADD CONSTRAINT fk_imagen_informacion 
-- FOREIGN KEY (image_id) REFERENCES imagenes(id);

ALTER TABLE perfiles 
ADD CONSTRAINT fk_perfiles_usuarios 
FOREIGN KEY (usuario_id) REFERENCES usuarios(id)  ON DELETE CASCADE;

ALTER TABLE tecnologias
ADD CONSTRAINT fk_tecnologias_usuarios 
FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;

ALTER TABLE roles_usuarios
ADD CONSTRAINT fk__roles_usuarios__usuarios
FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
ADD CONSTRAINT fk__roles_id__roles
FOREIGN KEY (rol_id) REFERENCES roles(id);

ALTER TABLE usuarios_proyectos
ADD CONSTRAINT fk_usuarios_proyectos__usuarios
FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
ADD CONSTRAINT fk_proyecto_id__proyecto
FOREIGN KEY (proyecto_id) REFERENCES proyectos(id);


INSERT INTO `roles` VALUES (0,'admin'), (0, 'user');

-- AGREGAR USUARIO ADMIN MANUALMENTE A LA BBDD DESDE LA API PARA GENERAR HASH DE ADMIN
-- LUEGO EJECUTAR LAS SIGUIENTES LINEAS


UPDATE roles_usuarios SET rol_id = 1 WHERE id = 1;



