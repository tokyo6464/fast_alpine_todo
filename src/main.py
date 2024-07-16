import uvicorn
from fastapi import FastAPI, Query, Request, Response, status, Cookie, Path
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Tuple, Union, Literal, Optional, Dict, Any
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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


class CreateTaskParam(BaseModel):
    content: str


class UpdateContentParam(BaseModel):
    content: str
    done_flg: Literal["0", "1"]


# TODO Cookieの有効期限の再設定
# new テンプレート関連の設定 (jinja2)
templates = Jinja2Templates(directory=static_dir)
jinja_env = templates.env  # Jinja2.Environment : filterやglobalの設定用


def create_password_hash(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def _set_cookie(response: Response, session_key: str) -> None:
    response.set_cookie(
        key="todo_session_key",
        value=str(session_key),
        max_age=int(session_max_age_sec),
        httponly=True,
        # httponly=True,  # JavaScriptからアクセスできないようにする
    )


def _reset_cookie(response: Response) -> None:
    response.set_cookie(key="shuttle_session_key", value="", max_age=0)


def get_login_id_by_cookie(session_key: str) -> Optional[str]:
    return db.get_login_id_by_session_key(session_key)


def check_login(
    login_param: LoginParam,
) -> Tuple[bool, Union[str, None], Union[str, None]]:
    db_password: Union[str, None] = None
    db_user_name: Union[str, None] = None

    db_password, db_user_name = db.get_user_password_name(
        login_param.login_id
    )

    # ログインID不一致
    if db_password is None:
        return False, None, None

    # パスワード不一致
    if verify_password(login_param.password, db_password) is False:
        return False, None, None

    # 認証成功
    # セッションCookieの払い出し
    session_key = str(uuid.uuid4())

    # DBへのセッションCookieの設定
    db.update_login_info(login_param.login_id, session_key)

    return True, db_user_name, session_key


def get_user_info_by_session_key(
    session_key: str,
) -> Optional[Dict[str, Any]]:
    login_id, user_name = db.get_user_info_by_session_key(session_key)
    if login_id is None:
        return None

    return {
        "login_id": login_id,
        "user_name": user_name,
    }


def create_new_user(login_id: str, password: str, user_name: str) -> bool:
    return db.create_user(
        login_id, create_password_hash(password), user_name
    )


@app.post("/login")
def login(login_param: LoginParam):
    response = Response()
    result, user_name, session_key = check_login(login_param)

    # 認証エラー
    if result is False:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        _reset_cookie(response)
        return response

    # Cookieにセッションキーを付加してユーザ情報を返却
    response = JSONResponse(
        content={"id": login_param.login_id, "name": user_name}
    )

    # Cookieにセッションキーを付加してユーザ情報を返却
    _set_cookie(response, str(session_key))
    return response


@app.get("/myself")
def get_myself(todo_session_key: Optional[str] = Cookie(None)):
    response = Response()

    if todo_session_key is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    myself = get_user_info_by_session_key(str(todo_session_key))

    if myself is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    return myself


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

    # ユーザーに紐づく初期状態のタスク情報を作成
    db.create_task(create_user_param.login_id, "")
    return {
        "id": create_user_param.login_id,
        "name": create_user_param.user_name,
    }


@app.get("/tasks")
async def get_tasks(todo_session_key: Optional[str] = Cookie(None)):
    """
    login_idに紐づくタスクをDBから全件取得する
    """
    result = db.get_tasks_info_by_user_id(todo_session_key)
    if result:
        return result
    else:
        return {
            "tasks": [],
            "update_time": "",
        }


@app.post("/tasks")
async def create_task(
    new_task: CreateTaskParam, todo_session_key: Optional[str] = Cookie(None)
):
    response = Response()

    # セッションチェック/権限チェック
    if todo_session_key is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    login_id = get_login_id_by_cookie(todo_session_key)

    # 登録したデータのid, 更新日時
    result = db.create_task(login_id, new_task.content)

    return result


@app.put("/tasks/{task_id}")
async def update_task(
    upd_param: UpdateContentParam,
    task_id: int = Path(title="The ID of the item to Update"),
    todo_session_key: Optional[str] = Cookie(None),
):
    response = Response()

    # セッションチェック/権限チェック
    if todo_session_key is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    login_id = get_login_id_by_cookie(todo_session_key)

    # 更新したデータのid, 更新日時
    result = db.update_task(login_id, task_id, upd_param)

    return result


@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int = Path(title="The ID of the item to Delete"),
    todo_session_key: Optional[str] = Cookie(None),
):
    response = Response()

    # セッションチェック/権限チェック
    if todo_session_key is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    login_id = get_login_id_by_cookie(todo_session_key)

    # 削除したデータのid, 更新日時
    result = db.delete_task(login_id, task_id)

    return result


@app.get("/signup", response_class=HTMLResponse)
async def read_sign_up(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("signUp.html", context)


@app.get("/todos", response_class=HTMLResponse)
async def read_todos(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("todos.html", context)


app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5999, reload=True)
