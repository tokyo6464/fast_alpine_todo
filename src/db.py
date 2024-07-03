from typing import Optional, Tuple, Literal, List
from pydantic import BaseModel
import os
import json
from datetime import datetime

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


class TaskInfoResponse(BaseModel):
    login_id: str
    update_time: str


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


def get_login_id_by_session_key(
    session_key: str,
) -> Optional[str]:
    """
    セッションキーからログインIDを取得する
    """
    # json.load関数を使ったjsonファイルの読み込み
    with open(users_file_path) as f:
        db = json.load(f)

    users = db["users"]

    for user in users:
        if user["session_value"] == session_key:
            return user["id"]

    return None


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
    login_id: Optional[str] = None

    # ログインIDが存在しているかをチェック
    for user in users:
        if user["session_value"] == session_login_id:
            login_id = user["id"]
            break

    # ログインIDに紐づくタスクが存在しているかをチェック
    for task in tasks:
        if task["login_id"] == login_id:
            return task

    return None


def create_task(login_id: str, content: str) -> Optional[TaskInfoResponse]:
    tasks = get_data_from_db("tasks")
    # 編集対象のタスク情報
    target_task_info = None
    target_task_info_index = None

    # ログインIDに紐づくタスクが存在しているかをチェック

    for index, task in enumerate(tasks):
        print("task", task)
        if task["login_id"] == login_id:
            target_task_info = task
            target_task_info_index = index
            break  # タスクが見つかったらループを抜ける

    target_task_list = []
    # 既に紐づくタスク情報が存在する場合はタスク情報を設定
    if target_task_info is not None:
        target_task_list = target_task_info["task_list"]

    new_id: int = 1

    # 最後の要素のid + 1を新規タスクのidとする
    if not target_task_list:  # リストが空の場合
        pass
    else:
        new_id = target_task_list[-1]["id"] + 1  # 最後の要素のid + 1

    new_task = {
        "id": new_id,
        "content": content,
        "done_flg": "0",
    }

    target_task_list.append(new_task)

    # 現在の日時を取得
    now = datetime.now()
    # フォーマット
    formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")

    new_target_task_info = {
        "login_id": login_id,
        "task_list": target_task_list if content != "" else [],
        "update_time": formatted_date_time,
    }

    if target_task_info_index is not None:
        tasks[target_task_info_index] = new_target_task_info
    else:
        # 新規ユーザー登録時は最後尾にタスク情報を設定
        tasks.append(new_target_task_info)

    # 更新されたデータをJSON形式に変換
    updated_json = json.dumps({"tasks": tasks}, indent=4)
    # JSONファイルに更新データを書き込む
    with open(tasks_file_path, "w") as file:
        file.write(updated_json)

    return {
        "login_id": login_id,
        "update_time": formatted_date_time,
    }
