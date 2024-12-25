from flask import jsonify, request, Blueprint, Flask
from security import hash_password, verify_password, verify_auth_token_with_jwt, token_id_recuperar_password, security_blueprint
from validaciones import *

def create_blueprint(conexion):

    # Defining a blueprint
    usuario_bp = Blueprint('usuario', __name__)
    
    security_bp = security_blueprint(conexion)
    usuario_bp.register_blueprint(security_bp)



    # -----------------------------------------------------------------
    # ------------------  obtener datos de un usuario -----------------
    # -----------------------------------------------------------------
   
    @usuario_bp.route('/usuario', methods=["GET"])
    @security_bp.token_required
    def get_usuario(id_token, role_token):
        token = request.headers.get('Authorization')
        
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
                    ru.rol_id,
                    i.url_github                
                FROM 
                    usuarios u 
                LEFT JOIN 
                    informacion i ON u.id = i.usuario_id
                LEFT JOIN 
                    roles_usuarios ru ON u.id = ru.usuario_id
                WHERE u.id = %s
                """
            
            # Get Usuario
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
                    "url_github":user[7],
                    "perfiles": [],
                    "tecnologias": [],
                }            
                
            # Get Perfiles
            sql = """
                SELECT perfil FROM perfiles WHERE usuario_id = %s
                """
        
            cursor.execute(sql, (id_token,))
            perfiles = cursor.fetchall()  
            
            if perfiles:
                for perfil,*y in perfiles: # *y esta porque devuelve una tupla y si solo fuese perfil el output seria: ('x',)
                    data_usuario["perfiles"].append(perfil)
                    
            # Get Tecnologias
            sql = """
                SELECT tecnologia FROM tecnologias WHERE usuario_id = %s
                """
        
            cursor.execute(sql, (id_token,))
            tecnologias = cursor.fetchall()  
            
            if tecnologias:
                for tecnologia,*y in tecnologias: # *y esta porque devuelve una tupla y si solo fuese perfil el output seria: ('x',)
                    data_usuario["tecnologias"].append(tecnologia)

            # Endpoint Return                        
            if datos:
                return jsonify({"datos":data_usuario,"mensaje":"Datos del usuario "+user[3]}), 200
            else:
                return jsonify({"mensaje": "Usuario no encontrado"}), 404
        except Exception as ex:    
            return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500    
        finally:
            cursor.close()



    # -----------------------------------------------------------------------
    # - actualizar usuario --> usuarios, informacion, perfiles, tecnologias -
    # -----------------------------------------------------------------------    
    @usuario_bp.route('/usuario', methods=["PUT"])
    @security_bp.token_required
    def actualizar_usuario(id_token, role_token):

        nombre = request.form.get('nombre') 
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        github = request.form.get('github')
        informacion_adicional = request.form.get('informacion_adicional')
        imagenBase64 = request.form.get('image')
        perfiles = request.form.get('perfiles') 
        tecnologias = request.form.get('tecnologias')
        user_id_by_admin = request.form.get('id')
        
        
        if perfiles:
            perfiles = perfiles.split(',')
        
        if tecnologias:
            tecnologias = tecnologias.split(',')
        
        
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


            #verificar rol        
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)        
            if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
            else:
                id_user = validated_user_id["id"]


            # informacion desde el front
            info_user_front = {"nombre": nombre, 
                            "apellido": apellido, 
                            "email": email,                           
                            "info_adicional": informacion_adicional, 
                            "perfiles": perfiles, 
                            "tecnologias": tecnologias,
                            "github": github, 
                            "image": imagenBase64 
                            }      
            

            # buscar informacion del usuario en la bbdd     
            cursor.execute("""
                    SELECT u.nombre, u.apellido, u.email, i.informacion_adicional, i.url_github, i.image,
                    GROUP_CONCAT(DISTINCT p.perfil SEPARATOR ',') AS perfiles,
                    GROUP_CONCAT(DISTINCT t.tecnologia SEPARATOR ',') AS tecnologias
                    FROM usuarios u
                    LEFT JOIN informacion i ON u.id = i.usuario_id
                    LEFT JOIN perfiles p ON u.id = p.usuario_id
                    LEFT JOIN tecnologias t ON u.id = t.usuario_id
                    WHERE u.id = %s
                    GROUP BY u.id, u.nombre, u.apellido, u.email, i.informacion_adicional, i.url_github, image;
                       """, (id_user,))     
            user_bbdd = cursor.fetchone()
                      
            info_user_bbdd = {"nombre":user_bbdd[0], 
                            "apellido":user_bbdd[1], 
                            "email":user_bbdd[2], 
                            "info_adicional":user_bbdd[3],                                                  
                            "github": user_bbdd[4],
                            "image" : user_bbdd[5],
                            "perfiles": user_bbdd[6], 
                            "tecnologias":user_bbdd[7]
                            }
            

            # verificar si la informacion es igual a la almacenada en BBDD  
                ## 1 - agrega solo informacion enviada por front para comprar con bbdd
            verificar_con_bbdd = {}     

            for key, value in info_user_front.items():
                if value is not None:
                    verificar_con_bbdd[key] = value
                
                ## 2 - compara ambos diccionarios  
            datos_actualizar = verificacion_con_bbdd(verificar_con_bbdd, info_user_bbdd)

            if not datos_actualizar:
                return jsonify ({"mensaje": "todos los datos ya existen"}), 200  
            
            # if "error" in datos_actualizar:
            #     return jsonify(datos_actualizar), 500
            

            #verificar que el mail no pertenezca a otro usuario
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

            if "github" in datos_actualizar:
                set_clause["informacion"].append("url_github = %s")
                params["informacion"].append(github)

    
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


    # -----------------------------------------------------------------
    # -------------- Delete usuario join todas las tablas -------------
    # -----------------------------------------------------------------
    @usuario_bp.route('/usuario', methods=["DELETE"])
    @security_bp.token_required
    def borrar_usuario(id_token, role_token):

        datos= request.get_json(silent=True)

        try:
            cursor=conexion.connection.cursor()
           
            #verificar si es admin o user       
            if datos:   
                user_id_by_admin = datos.get('id')             
                validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
                if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
                else:
                    id_user = validated_user_id["id"]
            
            else:
                user_id_by_admin = None     
                validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
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

    return usuario_bp