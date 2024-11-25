# ------------  CRUD tabla proyectos ------------------
@app.route('/proyecto', methods=["POST"]) #terminado
@token_required
def proyecto(id_token, role_token):
    
    titulo = request.form.get('titulo')
    description = request.form.get('description')
    url_deploy = request.form.get('url_deploy')
    url_repository = request.form.get('url_repository')
    tecnologias = request.form.getlist('tecnologias[]')
    estado = request.form.get('estado')
    integrantes = request.form.getlist('integrantes[]')
    user_id_by_admin = request.form.get('id')
    
    # buscar usuario y asignar rol
    validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
    if validated_user_id["id"] is None:
            return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
           
    id_user = validated_user_id["id"]    
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)

        validaciones = {}

        if titulo:   
            validaciones["titulo"] = (validar_alfanumerico, titulo, "titulo")# cambiar validacion a ya que no permite espacios
        else:
            return jsonify ({"mensaje": " el titulo es requerido"})

        if description:
            validaciones["description"] = (verificar_longitud_informacion, description, "description")

        if url_deploy:
            validaciones["url_deply"] = (validar_url, url_deploy, "url_deploy")

        if url_repository:
            validaciones["url_repository"] = (validar_url, url_repository, "url_repository")

        if tecnologias:
            validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# no esta validando que no haya caracteres especiales

        if estado:
            validaciones["estado"] = (validar_alfanumerico, estado, "estado")# cambiar validacion a ya que no permite espacios


        resultado_validacion = validar_datos_generica(cursor, validaciones)        
        if resultado_validacion: #llamarla not_validated o algo asi
            return jsonify(resultado_validacion), 400

        #insertar en tabla proyectos
        sql = """INSERT INTO proyectos(
                    titulo, 
                    descripcion, 
                    url_deploy, 
                    url_repository,
                    estado,
                    usuario_id_owner)
                    VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (titulo, description, url_deploy, url_repository, estado, id_user))
        
        #recuperar id de proyecto
        proyecto_id = cursor.lastrowid

        # insertar en tabla tecnologias_proyecto
        for tecnologia in tecnologias:
            cursor.execute("INSERT INTO tecnologias_proyecto (proyecto_id, tecnologia) VALUES (%s, %s)", (proyecto_id, tecnologia))
        
        # insertar en tabla usuarios_proyecto
        integrantes_id = [id_token]
        for email in integrantes:            
            usuario_id = find_user_by_email(cursor, email)#no estoy validando el formato del mail
            if usuario_id == None:
                return jsonify({"mensaje": f"el usuario {email} no se encuentra registrado", "error": "usuario invalido"})
            integrantes_id.append(usuario_id[0])
        
        for usuario_id in integrantes_id:
            cursor.execute("INSERT INTO usuarios_proyecto (usuario_id, proyecto_id) VALUES (%s, %s)", (usuario_id, proyecto_id))
        

        conexion.connection.commit()
        return jsonify({"mensaje": "proyecto cargado con exito"}),200      
    except Exception as ex: 
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500    
    finally:
        cursor.close()



@app.route('/proyectos', methods=["GET"]) #terminado
def mostrar_proyecto():
    titulo = request.args.get('titulo')
    print(titulo)
    try:
        cursor=conexion.connection.cursor()
        sql= """
        SELECT
            p.titulo,
            p.descripcion,
            p.url_deploy,
            p.url_repository,
            p.estado,
            p.usuario_id_owner,
            GROUP_CONCAT(DISTINCT up.usuario_id SEPARATOR ',') AS creadores,
            GROUP_CONCAT(DISTINCT tp.tecnologia SEPARATOR ',') AS tecnologias
        FROM 
            proyectos p
        LEFT JOIN
            usuarios_proyecto up ON p.id = up.proyecto_id
        LEFT JOIN
            tecnologias_proyecto tp ON p.id = tp.proyecto_id
        WHERE 
            1 = 1       
            """
        parametros = []
        if titulo:
            sql += "AND titulo = %s"
            parametros.append(titulo)
        
        sql +=  "GROUP BY p.id"

        cursor.execute(sql, parametros)
        datos = cursor.fetchall()
        if datos:
            proyectos = {}
            for dato in datos:
                proyectos[dato[0]] = { "titulo" : dato[0],
                            "descripcion" : dato[1],
                            "url_deploy" : dato[2],
                            "url_repository" : dato[3],
                            "estado" : dato[4],
                            "usuario_id_owner" : dato[5],
                            "creadores_id" : dato[6],
                            "tecnologias" : dato[7]
                }

                for creador in proyectos["creadores"]:
                    print("buscar nombre y apellido por id")
                    
            return jsonify({"proyectos" : proyectos})
        else:
            return jsonify({"mensaje": "proyecto no encontrado"}), 404
    
    except Exception as ex:         
        return jsonify({"mensaje": "Error al buscar el proyecto", "error": str(ex)}), 500    
    finally:
        cursor.close()