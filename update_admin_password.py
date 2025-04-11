import os
import psycopg2
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:postgres@localhost:5432/postgres')
ADMIN_USERNAME = "tradeporu"
ADMIN_PASSWORD = "X12345x"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    return psycopg2.connect(DB_URL)

def update_admin_password():
    password_hash = hash_password(ADMIN_PASSWORD)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Обновляем пароль для всех администраторов
                cur.execute("""
                    UPDATE users
                    SET password_hash = %s
                    WHERE is_admin = TRUE
                    RETURNING user_id, username
                """, (password_hash,))
                conn.commit()
                updated_users = cur.fetchall()
                
                logger.info(f"Обновлено администраторов: {len(updated_users)}")
                for user in updated_users:
                    logger.info(f"Обновлен пользователь: ID {user[0]}, username: {user[1]}")
                
                # Проверяем, существует ли администратор
                cur.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE username = %s AND is_admin = TRUE
                """, (ADMIN_USERNAME,))
                admin_count = cur.fetchone()[0]
                
                return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении пароля администратора: {e}")
        return False

if __name__ == "__main__":
    logger.info("Начало обновления пароля администратора...")
    success = update_admin_password()
    if success:
        logger.info(f"Пароль администратора успешно обновлен. Хеш: {hash_password(ADMIN_PASSWORD)}")
    else:
        logger.error("Ошибка при обновлении пароля администратора.")