from flask import jsonify, request, Blueprint
from security import hash_password, verify_password, generate_auth_token, verify_auth_token_with_jwt, token_id_recuperar_password, security_blueprint
from validaciones import *
from flask_mail import Message

def create_blueprint(conexion,mail):
    # Defining a blueprint
    auth_bp = Blueprint('auth', __name__)

    security_bp = security_blueprint(conexion)
    auth_bp.register_blueprint(security_bp)

    
    # -----------------------------------------------------------------
    # ---------------------------  login ------------------------------
    # -----------------------------------------------------------------
    @auth_bp.route('/login', methods=["POST"]) 
    def login():
        email = request.form.get('email')
        user_pass_front = request.form.get('password')

        
        contraseña_invalida = False # hacer funcion para verificar contraseña
        email_invalido = validar_email(email, "email")
        
        if email_invalido or contraseña_invalida:
            return jsonify (email_invalido)

        try:
            cursor = conexion.connection.cursor()
            sql = """SELECT 
                        u.id, 
                        u.nombre,
                        u.apellido, 
                        u.password,
                        i.image,
                        ru.rol_id                     
                    FROM 
                        usuarios u
                    LEFT JOIN 
                        informacion i ON u.id = i.usuario_id
                    LEFT JOIN 
                        roles_usuarios ru ON u.id = ru.usuario_id
                    WHERE 
                        email = %s                
                """  
            cursor.execute(sql,(email,))
            usuario = cursor.fetchone() 
           
            if usuario is None:
                return jsonify({"mensaje":"El usuario no se encuentra registrado"}), 409
            
            user_pass_bbdd = usuario[3]
           
            if usuario and verify_password(user_pass_bbdd, user_pass_front):    
                id_user = usuario[0]
                rol = usuario[5]
                token = "Bearer " + generate_auth_token(id_user, rol)
                
                # insertar token en tabla sesion
                cursor.execute ("INSERT INTO sesiones (usuario_id, token_sesion) VALUES (%s, %s)", (id_user, token))
                conexion.connection.commit()     

                return jsonify({"mensaje": "login exitoso", 
                                "token":  token,
                                "datos": {
                                    "nombre" : usuario[1],
                                    "apellido" : usuario[2], 
                                    "imagenBase64" : usuario[4]                          
                                }}), 200            
            else:
                return jsonify({"mensaje": "contraseña inválida"}), 401  
                       

        except Exception as ex:
            return jsonify({"mensaje": "Error al loguear el usuario", "error": str(ex)}), 500  
        
        finally:
            cursor.close()


    # -----------------------------------------------------------------
    # -----------------------------  sign out -------------------------
    # -----------------------------------------------------------------
    @auth_bp.route('/sign_out', methods=["DELETE"])
    @security_bp.token_required
    def sign_out(id_token, role_token):
        token = request.form.get('token')
        try:
            cursor = conexion.connection.cursor()

            cursor.execute("DELETE FROM sesiones WHERE token_sesion = %s",(token,))
            
            conexion.connection.commit()

            if cursor.rowcount > 0:
                return jsonify({"mensaje": "deslogueo exitoso"})
            else:
                return jsonify({"mensaje": "token no encontrado"})
        
        except Exception as ex:
            return jsonify({"mensaje": "Error al desloguear el usuario", "error": str(ex)}), 500  
        
        finally:
            cursor.close()


        
    # -----------------------------------------------------------------
    # -------------------------  crear usuario ------------------------
    # -----------------------------------------------------------------
    @auth_bp.route('/registrar', methods=["POST"]) 
    def registrar():   
        
        
        nombre = request.form.get('nombre') 
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        password = request.form.get('password')
        github = request.form.get('github')
        informacion_adicional = request.form.get('informacion_adicional')
        imagenBase64 = request.form.get('image')
        perfiles = request.form.get('perfiles')
        tecnologias = request.form.get('tecnologias') 


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
            else:
                return jsonify ({"mensaje": " el nombre es requerido"})
            
            if apellido:
                validaciones["apellido"] = (validar_alpha, apellido, "apellido")
            else:
                return jsonify ({"mensaje": " el apellido es requerido"})

            if email:
                validaciones["email"] = (validar_y_verificar_email, email, "email", cursor)
            else:
                return jsonify ({"mensaje": " el email es requerido"})
            
            
            if password:
                print("falta validar password")
            else:
                return jsonify ({"mensaje": " la contraseña es requerida"})

            if informacion_adicional:
                validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")

            if perfiles:
                validaciones["perfiles"] = (validar_comma_en_list, perfiles, "perfiles")
            
            if tecnologias:
                validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")

            resultado_validacion = validar_datos_generica(cursor, validaciones)        
            if resultado_validacion:
                return jsonify(resultado_validacion), 400
        
        
            # Hacer hash de contraseña
            hashed_password = hash_password(password)
        
            # Insertar en tabla usuarios
            sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (nombre, apellido, email, hashed_password))
            usuario_id = cursor.lastrowid
        
            # insertar en tabla informacion (me aseguro que usuario e informacion tengan el mismo id)       
            sql = "INSERT INTO informacion (usuario_id, informacion_adicional, image, url_github) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (usuario_id,informacion_adicional,imagenBase64,github))
            
            # insetar en tabla perfiles
            for perfil in perfiles:
                sql = "INSERT INTO perfiles (usuario_id, perfil) VALUES(%s, %s)"
                cursor.execute(sql,(usuario_id,perfil))

            # insertar en tabla tecnologias
            for tecnologia in tecnologias:
                cursor.execute("INSERT INTO tecnologias (usuario_id, tecnologia) VALUES (%s, %s)", (usuario_id, tecnologia))
            
            # insetar en tabla roles
            rol_id = 2 # usuario por defecto
            cursor.execute("INSERT INTO roles_usuarios (usuario_id, rol_id) VALUES (%s, %s)", (usuario_id, rol_id))
                    
            token = "Bearer " + generate_auth_token(usuario_id, rol_id)
            
            # insertar token en tabla sesion
            cursor.execute ("INSERT INTO sesiones (usuario_id, token_sesion) VALUES (%s, %s)", (usuario_id, token))
            
            
            conexion.connection.commit() 
            response = jsonify({
                "mensaje": "Usuario registrado",
                "token":  token,
                }),200 
            return response
        
        except Exception as ex: 
            conexion.connection.rollback()
            return jsonify({"mensaje": "Error al registrar el usuario", "error": str(ex)}), 500  
        
        finally:
            cursor.close()

    # -----------------------------------------------------------------
    # ----------------------  actualizar password---- -----------------
    # -----------------------------------------------------------------    
    @auth_bp.route('/actualizar_password', methods=["PUT"]) # el user admin para cambiar su password debe enviar el id 1
    @security_bp.token_required
    def actualizar_password(id_token, role_token):

        password = request.form.get("password")
        user_id_by_admin = request.form.get("id")
        try:
            cursor = conexion.connection.cursor()
            
            #verificar si es admin o user               
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token, cursor)
            if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
            else:
                id_user = validated_user_id["id"]
            
            if password:

                #falta validar password
            
                #seleccionar pass de bbdd
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



    # -----------------------------------------------------------------
    # -----------------------  recuperar password ---------------------
    # ------------------------------paso 1 ----------------------------    
    @auth_bp.route('/recuperar_contra/validacion', methods=["POST"]) #TO DO ver nombres acordados con Bauti
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
                cursor.execute("INSERT INTO recuperar_password(usuario_id, token_recuperar) VALUES (%s, %s)",(usuario_id, token_id))

                #crear mensaje
                msg = Message ("Recuperar contraseña",                  
                recipients=[f"{email}"],
                body = f"""
    Nos comunicamos desde el Club de Desarrolladores de Vicente López.
                
    Para recuperar su contraseña acceda al siguiente link:

    http://127.0.0.1:5000/recuperar_password/actualizar?token_id={token_id}

    Por favor, siga las instrucciones en la página para restablecer su contraseña.

    Este es un correo automático, por favor no responda.
                """)
                # Enviar correo

                mail.send(msg) 

                conexion.connection.commit()

                return jsonify({"mensaje" : "email enviado con exito"}), 200
                
            else:
                return jsonify({"mensaje":"debe proporcionar un email"}), 400
            
        except Exception as e:
            return jsonify({"mensaje":"Error al enviar el correo", "error": str(e)},500)
        
        finally:
            cursor.close()




    # -----------------------------------------------------------------
    # -----------------------  recuperar password ---------------------
    # ------------------------------paso 2 ----------------------------    
    @auth_bp.route('/recuperar_contra/validacion', methods=["PUT"])
    def restablecer_password():

        token_id = request.args.get('token_id')
        password = request.form.get('password')
    
        if not token_id or not password:
            return jsonify({"mensaje" : "formato de recuperación incorrecto"}), 400
        
        token_valido = verify_auth_token_with_jwt(token_id)
                    
        if token_valido["status"] == "error":
            return jsonify ({"mensaje" : "Error! Token invalido."}), 400
        
        # falta validar password
        print("--------------------------------------------------------",token_id, password) 
        try:   
            cursor = conexion.connection.cursor()

            usuario_id = token_valido["data"]["id_user"]

            hashed_password = hash_password(password) 

            #verificar si token fue usado
            cursor.execute("SELECT usado FROM recuperar_password WHERE token_recuperar = %s", (token_id,))
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



    return auth_bp
