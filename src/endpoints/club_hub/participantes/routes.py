from flask import jsonify, request,  Blueprint

def create_blueprint(conexion):
    participantes_bp = Blueprint('participantes', __name__)


    # -----------------------------------------------------------------
    # ----------  obtener datos de todos los participantes ------------
    # -----------------------------------------------------------------
    
    @participantes_bp.route('/usuarios', methods=["GET"])
    def mostrar_participantes():
        nombre = request.args.get('nombre')
        apellido = request.args.get('apellido')
        
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
                WHERE 1=1
                """
            #agregar nombre y apellido a la consulta sql
            parametros = []
            if nombre:
                sql += "AND nombre = %s"
                parametros.append(nombre)
            if apellido:
                sql += "AND apellido = %s"
                parametros.append(apellido)        
            # ejecutar consulta
            cursor.execute(sql, parametros)
            datos = cursor.fetchall()  
            
            if datos:
                usuarios_dict = {}        
                for user in datos:
                    # verficar rol para mostrar
                    if user[8] == 1:
                        rol = "admin"
                    else:
                        rol = "usuario"
                    user_id = user[0]
                    if user_id == 1:
                        continue            
                    if user_id not in usuarios_dict:
                        usuarios_dict[user_id] = {
                            "id": user_id,
                            "nombre": user[1],
                            "apellido": user[2],
                            "email": user[3],                        
                            "informacion": user[4],
                            "image": user[5],
                            "perfiles": [], 
                            "tecnologias": [],
                            "rol": rol, 
                            "github":user[9]
                    }            
                    if user[6] is not None and user[6] not in usuarios_dict[user_id]["perfiles"]:
                        usuarios_dict[user_id]["perfiles"].append(user[6])
                    if user[7] is not None and user[7] not in usuarios_dict[user_id]["tecnologias"]:
                        usuarios_dict[user_id]["tecnologias"].append(user[7])        
                usuarios = list(usuarios_dict.values())       
                return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"}), 200
            else:
                return jsonify({"mensaje": "Usuario no encontrado"}), 404
        except Exception as ex:    
            return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500    
        finally:
            cursor.close()
    
    return participantes_bp
