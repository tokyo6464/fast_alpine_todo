from typing import Optional, Tuple, Literal, List
from pydantic import BaseModel
from datetime import datetime
from main import UpdateContentParam
import mysql.connector


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
    task_id: str
    update_time: str


def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",  # 接続情報は設定に合わせて変更必要
        user="your_username",
        password="your_password",
        database="task_manager",
    )


def connect_db():
    """
    データベース接続を行い、接続オブジェクトとカーソルを返す
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    return conn, cursor


def logout_user(session_key: str) -> bool:
    """
    ユーザーをログアウトする（session_valueを無効化）
    :param session_key: ログイン中のセッションキー
    :return: ログアウトが成功したかどうか（True/False）
    """
    # データベース接続
    conn, cursor = connect_db()

    # session_valueをNULLにして無効化
    query = "UPDATE users SET session_value = NULL WHERE session_value = %s"
    cursor.execute(query, (session_key,))

    # ログアウトが成功したかどうか（更新された行数が1かどうか）
    if cursor.rowcount == 1:
        conn.commit()
        success = True
    else:
        success = False

    cursor.close()
    conn.close()

    return success


def get_login_id_by_session_key(session_key: str) -> Optional[str]:
    """
    セッションキーからログインIDを取得する
    """
    conn, cursor = connect_db()
    query = "SELECT id FROM users WHERE session_value = %s"
    cursor.execute(query, (session_key,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None


def get_user_info_by_session_key(
    session_key: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    セッションキーからログインIDとユーザー名をDBから取得する
    """
    conn, cursor = connect_db()
    query = "SELECT id, name FROM users WHERE session_value = %s"
    cursor.execute(query, (session_key,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:
        return result[0], result[1]  # login_id, nameを返す
    return None, None


def get_user_password_name(
    login_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    パスワードとユーザー名をDBから取得する
    """
    conn, cursor = connect_db()
    query = "SELECT password, name FROM users WHERE id = %s"
    cursor.execute(query, (login_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:
        return result[0], result[1]
    return None, None


def update_login_info(login_id: str, session_key: str) -> None:
    """
    ログイン情報の更新
    """
    conn, cursor = connect_db()
    query = "UPDATE users SET session_value = %s WHERE id = %s"
    cursor.execute(query, (session_key, login_id))
    conn.commit()
    cursor.close()
    conn.close()


def create_user(login_id: str, password: str, user_name: str) -> bool:
    """
    新しいユーザーをデータベースに作成する関数
    成功したらTrueを返し、既にユーザーが存在している場合はFalseを返す
    """
    conn, cursor = connect_db()
    query = "INSERT INTO users (id, password, name) VALUES (%s, %s, %s)"

    try:
        cursor.execute(query, (login_id, password, user_name))  # クエリを実行
        conn.commit()  # データベースへの変更を確定
        return True
    except mysql.connector.IntegrityError:
        # 主キーの重複などのIntegrityErrorが発生した場合
        return False
    finally:
        cursor.close()  # クエリ完了後にカーソルを閉じる
        conn.close()  # DB接続を閉じる


def get_tasks_info_by_user_id(session_login_id: str) -> Optional[TaskInfo]:
    """
    ログインIDからそのユーザーのタスク一覧を取得する関数
    """
    conn = get_db_connection()
    cursor = conn.cursor(
        dictionary=True
    )  # 結果を辞書形式で取得するカーソルを使用

    # ユーザーのログインIDをDBから取得
    query = "SELECT id FROM users WHERE id = %s"
    cursor.execute(query, (session_login_id,))
    user = cursor.fetchone()  # ユーザー情報を1件取得
    print("user", user)  # デバッグ用出力
    print("session_login_id", session_login_id)  # デバッグ用出力
    print("query", query)  # デバッグ用出力

    if not user:  # ユーザーが存在しない場合
        cursor.close()
        conn.close()
        return None

    login_id = user["id"]  # ユーザーIDを取得

    # ユーザーのタスクを取得するクエリ
    query = """
    SELECT id, content, done_flg
    FROM tasks
    WHERE login_id = %s
    """
    cursor.execute(query, (login_id,))
    tasks = cursor.fetchall()  # タスク情報を全件取得

    cursor.close()
    conn.close()

    # TaskInfoオブジェクトを返す（タスク一覧を含む）
    return TaskInfo(
        login_id=login_id, task_list=[Task(**task) for task in tasks]
    )


def create_task(login_id: str, content: str) -> Optional[TaskInfoResponse]:
    """
    指定されたユーザーに対して新しいタスクを作成する関数
    """
    conn, cursor = connect_db()

    # タスクを追加するクエリ
    query = """
    INSERT INTO tasks (login_id, content, update_time)
    VALUES (%s, %s, NOW())
    """
    cursor.execute(query, (login_id, content))
    task_id = cursor.lastrowid  # 追加したタスクのIDを取得

    # 追加したタスクの更新日時を取得するクエリ
    query = "SELECT update_time FROM tasks WHERE id = %s"
    cursor.execute(query, (task_id,))
    update_time = cursor.fetchone()[0]  # 更新日時を取得

    conn.commit()  # データベースへの変更を確定
    cursor.close()
    conn.close()

    # タスク情報のレスポンスを返す
    return TaskInfoResponse(
        task_id=str(task_id),
        update_time=update_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def update_task(
    login_id: str, task_id: int, upd_param: UpdateContentParam
) -> Optional[TaskInfoResponse]:
    """
    指定されたタスクを更新する関数
    """
    conn, cursor = connect_db()

    # タスクを更新するクエリ
    query = """
    UPDATE tasks
    SET content = %s, done_flg = %s, update_time = NOW()
    WHERE id = %s AND login_id = %s
    """
    cursor.execute(
        query, (upd_param.content, upd_param.done_flg, task_id, login_id)
    )

    if cursor.rowcount == 0:
        # 更新対象のレコードが存在しない場合
        cursor.close()
        conn.close()
        return None

    # 更新後のタスクの更新日時を取得するクエリ
    query = "SELECT update_time FROM tasks WHERE id = %s"
    cursor.execute(query, (task_id,))
    update_time = cursor.fetchone()[0]  # 更新日時を取得

    conn.commit()  # データベースへの変更を確定
    cursor.close()
    conn.close()

    # 更新結果のレスポンスを返す
    return TaskInfoResponse(
        task_id=str(task_id),
        update_time=update_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def delete_task(login_id: str, task_id: int) -> Optional[TaskInfoResponse]:
    """
    指定されたタスクを削除する関数
    """
    conn, cursor = connect_db()

    # タスクを削除するクエリ
    query = "DELETE FROM tasks WHERE id = %s AND login_id = %s"
    cursor.execute(query, (task_id, login_id))

    if cursor.rowcount == 0:
        # 削除対象のレコードが存在しない場合
        cursor.close()
        conn.close()
        return None

    update_time = datetime.now()  # 現在の日時を削除時間として使用

    conn.commit()  # データベースへの変更を確定
    cursor.close()
    conn.close()

    # 削除結果のレスポンスを返す
    return TaskInfoResponse(
        task_id=str(task_id),
        update_time=update_time.strftime("%Y-%m-%d %H:%M:%S"),
    )
