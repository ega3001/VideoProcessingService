from datetime import datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError

from api.exceptions import credentials_exception, tokenExpired_exception
from core.config import Config


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def create_access_token(data: dict, email=False):
    if not email:
        access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        access_token_expires = timedelta(minutes=Config.EMAIL_CODE_EXPIRE_MINUTES)

    to_encode = data.copy()

    expire = datetime.utcnow() + access_token_expires

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        email: str = payload.get("email")
        aim: str = payload.get("aim")
        if email is None or aim is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise tokenExpired_exception
    except JWTError:
        raise credentials_exception

    return email, aim

def create_share_token(data: dict) -> str:
    encode = data.copy()

    expire = datetime.utcnow() + timedelta(weeks=Config.SHARE_TOKEN_EXPIRE_WEEK)
    encode.update({"exp": expire})

    return jwt.encode(encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

def decode_share_token(token: str):
    try:
        data = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        aim: str = data.get("aim")
        id: str = data.get("prj_id")

        if aim is None or id is None:
            raise credentials_exception
    
    except ExpiredSignatureError:
        raise tokenExpired_exception
    except JWTError:
        raise credentials_exception
    
    return id, aim

def create_cent_token(data: dict) -> str:
    encode = data.copy()
    encode.update({"exp": datetime.utcnow() + timedelta(weeks=Config.SHARE_TOKEN_EXPIRE_WEEK)})

    return jwt.encode(encode, Config.CENTRIFUGO_TOKEN_HMAC_SECRET_KEY, algorithm=Config.ALGORITHM)