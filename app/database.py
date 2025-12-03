import sqlite3
import threading

DATABASE_URL = "file_metadata.db"

# 使用线程锁来确保多线程环境下的数据库访问安全
db_lock = threading.Lock()

def get_db_connection():
    """获取数据库连接。"""
    conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库，创建表。"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_id TEXT NOT NULL UNIQUE,
                    filesize INTEGER NOT NULL,
                    description TEXT DEFAULT '',
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # 兼容旧数据库：添加 description 列（如果不存在）
            cursor.execute("PRAGMA table_info(files)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'description' not in columns:
                cursor.execute("ALTER TABLE files ADD COLUMN description TEXT DEFAULT ''")
            conn.commit()
            print("数据库已成功初始化。")
        finally:
            conn.close()

def add_file_metadata(filename: str, file_id: str, filesize: int, description: str = ""):
    """
    向数据库中添加一个新的文件元数据记录。
    如果 file_id 已存在，则忽略。
    """
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO files (filename, file_id, filesize, description) VALUES (?, ?, ?, ?)",
                (filename, file_id, filesize, description)
            )
            conn.commit()
            print(f"已添加或忽略文件元数据: {filename}")
        finally:
            conn.close()

def get_all_files():
    """从数据库中获取所有文件的元数据。"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT filename, file_id, filesize, description, upload_date FROM files ORDER BY upload_date DESC")
            files = [dict(row) for row in cursor.fetchall()]
            return files
        finally:
            conn.close()

def get_file_by_id(file_id: str):
    """通过 file_id 从数据库中获取单个文件元数据。"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT filename, filesize, description FROM files WHERE file_id = ?", (file_id,))
            result = cursor.fetchone()
            if result:
                return {"filename": result[0], "filesize": result[1], "description": result[2] or ""}
            return None
        finally:
            conn.close()

def delete_file_metadata(file_id: str) -> bool:
    """
    根据 file_id 从数据库中删除文件元数据。
    返回: 如果成功删除了一行，则为 True，否则为 False。
    """
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            conn.commit()
            # cursor.rowcount 会返回受影响的行数
            return cursor.rowcount > 0
        finally:
            conn.close()

def delete_file_by_message_id(message_id: int) -> str | None:
    """
    根据 message_id 从数据库中删除文件元数据，并返回其 file_id。
    因为一个消息ID只对应一个文件，所以我们可以这样做。
    """
    file_id_to_delete = None
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # 首先，根据 message_id 找到对应的 file_id
            # 我们使用 LIKE 操作符，因为 file_id 是 "message_id:actual_file_id" 的格式
            cursor.execute("SELECT file_id FROM files WHERE file_id LIKE ?", (f"{message_id}:%",))
            result = cursor.fetchone()
            if result:
                file_id_to_delete = result[0]
                # 然后，删除这条记录
                cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id_to_delete,))
                conn.commit()
                print(f"已从数据库中删除与消息ID {message_id} 关联的文件: {file_id_to_delete}")
            return file_id_to_delete
        finally:
            conn.close()

def update_file_description(file_id: str, description: str) -> bool:
    """更新文件的描述。"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE files SET description = ? WHERE file_id = ?", (description, file_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def update_description_by_message_id(message_id: int, description: str) -> str | None:
    """根据 message_id 更新描述，返回 file_id。"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT file_id FROM files WHERE file_id LIKE ?", (f"{message_id}:%",))
            result = cursor.fetchone()
            if result:
                file_id = result[0]
                cursor.execute("UPDATE files SET description = ? WHERE file_id = ?", (description, file_id))
                conn.commit()
                return file_id
            return None
        finally:
            conn.close()
