import uvicorn
from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel
from typing import Tuple, Union
from fastapi.staticfiles import StaticFiles
import os
import uuid
import db

import bcrypt

# from config import config


app = FastAPI()


session_max_age_sec = 28800


# 静的ファイルを提供するディレクトリのパス
static_dir = os.path.join(os.path.dirname(__file__), "static")


# ディレクトリが存在するか確認
if not os.path.isdir(static_dir):
    raise RuntimeError(f"Directory '{static_dir}' does not exist")


class LoginParam(BaseModel):
    login_id: str = Query(..., min_length=8, max_length=64)
    password: str = Query(..., min_length=8, max_length=64)


class CreateUserParam(BaseModel):
    login_id: str = Query(..., min_length=8, max_length=64)
    password: str = Query(..., min_length=8, max_length=64)
    user_name: str = Query(..., min_length=2, max_length=64)


def create_password_hash(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def _set_cookie(response: Response, session_key: str) -> None:
    response.set_cookie(
        key="todo_session_key",
        value=str(session_key),
        max_age=int(session_max_age_sec),
    )


def check_login(login_param: LoginParam) -> Tuple[bool, Union[str, None]]:
    db_password: Union[str, None] = None

    db_password = db.get_user_password(login_param.login_id)

    print(db_password)

    # ログインID不一致
    if db_password is None:
        return False, None

    # パスワード不一致
    if verify_password(login_param.password, db_password) is False:
        return False, None
    print("create_password_hash", create_password_hash(login_param.password))

    # 認証成功
    # セッションCookieの払い出し
    session_key = str(uuid.uuid4())

    return True, session_key


def create_new_user(login_id: str, password: str, user_name: str) -> bool:
    return db.create_user(login_id, create_password_hash(password), user_name)


@app.get("/hello")
def hello():
    return {"status": "SUCCESS", "msg": "Hello, World!"}


@app.post("/login")
def login(login_param: LoginParam, response: Response):
    result, session_key = check_login(login_param)

    print("result", result)
    print("session_key", session_key)
    # 認証エラー
    if result is False:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        # _reset_cookie(response)
        print(response)
        return {"status": "FAILURE", "msg": "Unauthorized"}

    # Cookieにセッションキーを付加してユーザ情報を返却
    _set_cookie(response, str(session_key))
    return {"status": "SUCCESS", "id": login_param.login_id}


@app.post("/createUser")
async def create_user(
    create_user_param: CreateUserParam,
):
    response = Response()

    # ユーザ追加(すでに存在していればエラー)
    if (
        create_new_user(
            create_user_param.login_id,
            create_user_param.password,
            create_user_param.user_name,
        )
        is False
    ):
        response.status_code = status.HTTP_409_CONFLICT
        return response

    response.status_code = status.HTTP_204_NO_CONTENT
    return response


app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5999, reload=True)
