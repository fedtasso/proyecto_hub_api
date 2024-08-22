from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
import datetime
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
def generate_auth_token(user_id: int) -> str:    
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token válido por 1 hora
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verify_auth_token(token: str) -> dict:    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'status': 'error', 'message': 'Token expirado'}, 401        
    except jwt.InvalidTokenError:
        return {'status': 'error', 'message': 'Token inválido'}, 401
    
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
        result = verify_auth_token(token)
        if result.get('status') == 'error':
            return jsonify({"mensaje": result.get('message')}), 401        
        return f(*args, **kwargs)
    return decorator