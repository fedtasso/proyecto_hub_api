from flask import jsonify, request,  Blueprint
from security import security_blueprint
from validaciones import *

def create_blueprint(conexion):
    proyectos_bp = Blueprint('proyectos', __name__)

    security_bp = security_blueprint(conexion)
    proyectos_bp.register_blueprint(security_bp)

 

    # -----------------------------------------------------------------
    # ------------------------  crear proyecto ------------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/proyectos', methods=["POST"])
    @security_bp.token_required
    def proyecto(id_token, role_token):
        
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        url_deploy = request.form.get('url_deploy')
        url_repository = request.form.get('url_repository')
        estado = request.form.get('estado')
        permite_sumarse = request.form.get('permite_sumarse')        
        tecnologias = request.form.get('tecnologias')
        user_id_by_admin = request.form.get('id')
                
        if tecnologias:
            tecnologias = tecnologias.split(',')

        try: 
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            # buscar usuario y asignar rol
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
            id_user = validated_user_id["id"] 

            
          
            # validaciones = {} # TO DO validaciones

            # if titulo:   
            #     validaciones["titulo"] = (validar_alfanumerico, titulo, "titulo")# TO DO cambiar validacion a ya que no permite espacios
            # else:
            #     return jsonify ({"mensaje": " el titulo es requerido"})

            # if descripcion:
            #     validaciones["descripcion"] = (verificar_longitud_informacion, descripcion, "descripcion")

            # if url_deploy:
            #     validaciones["url_deply"] = (validar_url, url_deploy, "url_deploy") # TO DO crear validacion

            # if url_repository:
            #     validaciones["url_repository"] = (validar_url, url_repository, "url_repository") # TO DO crear validacion

            # if tecnologias:
            #     validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# TO DO no esta validando que no haya caracteres especiales

            # if estado:
            #     validaciones["estado"] = (validar_alfanumerico, estado, "estado")# TO DOcambiar validacion a ya que no permite espacios


            # resultado_validacion = validar_datos_generica(cursor, validaciones)        
            # if resultado_validacion: # TO DO llamarla not_validated o algo asi
            #     return jsonify(resultado_validacion), 400


            #insertar en tabla proyectos
            sql = """INSERT INTO proyectos(
                        titulo, 
                        descripcion, 
                        url_deploy, 
                        url_repository,
                        estado,
                        permite_sumarse)
                        VALUES (%s, %s, %s, %s, %s, %s)"""
            
            cursor.execute(sql, (titulo, descripcion, url_deploy, url_repository, estado, permite_sumarse))
            
            #recuperar id de proyecto
            proyecto_id = cursor.lastrowid

            # insertar creador en usuarios_proyectos
            cursor.execute("INSERT INTO usuarios_proyectos (usuario_id, proyecto_id, admin) VALUES (%s, %s, %s)", (id_user ,proyecto_id, 1))

            # insertar en tabla tecnologias_proyecto
            for tecnologia in tecnologias:
                cursor.execute("INSERT INTO tecnologias_proyectos (proyecto_id, tecnologia) VALUES (%s, %s)", (proyecto_id, tecnologia))
                    
            conexion.connection.commit()
            return jsonify({"mensaje": "proyecto cargado con exito"}),200   
           
        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()


    # -----------------------------------------------------------------
    # ---------------------- Actualizar proyecto ----------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/proyecto', methods=["PUT"])
    @security_bp.token_required
    def actualizar_proyecto(id_token, role_token):
        
        proyecto_id = request.form.get('proyecto_id')
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        url_deploy = request.form.get('url_deploy')
        url_repository = request.form.get('url_repository')
        estado = request.form.get('estado')
        permite_sumarse = request.form.get('permite_sumarse') 
        tecnologias = request.form.get('tecnologias') 
        user_id_by_admin = request.form.get('id')

        if tecnologias:
            tecnologias = tecnologias.split(',')

        # validaciones = {} # TO DO validaciones

        # if titulo:   
        #     validaciones["titulo"] = (validar_alfanumerico, titulo, "titulo")# TO DO cambiar validacion a ya que no permite espacios
        # else:
        #     return jsonify ({"mensaje": " el titulo es requerido"})

        # if descripcion:
        #     validaciones["descripcion"] = (verificar_longitud_informacion, descripcion, "descripcion")

        # if url_deploy:
        #     validaciones["url_deply"] = (validar_url, url_deploy, "url_deploy") # TO DO crear validacion

        # if url_repository:
        #     validaciones["url_repository"] = (validar_url, url_repository, "url_repository") # TO DO crear validacion

        # if tecnologias:
        #     validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# TO DO no esta validando que no haya caracteres especiales

        # if estado:
        #     validaciones["estado"] = (validar_alfanumerico, estado, "estado")# TO DOcambiar validacion a ya que no permite espacios


        # resultado_validacion = validar_datos_generica(cursor, validaciones)        
        # if resultado_validacion: # TO DO llamarla not_validated o algo asi
        #     return jsonify(resultado_validacion), 400

        try: 
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            # buscar usuario y asignar rol
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
            id_user = validated_user_id["id"] 

            # verificar si proyecto existe
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()            
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401
            

            # verificar si id_user es administrador del proyecto
            cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            rol_proyecto = cursor.fetchone()
            if not rol_proyecto:
                return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401                            
            if rol_proyecto[0] == 0:
                return jsonify ({"mensaje": "sin permisos, el usuario no es administrador"}), 401
            

            # agrupar en diccionario informacion del front            
            info_proyecto_front = {'titulo' : titulo,
                                   'descripcion' : descripcion,
                                   'url_deploy' : url_deploy,
                                   'url_repository' : url_repository,
                                   'estado' : estado,
                                   'permite_sumarse' : permite_sumarse,
                                   'tecnologias' : tecnologias
                                    }

            # buscar informacion de proyecto en BBDD
            sql= """
            SELECT
                p.id,
                p.titulo,
                p.descripcion,
                p.url_deploy,
                p.url_repository,
                p.estado,
                p.permite_sumarse,                               
                GROUP_CONCAT(DISTINCT tp.tecnologia SEPARATOR ',') AS tecnologias
            FROM 
                proyectos p
            LEFT JOIN
                tecnologias_proyectos tp ON p.id = tp.proyecto_id
            WHERE 
                p.id = %s
             GROUP BY 
             p.id, p.titulo, p.descripcion, p.url_deploy, p.url_repository, p.estado, p.permite_sumarse;
                """            
            cursor.execute(sql, (proyecto_id,))
            datos = cursor.fetchone()

            info_proyecto_bbdd = {'titulo' : datos[1],
                                   'descripcion' : datos[2],
                                   'url_deploy' : datos[3],
                                   'url_repository' : datos[4],
                                   'estado' : datos[5],
                                   'permite_sumarse' : str(datos[6]),
                                   'tecnologias' : datos[7]
                                    }
            

            # verificar si la informacion es igual a la almacenada en BBDD  
                ## 1 - agrega solo informacion enviada por front para comprar con bbdd
            verificar_con_bbdd = {}     
            for key, value in info_proyecto_front.items():                
                if value:                    
                    verificar_con_bbdd[key] = value
            
                ## 2 - compara ambos diccionarios
            datos_actualizar = verificacion_con_bbdd(verificar_con_bbdd, info_proyecto_bbdd)           
            if not datos_actualizar:
                return jsonify ({"mensaje": "todos los datos ya existen"}), 200  
            
                        
            # crear diccionario con solo tablas a actualizar
            set_clause = {
                "proyectos": [],
                "tecnologias_proyectos": []                
            }
            params = {
               "proyectos": [],
               "tecnologias_proyectos": []
            }

            #agregar informacion a diccionarios
            if "titulo" in datos_actualizar:
                set_clause["proyectos"].append("titulo = %s")
                params["proyectos"].append(titulo)

            if "descripcion" in datos_actualizar:
                set_clause["proyectos"].append("descripcion = %s")
                params["proyectos"].append(descripcion)

            if "url_repository" in datos_actualizar:
                set_clause["proyectos"].append("url_repository = %s")
                params["proyectos"].append(url_repository)

            if "url_deploy" in datos_actualizar:
                set_clause["proyectos"].append("url_deploy = %s")
                params["proyectos"].append(url_deploy)

            if "estado" in datos_actualizar:
                set_clause["proyectos"].append("estado = %s")
                params["proyectos"].append(estado)

            if "permite_sumarse" in datos_actualizar:
                set_clause["proyectos"].append("permite_sumarse = %s")
                params["proyectos"].append(permite_sumarse)

            if "tecnologias" in datos_actualizar:
                set_clause["tecnologias_proyectos"].append("tecnologia = %s")
                params["tecnologias_proyectos"].append(tecnologias)

            
            # actualizar proyecto
            if set_clause["proyectos"]:
                params["proyectos"].append(proyecto_id)
                sql = f"""UPDATE proyectos SET {', '.join(set_clause["proyectos"])} WHERE id = %s"""               
                cursor.execute(sql, tuple(params["proyectos"]))

            

            # actualizar tecnologias
            if "tecnologias" in datos_actualizar:             
                for value in datos_actualizar["tecnologias"]["update"]:            
                    sql = """
                        INSERT INTO
                            tecnologias_proyectos (tecnologia, proyecto_id)
                        VALUES
                            (%s, %s)                                                       
                    """                    
                    cursor.execute(sql,(value, proyecto_id))      
            
            #borrar tecnologias            
                for value in datos_actualizar["tecnologias"]["delete"]:                 
                    sql = """
                        DELETE FROM
                            tecnologias_proyectos 
                        WHERE 
                            tecnologia = %s AND proyecto_id = %s 
                    """
                    cursor.execute(sql,(value, proyecto_id)) 
            
              
            conexion.connection.commit()
            return jsonify({"mensaje": "proyecto cargado con exito"}),200   
           
        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()

    # -----------------------------------------------------------------
    # --------------------- sumarse a proyecto ------------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/sumarse_proyecto', methods=["POST"])
    @security_bp.token_required
    def sumarse_proyecto(id_token, role_token):
    
        proyecto_id = request.form.get('proyecto_id')
        sumar_participante = request.form.get('participante')
        user_id_by_admin = request.form.get('id')

        if not proyecto_id:
             return jsonify ({"mensaje": "debe proporcionar un id de proyecto"}), 401
        
        # TO Do validaciones
        
        try:
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            # buscar usuario y asignar rol
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
                
            id_user = validated_user_id["id"] 

            # verificar si proyecto existe
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401
            

            # # verificar si admin agrega otro participante
            # if sumar_participante:
                
            #     # verficar si es admin        
            #     cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            #     is_admin = cursor.fetchone()

            #     if is_admin == None:
            #         return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401

                
            #     if is_admin[0] == 1:
            #         id_user = sumar_participante
            #         # verificar si el participante existe
            #         participante_existe = find_user_by_id(cursor, id_user)
                
            #         if not participante_existe:
            #             return jsonify ({"mensaje": "El id proporcionado no corresponde a ningún participante"}), 401

            #     else:
            #         return jsonify ({"mensaje": "No tiene permisos para agregar un participante al proyecto"}), 401

            
            
            # verificar si el participante está en el proyecto
            cursor.execute("SELECT usuario_id FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            datos = cursor.fetchall()
            if datos:
                return jsonify ({"mensaje": "El usuario ya se encuentra registrado en el proyecto"}), 401

            # insertar en tabla participantes            
            cursor.execute("INSERT INTO usuarios_proyectos (usuario_id, proyecto_id) VALUES (%s, %s)", (id_user, proyecto_id))

            conexion.connection.commit()
            return jsonify ({"mensaje": "Te uniste satisfactoriamente al proyecto. Bienvenido!"}), 200

        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()


    # -----------------------------------------------------------------
    # ---------------------- salir de proyecto ------------------------
    # -----------------------------------------------------------------
    # usuario sale de proyecto con token, admin_proyecto borra participante con borrar_participante
    @proyectos_bp.route('/salir_proyecto', methods=["DELETE"])
    @security_bp.token_required
    def salir_proyecto(id_token, role_token):
        
        proyecto_id = request.form.get('proyecto_id')
        borrar_participante = request.form.get('participante')
        user_id_by_admin = request.form.get('id')
       
        # TO Do validaciones
       
        try:
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            # buscar usuario y asignar rol TO DO revisar como funciona si es admin del sitio
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
                
            id_user = validated_user_id["id"] 

            # verificar si proyecto existe
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401

            # verificar si admin está en el proyecto y si agrega a otro participante
            if borrar_participante:
                # verficar si es admin
                cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
                is_admin = cursor.fetchone()

                if not is_admin:
                    return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
                
                if is_admin[0] == 1:
                    id_user = borrar_participante
                    # verificar si el participante existe
                    participante_existe = find_user_by_id(cursor, id_user)
                
                    if not participante_existe:
                        return jsonify ({"mensaje": "El id proporcionado no corresponde a ningún participante"}), 401

                else:
                    return jsonify ({"mensaje": "No tiene permisos para borrar un participante del proyecto"}), 401

            # verificar si el participante está en el proyecto
            cursor.execute("SELECT usuario_id FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            datos_usuario = cursor.fetchall()
            
            if not datos_usuario:
                return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
            
            # borrar en tabla participantes            
            cursor.execute("DELETE FROM usuarios_proyectos WHERE usuario_id = %s and proyecto_id = %s", (id_user, proyecto_id))

            conexion.connection.commit()
            if borrar_participante:
                return jsonify ({"mensaje": "El participante ha sido eliminado del proyecto."}), 200
            else:
                return jsonify ({"mensaje": "Saliste del proyecto satisfactoriamente."}), 200

        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()



    # -----------------------------------------------------------------
    # ---------------------  mostrar proyectos admin ------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/proyectos_admin', methods=["GET"]) 
    @security_bp.token_required
    def mostrar_proyecto_admin(id_token, role_token):
       
        # TO Do validaciones
        
        try:
            cursor = conexion.connection.cursor()
                               
            sql= """
            SELECT
                p.id,
                p.titulo,
                p.descripcion,
                p.url_deploy,
                p.url_repository,
                p.estado,
                p.permite_sumarse,                
                GROUP_CONCAT(DISTINCT tp.tecnologia SEPARATOR ',') AS tecnologias
            FROM 
                proyectos p
            LEFT JOIN
                usuarios_proyectos up ON p.id = up.proyecto_id
            LEFT JOIN
                tecnologias_proyectos tp ON p.id = tp.proyecto_id
            WHERE 
                up.usuario_id = %s AND up.admin = 1
            GROUP BY p.id, p.titulo, p.descripcion, p.url_deploy, p.url_repository, p.estado, p.permite_sumarse;           
                """
           
            cursor.execute(sql, (id_token,))
            datos = cursor.fetchall()
                   

            if datos:
                proyectos = {}
                for dato in datos:  
                   
                    cursor.execute("""SELECT u.id, u.nombre, u.apellido, i.image, up.admin 
                            FROM usuarios u
                            LEFT JOIN informacion i ON i.usuario_id = u.id                            
                            LEFT JOIN usuarios_proyectos up ON up.usuario_id = u.id                            
                            WHERE up.proyecto_id = %s
                            """, (dato[0],))
                    data_participantes = cursor.fetchall()
                    lista_participantes = []
                                        
                    for i in data_participantes:    
                        participantes_proyecto = {}

                        participantes_proyecto["id"] = i[0]
                        participantes_proyecto["nombre"] = i[1]
                        participantes_proyecto["apellido"] = i[2]
                        participantes_proyecto["image"] = i[3]
                        participantes_proyecto["admin"] = i[4]
                        lista_participantes.append(participantes_proyecto)
                        
                    lista_tecnologias = []
                    if dato[7] != None and dato[7] != 'undefined':
                        lista_tecnologias = dato[7].split(',')   
                   
                    proyectos[dato[0]] = { 
                                "id" : dato[0],
                                "titulo" : dato[1],
                                "descripcion" : dato[2],
                                "url_deploy" : dato[3],
                                "url_repository" : dato[4],
                                "estado" : dato[5],
                                "permite_sumarse" : dato[6],
                                "participantes" : lista_participantes,
                                "tecnologias" : lista_tecnologias
                    }
                     
                lista_proyectos = list(proyectos.values())       
                return jsonify({"proyectos_admin" : lista_proyectos})
            else:
                return jsonify({"mensaje": "el usuario no es administrador de proyecto"}), 404
        
        except Exception as ex:         
            return jsonify({"mensaje": "Error al buscar los proyectos del usuario", "error": str(ex)}), 500    
        finally:
            cursor.close()

    # -----------------------------------------------------------------
    # ------------------------  mostrar proyectos ---------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/proyectos', methods=["GET"]) 
    # si el token es requerido no va a dar error participantes porque muestra sus propios proyectos, 
    # si muestra todos los proyectos existentes si verficar que participantes no sea None
    # @token_required
    def mostrar_proyecto():
        titulo = request.args.get('titulo')        
        
        # TO Do validaciones
        
        try:
            cursor=conexion.connection.cursor()


            sql= """
            SELECT
                p.id,
                p.titulo,
                p.descripcion,
                p.url_deploy,
                p.url_repository,
                p.estado,
                p.permite_sumarse,               
                GROUP_CONCAT(DISTINCT up.usuario_id SEPARATOR ',') AS particpantes,
                GROUP_CONCAT(DISTINCT tp.tecnologia SEPARATOR ',') AS tecnologias
            FROM 
                proyectos p
            LEFT JOIN
                usuarios_proyectos up ON p.id = up.proyecto_id
            LEFT JOIN
                tecnologias_proyectos tp ON p.id = tp.proyecto_id
            WHERE 
                1 = 1                 
                """
            parametros = []
            if titulo:
                sql += "AND titulo = %s"
                parametros.append(titulo)
            
            sql +=  " GROUP BY p.id, p.titulo, p.descripcion, p.url_deploy, p.url_repository, p.estado, p.permite_sumarse;"

            cursor.execute(sql, parametros)
            datos = cursor.fetchall()
            
            if datos:
                proyectos = {}
                for dato in datos:  
                    
                    # Evita error si un proyecto se quedó sin participantes
                    if dato[7] == None:
                        participantes = ()                        
                    else:
                        participantes = dato[7].split(',')                 

                    lista_participantes = []
                    for user in participantes:

                        cursor.execute("""
                                       SELECT u.id, u.nombre, u.apellido, i.image, up.admin 
                                       FROM usuarios u 
                                       LEFT JOIN informacion i ON u.id = i.usuario_id
                                       LEFT JOIN usuarios_proyectos up ON u.id = up.usuario_id
                                       WHERE u.id = %s AND proyecto_id = %s""", (user, dato[0]))
                        resultado = cursor.fetchall()
                        participante_proyecto ={}

                        # Evita error si un proyecto se quedó sin participantes
                        for i in resultado:                           
                            participante_proyecto["nombre"] = i[1]
                            participante_proyecto["apellido"] = i[2]
                            participante_proyecto["image"] = i[3]
                           

                            lista_participantes.append(participante_proyecto)
                            
                            
                    lista_tecnologias = []
                    if dato[8] != None and dato[8] != 'undefined':
                        lista_tecnologias = dato[8].split(',')     
                                                                
                    proyectos[dato[0]] = { 
                                "id" : dato[0],
                                "titulo" : dato[1],
                                "descripcion" : dato[2],
                                "url_deploy" : dato[3],
                                "url_repository" : dato[4],
                                "estado" : dato[5],
                                "permite_sumarse" : dato[6],
                                "participantes" : lista_participantes,
                                "tecnologias" : lista_tecnologias
                    }
                proyectos = list(proyectos.values())                                    
                return jsonify({"proyectos" : proyectos})
            else:
                return jsonify({"mensaje": "proyecto no encontrado"}), 404
        
        except Exception as ex:         
            return jsonify({"mensaje": "Error al buscar el proyecto", "error": str(ex)}), 500    
        finally:
            cursor.close()


    # -----------------------------------------------------------------
    # ----------------------- borrar proyecto -------------------------
    # -----------------------------------------------------------------
    @proyectos_bp.route('/proyecto', methods=["DELETE"])
    @security_bp.token_required
    def borrar_proyecto(id_token, role_token):
        
        proyecto_id = request.form.get('proyecto_id')
        user_id_by_admin = request.form.get('id')
       
        # TO Do validaciones

        try:
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)

            # buscar usuario y asignar rol
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                    return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
                
            id_user = validated_user_id["id"] 

            # verificar si proyecto existe
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401

            # verificar si id_user (quien accede al endpoint) es administrador del proyecto
            cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            rol_proyecto = cursor.fetchone()
            if not rol_proyecto:
                return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
                            
            if rol_proyecto[0] == 0:
                return jsonify ({"mensaje": "sin permisos, el usuario no es administrador"}), 401

            # borrar en tabla participantes            
            cursor.execute("DELETE FROM proyectos WHERE id = %s", (proyecto_id,))

            conexion.connection.commit()
            return jsonify ({"mensaje": "Proyecto eliminado."}), 200

        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al borrar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()



    # -----------------------------------------------------------------
    # ------------------- añadir admin de proyecto --------------------
    # ----------------------------------------------------------------- 
    # cambiar rol a admin con is_admin, cambiar rol a participante con is_participante   
    @proyectos_bp.route('/cambiar_rol_proyecto', methods=["PUT"])
    @security_bp.token_required
    def cambiar_rol_proyecto(id_token, role_token):
        
        proyecto_id = request.form.get('proyecto_id')
        is_admin = request.form.get('is_admin')
        is_participante = request.form.get('is_participante')

        # TO Do validaciones
        if is_admin and is_participante:
            return jsonify ({"mensaje": "debe enviar un solo rol"}), 401
        try:
            cursor=conexion.connection.cursor()
            conexion.connection.autocommit(False)


            # verificar si proyecto existe
            cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401

            if is_admin:
                # verficar si es admin o participante
                cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (is_admin, proyecto_id))
                rol = cursor.fetchone()

                if not rol:
                    return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
                                
                if rol[0] == 1:
                    return jsonify ({"mensaje": "error, el usuario ya es administrador"}), 401
                    # verificar si el participante existe
                                   
                if rol[0] == 0:
                    cursor.execute("UPDATE usuarios_proyectos SET admin = 1 WHERE usuario_id = %s AND proyecto_id = %s", (is_admin, proyecto_id))
                    conexion.connection.commit()
                    return jsonify ({"mensaje": "cambio de rol exitoso"}), 200
            
            if is_participante:
                # verficar si es admin o participante
                cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (is_participante, proyecto_id))
                rol = cursor.fetchone()

                if not rol:
                    return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
                                
                if rol[0] == 0:
                    return jsonify ({"mensaje": "error, el usuario ya es administrador"}), 401
                    # verificar si el participante existe
                                   
                if rol[0] == 1:
                    cursor.execute("UPDATE usuarios_proyectos SET admin = 0 WHERE usuario_id = %s AND proyecto_id = %s", (is_participante, proyecto_id))
                    conexion.connection.commit()
                    return jsonify ({"mensaje": "cambio de rol exitoso"}), 200

        

        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()



    return proyectos_bp