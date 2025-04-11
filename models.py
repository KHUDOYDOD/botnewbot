import os
import psycopg2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:postgres@localhost:5432/postgres')

# Константы для администратора
ADMIN_USERNAME = "tradeporu"
ADMIN_PASSWORD_HASH = "b1f0fdf375c6398ee7180b6210152a054bd2020d10a6846594b897de622e13c7"  # Хеш для пароля X12345x

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    password_hash VARCHAR(255),
                    language_code VARCHAR(10) DEFAULT 'tg',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

def add_user(user_id: int, username: str = "", is_admin: bool = False):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, username, is_admin)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET username = EXCLUDED.username
                    RETURNING user_id
                """, (user_id, username or "", is_admin))
                conn.commit()
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return None

def approve_user(user_id: int, password_hash: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET is_approved = TRUE, password_hash = %s
                    WHERE user_id = %s
                    RETURNING user_id
                """, (password_hash, user_id))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error approving user: {e}")
        return False

def get_user(user_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, is_admin, is_approved, password_hash, language_code
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'is_admin': result[2],
                        'is_approved': result[3],
                        'password_hash': result[4],
                        'language_code': result[5]
                    }
                return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def update_user_language(user_id: int, language_code: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET language_code = %s
                    WHERE user_id = %s
                    RETURNING user_id, language_code
                """, (language_code, user_id))
                conn.commit()
                result = cur.fetchone()
                return result is not None
    except Exception as e:
        logger.error(f"Error updating user language: {e}")
        return False

def get_user_language(user_id: int) -> str:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT language_code
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                return result[0] if result else 'tg'
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return 'tg'

def verify_user_password(user_id: int, password_hash: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM users
                    WHERE user_id = %s AND password_hash = %s AND is_approved = TRUE
                """, (user_id, password_hash))
                result = cur.fetchone()
                if result is None:
                    return False
                count = result[0]
                return count > 0
    except Exception as e:
        logger.error(f"Error verifying user password: {e}")
        return False

def get_all_users():
    """Получить всех пользователей из базы данных."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, is_admin, is_approved, created_at
                    FROM users
                    ORDER BY created_at DESC
                """)
                users = []
                for row in cur.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'is_admin': row[2],
                        'is_approved': row[3],
                        'created_at': row[4]
                    })
                return users
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

def get_pending_users():
    """Получить всех пользователей, ожидающих одобрения."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, created_at
                    FROM users
                    WHERE is_approved = FALSE AND is_admin = FALSE
                    ORDER BY created_at DESC
                """)
                users = []
                for row in cur.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'created_at': row[2]
                    })
                return users
    except Exception as e:
        logger.error(f"Error getting pending users: {e}")
        return []

def delete_user(user_id: int):
    """Удалить пользователя из базы данных."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM users
                    WHERE user_id = %s AND is_admin = FALSE
                    RETURNING user_id
                """, (user_id,))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False

def set_user_admin_status(user_id: int, is_admin: bool):
    """Установить статус администратора для пользователя."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET is_admin = %s
                    WHERE user_id = %s
                    RETURNING user_id
                """, (is_admin, user_id))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error setting admin status: {e}")
        return False

def create_admin_user(user_id: int, username: str):
    """Создать админа с предустановленным паролем."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, username, is_admin, is_approved, password_hash)
                    VALUES (%s, %s, TRUE, TRUE, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET username = EXCLUDED.username, 
                        is_admin = TRUE, 
                        is_approved = TRUE,
                        password_hash = EXCLUDED.password_hash
                    RETURNING user_id
                """, (user_id, username, ADMIN_PASSWORD_HASH))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return False

# Initialize database tables
init_db()