from typing import Optional
import os
import json


# dbディレクトリのパス
db_dir = os.path.join(os.path.dirname(__file__), "db")
users_file_path = os.path.join(db_dir, "users.json")


def get_user_db():
    # json.load関数を使ったjsonファイルの読み込み
    with open(users_file_path) as f:
        db = json.load(f)

    users = db["users"]

    return users


def get_user_password(login_id: str) -> Optional[str]:
    """
    パスワード情報をDBから取得する
    """
    # json.load関数を使ったjsonファイルの読み込み
    with open(users_file_path) as f:
        db = json.load(f)

    users = db["users"]
    print("ユーザー情報", users)

    for user in users:
        if user["id"] == login_id:
            return user["password"]

    return None


def create_user(login_id: str, password: str, user_name: str) -> bool:
    users = get_user_db()

    # # json.load関数を使ったjsonファイルの読み込み
    # with open(users_file_path) as f:
    #     db = json.load(f)

    # users = db["users"]
    print("usersだよ", users)

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
