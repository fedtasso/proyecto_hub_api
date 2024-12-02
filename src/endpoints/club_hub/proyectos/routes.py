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
        description = request.form.get('description')
        url_deploy = request.form.get('url_deploy')
        url_repository = request.form.get('url_repository')
        estado = request.form.get('estado')
        permite_sumarse = request.form.get('permite_sumarse')        
        tecnologias = request.form.get('tecnologias') # To DO resolver error si no se envia desde el front
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

            # if description:
            #     validaciones["description"] = (verificar_longitud_informacion, description, "description")

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
            
            cursor.execute(sql, (titulo, description, url_deploy, url_repository, estado, permite_sumarse))
            
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
    # -------------------- agregar participantes ----------------------
    # -----------------------------------------------------------------
    # Un usuario puede sumarse a un proyecto y un administrador de proyecto puede sumar a otro usuario
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
            cursor.execute("SELECT proyecto_id FROM usuarios_proyectos WHERE proyecto_id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401
            
            # verificar si admin agrega otro participante
            if sumar_participante:
                
                # verficar si es admin        
                cursor.execute("SELECT admin FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
                is_admin = cursor.fetchone()

                if is_admin == None:
                    return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401

                
                if is_admin[0] == 1:
                    id_user = sumar_participante
                    # verificar si el participante existe
                    participante_existe = find_user_by_id(cursor, id_user)
                
                    if not participante_existe:
                        return jsonify ({"mensaje": "El id proporcionado no corresponde a ningún participante"}), 401

                else:
                    return jsonify ({"mensaje": "No tiene permisos para agregar un participante al proyecto"}), 401

            
            
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
            cursor.execute("SELECT proyecto_id FROM usuarios_proyectos WHERE proyecto_id = %s", (proyecto_id,))
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
                up.usuario_id = %s
            GROUP BY p.id, p.titulo, p.descripcion, p.url_deploy, p.url_repository, p.estado, p.permite_sumarse;           
                """
           
            cursor.execute(sql, (id_token,))
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
                                       SELECT u.id, u.nombre, u.apellido, up.admin 
                                       FROM usuarios u 
                                       LEFT JOIN usuarios_proyectos up ON u.id = up.usuario_id
                                       WHERE u.id = %s""", (user,))
                        resultado = cursor.fetchall()
                                               
                        participante_proyecto ={}

                        # Evita error si un proyecto se quedó sin participantes
                        for i in resultado:
                            participante_proyecto["id"] = i[0]
                            participante_proyecto["nombre"] = i[1]
                            participante_proyecto["apellido"] = i[2]
                            participante_proyecto["admin"] = i[3]

                            lista_participantes.append(participante_proyecto)
                                                                
                    proyectos[dato[0]] = { 
                                "id" : dato[0],
                                "titulo" : dato[1],
                                "descripcion" : dato[2],
                                "url_deploy" : dato[3],
                                "url_repository" : dato[4],
                                "estado" : dato[5],
                                "permite_sumarse" : dato[6],
                                "participantes" : lista_participantes,
                                "tecnologias" : dato[8]
                    }
                                            
                return jsonify({"proyectos_admin" : proyectos})
            else:
                return jsonify({"mensaje": "proyecto no encontrado"}), 404
        
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
                                       SELECT u.id, u.nombre, u.apellido, up.admin 
                                       FROM usuarios u 
                                       LEFT JOIN usuarios_proyectos up ON u.id = up.usuario_id
                                       WHERE u.id = %s""", (user,))
                        resultado = cursor.fetchall()
                                               
                        participante_proyecto ={}

                        # Evita error si un proyecto se quedó sin participantes
                        for i in resultado:                           
                            participante_proyecto["nombre"] = i[1]
                            participante_proyecto["apellido"] = i[2]
                           

                            lista_participantes.append(participante_proyecto)
                                                                
                    proyectos[dato[0]] = { 
                                "id" : dato[0],
                                "titulo" : dato[1],
                                "descripcion" : dato[2],
                                "url_deploy" : dato[3],
                                "url_repository" : dato[4],
                                "estado" : dato[5],
                                "permite_sumarse" : dato[6],
                                "participantes" : lista_participantes,
                                "tecnologias" : dato[8]
                    }
                                            
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
    @proyectos_bp.route('/borrar_proyecto', methods=["DELETE"])
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
            cursor.execute("SELECT proyecto_id FROM usuarios_proyectos WHERE proyecto_id = %s", (proyecto_id,))
            datos_proyecto = cursor.fetchall()
            if not datos_proyecto:
                return jsonify ({"mensaje": "El proyecto no existe"}), 401

            # verificar si el participante está en el proyecto
            cursor.execute("SELECT usuario_id FROM usuarios_proyectos WHERE usuario_id = %s AND proyecto_id = %s", (id_user, proyecto_id))
            datos_usuario = cursor.fetchall()
            if not datos_usuario:
                return jsonify ({"mensaje": "El usuario no se encuentra registrado en el proyecto"}), 401
            
            # verificar si usuario es admin de proyecto
            
            # borrar en tabla participantes            
            cursor.execute("DELETE FROM usuarios_proyectos WHERE usuario_id = %s and proyecto_id = %s", (id_user, proyecto_id))

            conexion.connection.commit()
            return jsonify ({"mensaje": "Saliste del proyecto satisfactoriamente."}), 200

        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500  
          
        finally:
            cursor.close()

    return proyectos_bp