from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify


SECRET_KEY = 'Pedr@Pic4piedr4as' # usar Servicios de Gestión de Secretos en el despliege  o Uso de Variables de Entorno con el modulo current_app de Flask

ph = PasswordHasher()

# ------------  hash de pass ------------  
def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    try:
        ph.verify(hash, password)        
        return True
    
    except VerifyMismatchError:
        return False


# ------------  Generar y verificar token  ------------   
def generate_auth_token(id_user: str, role: int) -> str:    
    payload = {
        'id_user': id_user,
        'role': role, 
        'exp': datetime.now(timezone.utc) + timedelta(hours=2)  # Token válido por 1 hora
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')    
    return token

def verify_auth_token(token: str) -> dict:    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return {'status': 'success', 'data': payload}
    
    except jwt.ExpiredSignatureError:
        return {'status': 'error', 'message': 'Token expirado'}        
    
    except jwt.InvalidTokenError:
        return {'status': 'error', 'message': 'Token inválido'}
    
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header is None:
            return jsonify({"mensaje": "Token no proporcionado"}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({"mensaje": "Formato del token inválido"}), 401

        token = parts[1]
        token_verify = verify_auth_token(token)         
        if token_verify.get('status') == 'error':
            return jsonify({"mensaje": token_verify.get('message')}), 401   
        
        data = token_verify.get('data')   
        id_user = data.get('id_user')
        role = data.get('role') 

        return f(id_user, role, *args, **kwargs)
    return decorator


def token_id_recuperar_password(id_user: str) -> str:    
    payload = {
        'id_user': id_user,        
        'exp': datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')    
    return token


# ------------  Borrar  ------------   

def admin_can_modify(role_token: int) -> bool:  
    if role_token == 1:
        return True       
        

