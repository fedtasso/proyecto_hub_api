from flask import jsonify, request, Blueprint, Flask
from security import hash_password, verify_password, verify_auth_token, token_required, token_id_recuperar_password
from validaciones import *

def create_blueprint(conexion,mail):

    # Defining a blueprint
    usuario_bp = Blueprint('usuario', __name__)


    #--- obtener datos de un usuario -----------
    @usuario_bp.route('/usuario', methods=["GET"])
    @token_required
    def get_usuario(id_token, role_token):
        
        try:
            cursor=conexion.connection.cursor()
            sql = """
                SELECT 
                    u.id,
                    u.nombre,
                    u.apellido,
                    u.email,                
                    i.informacion_adicional,
                    i.image,                
                    p.perfil,
                    t.tecnologia,                
                    ru.rol_id,
                    i.url_github                
                FROM 
                    usuarios u 
                LEFT JOIN 
                    informacion i ON u.id = i.usuario_id
                LEFT JOIN
                    perfiles p ON u.id = p.usuario_id
                LEFT JOIN 
                    tecnologias t ON u.id = t.usuario_id
                LEFT JOIN 
                    roles_usuarios ru ON u.id = ru.usuario_id
                WHERE u.id = %s
                """
            
            # ejecutar consulta
            cursor.execute(sql, (id_token,))
            datos = cursor.fetchall()  
            if datos:
                user = datos[0]
                data_usuario = {
                    "nombre": user[1],
                    "apellido": user[2],
                    "email": user[3],                        
                    "informacion": user[4],
                    "imagen": user[5],
                    "perfiles": [], 
                    "tecnologias": [],
                    "url_github":user[9]
                }            
                if user[6] is not None and user[6] not in data_usuario["perfiles"]:
                    data_usuario["perfiles"].append(user[6])
                if user[7] is not None and user[7] not in data_usuario["tecnologias"]:
                    data_usuario["tecnologias"].append(user[7])        
                return jsonify({"datos":data_usuario,"mensaje":"Datos del usuario "+user[3]}), 200
            else:
                return jsonify({"mensaje": "Usuario no encontrado"}), 404
        except Exception as ex:    
            return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500    
        finally:
            cursor.close()

    # ------- Update tablas --> usuarios, informacion, perfiles, tecnologias -----------
    @usuario_bp.route('/usuario', methods=["PUT"])
    @token_required
    def actualizar_usuario(id_token, role_token):

        # Se cambio para que use form
        nombre = request.form.get('nombre') 
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        github = request.form.get('github')
        informacion_adicional = request.form.get('informacion_adicional')
        imagenBase64 = request.form.get('image')
        perfiles = request.form.get('perfiles[]').split(',')
        tecnologias = request.form.get('tecnologias[]').split(',')   
        

        try: 
            cursor=conexion.connection.cursor()      
            conexion.connection.autocommit(False)

            #validar entradas
            validaciones = {}
            
            if nombre:
                validaciones["nombre"] = (validar_alpha, nombre, "nombre")

            if apellido:
                validaciones["apellido"] = (validar_alpha, apellido, "apellido")
            
            if email:
                validaciones["email"] = (validar_email, email, "email")
            
            if informacion_adicional:
                validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")

            if perfiles:
                validaciones["perfiles"] = (validar_comma_en_list, perfiles, "perfiles")
            
            if tecnologias:
                validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")

            resultado_validacion = validar_datos_generica(cursor, validaciones)        
            if resultado_validacion:
                return jsonify(resultado_validacion), 400
            print("validar datos",resultado_validacion)
                        
            # comparar info del front con la bbdd
            #informacion desde el front
            info_user_front = {"nombre": nombre, 
                            "apellido": apellido, 
                            "email": email,                           
                            "info_adicional": informacion_adicional, 
                            "perfiles": perfiles, 
                            "tecnologias": tecnologias,
                            "github": github
                            }      
            print(info_user_front)
            #buscar informacion del usuario en la bbdd     
            cursor.execute("""
                        SELECT u.nombre, u.apellido, u.email, i.informacion_adicional, i.url_github
                        FROM usuarios u
                        LEFT JOIN informacion i ON u.id = i.usuario_id
                        WHERE u.id = %s
                        """, (id_token,))     
            user_bbdd = cursor.fetchone()
        
            
            info_user_bbdd = {"nombre":user_bbdd[0], 
                            "apellido":user_bbdd[1], 
                            "email":user_bbdd[2], 
                            "info_adicional":user_bbdd[3],                                                  
                            "github": user_bbdd[4]
                            }
            
            cursor.execute("""
                        SELECT GROUP_CONCAT(DISTINCT perfil SEPARATOR ',') from perfiles where usuario_id = %s
                        """, (id_token,))     
            user_bbdd = cursor.fetchone()
            info_user_bbdd["perfiles"] = user_bbdd[0]
            
            cursor.execute("""
                        SELECT GROUP_CONCAT(DISTINCT tecnologia SEPARATOR ',') from tecnologias where usuario_id = %s
                        """, (id_token,))     
            user_bbdd = cursor.fetchone()
            info_user_bbdd["tecnologias"] = user_bbdd[0]
            
            print("info bbdd", info_user_bbdd)
            # verificar si la informacion es igual a la almacenada en BBDD  
            verificar_con_bbdd = {}
        
            for key, value in info_user_front.items():
                if value:
                    verificar_con_bbdd[key] = value
                
            datos_actualizar = verificacion_con_bbdd(id_token, verificar_con_bbdd, info_user_bbdd)
            if imagenBase64:
                datos_actualizar["image"] = imagenBase64
            print("datos_actualizar",datos_actualizar)
            if not datos_actualizar:
                print(id_token)
                return jsonify ({"mensaje": "todos los datos ya existen"}), 400  
            
            if "error" in datos_actualizar:
                return jsonify(datos_actualizar), 500
            
            #verificar que el mail no este usado por otro usuario
            if "email" in datos_actualizar:
                if validar_y_verificar_email(email, "email", cursor):
                    return jsonify ({"mensaje": "el mail ya existe"}), 400 
                
            # modificar informacion nueva en bbdd
            set_clause = {
                "usuarios": [],
                "informacion": [],
                "perfiles" : [],
                "tecnologias" : []
            }
            params = {
                "usuarios": [],
                "informacion": [],
                "perfiles" : [],
                "tecnologias" : [], 
            }
            
        
            if "nombre" in datos_actualizar:
                set_clause["usuarios"].append("nombre = %s")
                params["usuarios"].append(nombre)
            
            if "apellido" in datos_actualizar:
                set_clause["usuarios"].append("apellido = %s")
                params["usuarios"].append(apellido)

            if "email" in datos_actualizar:                        
                set_clause["usuarios"].append("email = %s")
                params["usuarios"].append(email)

            if "info_adicional" in datos_actualizar:
                set_clause["informacion"].append("informacion_adicional = %s")
                params["informacion"].append(informacion_adicional)
                
            if "image" in datos_actualizar:
                set_clause["informacion"].append("image = %s")
                params["informacion"].append(imagenBase64)
        

    
            # actualizar usuario
            if set_clause["usuarios"]:
                params["usuarios"].append(id_token)
                sql = f"""UPDATE usuarios
                                SET {', '.join(set_clause["usuarios"])} 
                                WHERE id = %s"""
                cursor.execute(sql, tuple(params["usuarios"]))

            # actualizar informacion
            if set_clause["informacion"]:
                params["informacion"].append(id_token)
                sql = f"""UPDATE informacion
                                SET {', '.join(set_clause["informacion"])} 
                                WHERE usuario_id = %s"""
                cursor.execute(sql, tuple(params["informacion"]))
                print(sql)
                print(tuple(params["informacion"]))

            # actualizar perfiles
            if "perfiles" in datos_actualizar:             
                for value in datos_actualizar["perfiles"]["update"]:            
                    sql = """
                        INSERT INTO
                            perfiles (usuario_id, perfil)
                        VALUES
                            (%s, %s)                                                       
                    """                    
                    cursor.execute(sql,(id_token, value))      
            
            #borrar perfiles            
                for value in datos_actualizar["perfiles"]["delete"]:                 
                    sql = """
                        DELETE FROM
                            perfiles 
                        WHERE 
                            usuario_id = %s  AND perfil = %s                                                     
                    """
                    cursor.execute(sql,(id_token, value)) 

            # actualizar tecnologias
            if "tecnologias" in datos_actualizar:             
                for value in datos_actualizar["tecnologias"]["update"]:            
                    sql = """
                        INSERT INTO
                            tecnologias (usuario_id, tecnologia)
                        VALUES
                            (%s, %s)                                                       
                    """                    
                    cursor.execute(sql,(id_token, value))      
            
            #borrar tecnologias            
                for value in datos_actualizar["tecnologias"]["delete"]:                 
                    sql = """
                        DELETE FROM
                            tecnologias 
                        WHERE 
                            usuario_id = %s  AND tecnologia = %s                                                     
                    """
                    cursor.execute(sql,(id_token, value)) 


            conexion.connection.commit()
            return jsonify({"mensaje": "Datos actualizados"}), 200        
        except Exception as ex:        
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al actualizar el usuario", "error": str(ex)}), 500
        finally:
            cursor.close()

    # ------- Delete usuario join todas las tablas   -----------
    @usuario_bp.route('/usuario', methods=["DELETE"])
    @token_required
    def borrar_usuario(id_token, role_token):

        datos= request.get_json(silent=True)

        try:
            cursor=conexion.connection.cursor()
            print(datos)
        
        
            #verificar si es admin o user       
            if datos:   
                user_id_by_admin = datos.get('id')             
                validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
                if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
                else:
                    id_user = validated_user_id["id"]
            
            else:
                user_id_by_admin = None     
                validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
                if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
                else:
                    id_user = id_token
            
        
            #Borrar usuario
            sql = "DELETE FROM usuarios WHERE id = %s"
            cursor.execute(sql,(id_user,))
            conexion.connection.commit()
            return jsonify({"mensaje":"Has eliminado el usuario"}), 200
        
        except Exception as ex:
            return jsonify({"mensaje":"error al eliminar el usuario", "error": str(ex)}), 500
        finally:
            cursor.close()


    # el user admin para cambiar su password debe enviar el id 1
    #-------------- actualizar_password -----------------
    @usuario_bp.route('/actualizar_password', methods=["PUT"])
    @token_required
    def actualizar_password(id_token, role_token):

        password = request.form.get("password")
        user_id_by_admin = request.form.get("id")
        try:
            cursor = conexion.connection.cursor()
            
            #verificar si es admin o user               
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
            if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
            else:
                id_user = validated_user_id["id"]
            print(id_user)      
            
            if password:

                #falta validar password
            
                #seleccionas pass de bbdd
                cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_user,))
                password_bbdd = cursor.fetchone()
                
                #verficar que el password sea distinto al almacenado
                if verify_password(password_bbdd[0], password):
                    return jsonify ({"mensaje": "la contraseña es identica a la actual"}), 400
                #actualizar password
                else:
                    hashed_password = hash_password(password)                
                    cursor.execute("UPDATE usuarios SET password = %s where id = %s", (hashed_password, id_token))
                    conexion.connection.commit()
                    return jsonify ({"mensaje": "contraseña actualizada con exito"}), 200
                
        except Exception as ex:
            return jsonify({"mensaje":"error al actualizar la contraseña", "error": str(ex)}), 500
        
        finally:
            cursor.close()


    #---------------------------------------------------------------------

    @usuario_bp.route('/recuperar_password', methods=["POST"])
    def recuperar_password():
        email = request.form.get("email")

        try:
            cursor = conexion.connection.cursor()
        
            if email:
                #validar formato de mail
                email_invalido = validar_email(email, "email")
                if email_invalido:
                    return jsonify (email_invalido)

                #buscar en bbdd
                mail_existe = verificar_email(email, cursor)
                
                if "error" in mail_existe:
                    return jsonify(mail_existe), 400
                
                usuario_id = mail_existe["id"]
                
                #crear token_id
                token_id = token_id_recuperar_password(usuario_id)
                
                #almacenar los token en la bbdd
                cursor.execute("INSERT INTO recuperar_password(usuario_id, token_id) VALUES (%s, %s)",(usuario_id, token_id))

                #crear mensaje
                # msg = Message ("Recuperar contraseña",                  
    #             recipients=[f"{email}"],
    #             body = f"""
    # Nos comunicamos desde el Club de Desarrolladores de Vicente López.
                
    # Para recuperar su contraseña acceda al siguiente link:

    # http://127.0.0.1:5000/restablecer_password?token_id={token_id}

    # Por favor, siga las instrucciones en la página para restablecer su contraseña.

    # Este es un correo automático, por favor no responda.
    #             """)
                msg = "Recuperar contraseña",                  

                # Enviar correo
                mail.send(msg) 

                conexion.connection.commit()

                return jsonify({"mensaje" : "email enviado con exito"}), 200
                
            else:
                return jsonify({"mensaje":"debe proporcionar un email"}), 400
            
        except Exception as e:
            return jsonify({"mensaje":"Error al enviar el correo", "error": {e}})



    @usuario_bp.route('/restablecer_password', methods=["POST"])
    def restablecer_password():

        token_id = request.args.get('token_id')
        password = request.form.get('password')
    
        if not token_id or not password:
            return jsonify({"mensaje" : "formato de recuperación incorrecto"}), 400
        
        token_valido = verify_auth_token(token_id)
                    
        if token_valido["status"] == "error":
            return jsonify (token_valido), 400
        
        # falta validar password
        
        try:   
            cursor = conexion.connection.cursor()

            usuario_id = token_valido["data"]["id_user"]

            hashed_password = hash_password(password) 

            #verificar si token fue usado
            cursor.execute("SELECT usado FROM recuperar_password WHERE usuario_id = %s", (usuario_id,))
            token_usado = cursor.fetchone()
            
            if token_usado[0] == 1:
                return jsonify({"mensaje" : "token expirado"}), 500
            
            #cambiar contraseña
            cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (hashed_password, usuario_id))

            #marcar token como usado
            cursor.execute("UPDATE recuperar_password SET usado = %s WHERE usuario_id = %s", (1, usuario_id,))


            conexion.connection.commit()

            return jsonify({"mensaje" : "contraseña cambiada exitosamente"}), 200
        
        except Exception as e:
            return jsonify({"mensaje":"Error al restablecer la contraseña", "error": str(e)}), 500
        
    # ---------- actualizar imagen de tabla informacion (form)-----------
    @usuario_bp.route('/image', methods=["PUT"]) #terminado
    @token_required
    def imagen(id_token, role_token):

        image = request.files.get('image')
        user_id_by_admin = request.form.get('id')
        
        # buscar usuario y asignar rol
        validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
        if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
        else:
            #if hay id request enviar error de permisos 400        
            id_user = validated_user_id["id"]    
        
        try: 
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            if image:
                file_path = imagen_validar_verificar_guardar(image, id_token)
            else:
                return jsonify({"mensaje": "debe seleccionar una imagen",}), 500    
            # insertar imagen en tabla informacion
            sql = "UPDATE informacion SET image = %s WHERE usuario_id = %s"
            cursor.execute(sql, (file_path, id_user))
                
            conexion.connection.commit()
            return jsonify({"mensaje": "imagen cargada con exito"}),200      
        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar la imagen", "error": str(ex)}), 500    
        finally:
            cursor.close()

    return usuario_bp