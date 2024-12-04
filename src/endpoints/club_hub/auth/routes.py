from flask import jsonify, request, Blueprint
from security import hash_password, verify_password, generate_auth_token, security_blueprint
from validaciones import *

def create_blueprint(conexion):

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

    return auth_bp
