from flask import Flask, session
from flask_mysqldb import MySQL 
from security import hash_password
from config import config
from flask_mail import Mail
from flask_cors import CORS

from endpoints.club_hub.auth import routes as auth
from endpoints.club_hub.usuario import routes as usuario
from endpoints.club_hub.participantes import routes as participantes

app=Flask(__name__)
CORS(app)

admin_existe = None
conexion = MySQL(app)
mail = Mail(app)

#cargar configuraciones
app.config.from_object(config["development"])

#cargar endpoints
app.register_blueprint(participantes.create_blueprint(conexion))
app.register_blueprint(auth.create_blueprint(conexion))
app.register_blueprint(usuario.create_blueprint(conexion,mail))


#funcion autoejecutable
def crear_admin():
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        
        nombre = "usuario"
        apellido = "administrador"
        email = "admin@gmail.com"
        password = "clubdedesarroladores"


        hashed_password = hash_password(password)
        
        cursor.execute("SELECT id FROM usuarios WHERE id = %s", (1,))
        admin_existe = cursor.fetchone()

        if admin_existe:
            return {"mensaje": "el administrador existe"}
        
        else:        
            # Insertar en tabla usuarios
            sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (nombre, apellido, email, hashed_password))
            usuario_id = cursor.lastrowid      
            
            # insetar en tabla roles rol admin
            rol_id = 1         
            cursor.execute("INSERT INTO roles_usuarios (usuario_id, rol_id) VALUES (%s, %s)", (usuario_id, rol_id))
            
            conexion.connection.commit()
            return {"mensaje": "administrador registrado con exito", "id": usuario_id},200    
      
    except Exception as ex: 
        conexion.connection.rollback()
        return {"mensaje": "Error al registrar el usuario", "error": str(ex)}, 500    
    finally:
        cursor.close()

@app.before_request
def setup():

    global admin_existe # buscar alternativa para no usar gloval   
    if admin_existe == False: 
        resultado = crear_admin()
        admin_existe = True
        print(resultado)
    
def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404

if __name__=='__main__':
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run(host="192.168.100.138", port=8001)
    


