# app/services/user_service.py

from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.config import settings

from fastapi.security import OAuth2PasswordBearer
from app.schemas.token import Token

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from app.core.database import get_db

from app.schemas.token import TokenData
from app.models.user import User as UserModel, UserRole, UserStatus 
from app.schemas.user import UserUpdate 

# Configuração para o hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_all_users(db: Session) -> list[UserModel]:
    """
    Retorna todos os usuários cadastrados no banco de dados.
    """
    return db.query(UserModel).all()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        nome_completo=user.nome_completo,
        telefone=user.telefone,
        hashed_password=hashed_password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Cria um novo token de acesso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
# O tokenUrl deve corresponder ao prefixo e ao caminho do seu endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)) -> User:
    """
    Decodifica o token, valida e retorna o usuário.
    Levanta uma exceção se o token for inválido.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenData(email=payload.get("sub"), role=payload.get("role"))

        if token_data.email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


def require_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependência que verifica se o usuário autenticado tem o status 'ativo'.
    """
    if current_user.status != UserStatus.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta precisa ser validada por um administrador para realizar esta ação."
        )
    return current_user

def require_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependência que verifica se o usuário autenticado tem o papel 'admin'.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem realizar esta ação."
        )
    return current_user

def require_collaborator_user(
    current_user: Annotated[UserModel, Depends(get_current_user)]
) -> UserModel:
    """
    Dependência que verifica se o usuário autenticado é um colaborador ativo.
    """
    if current_user.role != UserRole.COLABORADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas colaboradores podem realizar esta ação."
        )
    if current_user.status != UserStatus.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta de colaborador precisa estar ativa para realizar esta ação."
        )
    return current_user

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
async def get_current_user_or_none(token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None, db: Session = Depends(get_db)) -> User | None:
    """
    Dependência opcional: retorna o usuário se o token for válido,
    ou None se nenhum token for fornecido. Levanta exceção para tokens inválidos.
    """
    if token is None:
        return None 
    
 
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

def require_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependência que verifica se o usuário autenticado tem o status 'ativo'.
    """
    if current_user.status != UserStatus.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta precisa ser validada por um administrador para realizar esta ação."
        )
    return current_user

def require_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependência que verifica se o usuário autenticado tem o papel 'admin'.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem realizar esta ação."
        )
    return current_user

def require_collaborator_user(
    current_user: Annotated[UserModel, Depends(get_current_user)]
) -> UserModel:
    """
    Dependência que verifica se o usuário autenticado é um colaborador ativo.
    """
    if current_user.role != UserRole.COLABORADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas colaboradores podem realizar esta ação."
        )
    if current_user.status != UserStatus.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta de colaborador precisa estar ativa para realizar esta ação."
        )
    return current_user

def delete_user_by_id(db: Session, user_id: int) -> UserModel | None:
    """
    Deleta um usuário do banco de dados pelo seu ID.
    Retorna o usuário deletado ou None se não for encontrado.
    """
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def update_user(db: Session, db_user: UserModel, user_in: UserUpdate) -> UserModel:
    """Atualiza os dados de um usuário no banco de dados."""
    update_data = user_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != db_user.email:
        if get_user_by_email(db, email=update_data["email"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está sendo utilizado por outra conta."
            )

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def change_user_password(db: Session, db_user: UserModel, current_password: str, new_password: str) -> bool:
    """Verifica a senha atual e, se correta, atualiza para a nova senha."""
    if not verify_password(current_password, db_user.hashed_password):
        return False

    new_hashed_password = pwd_context.hash(new_password)
    db_user.hashed_password = new_hashed_password
    db.add(db_user)
    db.commit()
    return True

def get_active_collaborators(db: Session) -> list[UserModel]:
    """Retorna uma lista de todos os colaboradores com status 'ativo'."""
    return db.query(UserModel).filter(
        UserModel.role == UserRole.COLABORADOR,
        UserModel.status == UserStatus.ATIVO
    ).all()

