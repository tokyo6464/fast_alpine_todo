from typing import Optional, Tuple, Literal, List
from pydantic import BaseModel
import os
import json


# dbディレクトリのパス
db_dir = os.path.join(os.path.dirname(__file__), "db")
users_file_path = os.path.join(db_dir, "users.json")
tasks_file_path = os.path.join(db_dir, "tasks.json")


class UserInfo(BaseModel):
    login_id: str
    password: str
    name: str
    session_value: Optional[str]


class Task(BaseModel):
    id: int
    content: str
    done_flg: Literal["0", "1"]


class TaskInfo(BaseModel):
    login_id: str
    task_list: List[Task]


def get_data_from_db(db_name: Literal["users", "tasks"]):
    db_file_path: str
    if db_name == "users":
        db_file_path = users_file_path
    if db_name == "tasks":
        db_file_path = tasks_file_path

    # json.load関数を使ったjsonファイルの読み込み
    with open(db_file_path) as f:
        db = json.load(f)

    data = db[db_name]

    return data


def get_user_info_by_session_key(
    session_key: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    セッションキーからログインIDとユーザー名をDBから取得する
    """
    # json.load関数を使ったjsonファイルの読み込み
    with open(users_file_path) as f:
        db = json.load(f)

    users = db["users"]
    print("ユーザー情報", users)

    for user in users:
        if user["session_value"] == session_key:
            return user["id"], user["name"]

    return None, None


def get_user_password_name(
    login_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    パスワードとユーザー名をDBから取得する
    """
    # json.load関数を使ったjsonファイルの読み込み
    with open(users_file_path) as f:
        db = json.load(f)

    users = db["users"]

    for user in users:
        if user["id"] == login_id:
            return user["password"], user["name"]

    return None, None


def update_login_info(login_id: str, session_key: str) -> None:
    """
    ログイン情報の更新
    """
    users = get_data_from_db("users")
    target_user_info: UserInfo
    target_index: int

    for index, user in enumerate(users):
        if user["id"] == login_id:
            target_index = index
            target_user_info = user

    updated_session_value_user = {
        "id": login_id,
        "password": target_user_info["password"],
        "name": target_user_info["name"],
        "session_value": session_key,
    }
    print("target_user_info", target_user_info)
    print("target_index", target_index)
    users[target_index] = updated_session_value_user

    # 更新されたデータをJSON形式に変換
    updated_json = json.dumps({"users": users}, indent=4)
    # JSONファイルに更新データを書き込む
    with open(users_file_path, "w") as file:
        file.write(updated_json)


def create_user(login_id: str, password: str, user_name: str) -> bool:
    users = get_data_from_db("users")

    # ログインIDが存在しているかをチェック
    for user in users:
        if user["id"] == login_id:
            return False

    # 存在していない場合は登録する
    users.append({"id": login_id, "password": password, "name": user_name})

    # 更新されたデータをJSON形式に変換
    updated_json = json.dumps({"users": users}, indent=4)
    # JSONファイルに更新データを書き込む
    with open(users_file_path, "w") as file:
        file.write(updated_json)

    return True


def get_tasks_info_by_user_id(session_login_id: str) -> Optional[TaskInfo]:
    """
    ログインIDから紐づくタスク一覧を取得する
    """
    users = get_data_from_db("users")
    tasks = get_data_from_db("tasks")
    print("tasks", tasks)
    login_id: Optional[str] = None

    # ログインIDが存在しているかをチェック
    for user in users:
        if user["session_value"] == session_login_id:
            login_id = user["id"]
            break

    print("login_id", login_id)

    # ログインIDに紐づくタスクが存在しているかをチェック
    for task in tasks:
        print("task", task)
        if task["login_id"] == login_id:
            return task

    return None
