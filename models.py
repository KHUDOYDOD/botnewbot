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
            # Таблица пользователей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    password_hash VARCHAR(255),
                    language_code VARCHAR(10) DEFAULT 'tg',
                    is_moderator BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Проверка наличия колонки is_moderator и добавление, если её нет
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'is_moderator'
                """)
                column_exists = cur.fetchone() is not None
                
                if not column_exists:
                    cur.execute("""
                        ALTER TABLE users 
                        ADD COLUMN is_moderator BOOLEAN DEFAULT FALSE
                    """)
                    conn.commit()
                    logger.info("Added is_moderator column to users table")
            except Exception as e:
                logger.error(f"Error checking or adding is_moderator column: {e}")
            
            # Таблица для хранения валютных пар
            cur.execute("""
                CREATE TABLE IF NOT EXISTS currency_pairs (
                    id SERIAL PRIMARY KEY,
                    pair_code VARCHAR(20) UNIQUE NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для хранения текстов и сообщений
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_messages (
                    id SERIAL PRIMARY KEY,
                    message_key VARCHAR(50) NOT NULL,
                    language_code VARCHAR(10) NOT NULL,
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (message_key, language_code)
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
                # Сначала проверяем, существует ли колонка is_moderator
                try:
                    cur.execute("""
                        SELECT user_id, username, is_admin, is_approved, password_hash, language_code, is_moderator
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
                            'language_code': result[5],
                            'is_moderator': result[6]
                        }
                except Exception as column_error:
                    # Если колонка не существует, используем запрос без нее
                    if 'column "is_moderator" does not exist' in str(column_error):
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
                                'language_code': result[5],
                                'is_moderator': False  # По умолчанию не модератор
                            }
                    else:
                        # Если это другая ошибка, поднимаем ее снова
                        raise
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
                try:
                    # Пробуем запрос с is_moderator
                    cur.execute("""
                        SELECT user_id, username, is_admin, is_approved, created_at, is_moderator
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
                            'created_at': row[4],
                            'is_moderator': row[5]
                        })
                    return users
                except Exception as column_error:
                    # Если колонка не существует, используем запрос без нее
                    if 'column "is_moderator" does not exist' in str(column_error):
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
                                'created_at': row[4],
                                'is_moderator': False  # По умолчанию не модератор
                            })
                        return users
                    else:
                        # Если это другая ошибка, поднимаем ее снова
                        raise
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []
        
def get_approved_user_ids():
    """Получить ID всех подтвержденных пользователей для рассылки."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id
                    FROM users
                    WHERE is_approved = TRUE
                """)
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error getting approved user IDs: {e}")
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

def reset_user_approval(user_id: int):
    """Сбросить статус подтверждения пользователя, но оставить его в базе."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET is_approved = FALSE, password_hash = NULL
                    WHERE user_id = %s AND is_admin = FALSE
                    RETURNING user_id
                """, (user_id,))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error resetting user approval status: {e}")
        return False

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

def set_user_moderator_status(user_id: int, is_moderator: bool):
    """Установить статус модератора для пользователя."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Пробуем обновить, если колонка существует
                    cur.execute("""
                        UPDATE users
                        SET is_moderator = %s
                        WHERE user_id = %s
                        RETURNING user_id
                    """, (is_moderator, user_id))
                    conn.commit()
                    result = cur.fetchone()
                    return result is not None
                except Exception as column_error:
                    # Если колонка не существует, добавляем ее и пробуем снова
                    if 'column "is_moderator" does not exist' in str(column_error):
                        conn.rollback()  # Откатываем транзакцию перед созданием колонки
                        
                        # Добавляем колонку is_moderator
                        cur.execute("""
                            ALTER TABLE users 
                            ADD COLUMN IF NOT EXISTS is_moderator BOOLEAN DEFAULT FALSE
                        """)
                        conn.commit()
                        
                        # Теперь пробуем обновить снова
                        cur.execute("""
                            UPDATE users
                            SET is_moderator = %s
                            WHERE user_id = %s
                            RETURNING user_id
                        """, (is_moderator, user_id))
                        conn.commit()
                        result = cur.fetchone()
                        return result is not None
                    else:
                        # Если это другая ошибка, поднимаем ее снова
                        raise
    except Exception as e:
        logger.error(f"Error setting moderator status: {e}")
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

# Функции для управления валютными парами
def get_all_currency_pairs():
    """Получить все валютные пары из базы данных."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, pair_code, symbol, display_name, is_active
                    FROM currency_pairs
                    ORDER BY id
                """)
                pairs = []
                for row in cur.fetchall():
                    pairs.append({
                        'id': row[0],
                        'pair_code': row[1],
                        'symbol': row[2],
                        'display_name': row[3],
                        'is_active': row[4]
                    })
                return pairs
    except Exception as e:
        logger.error(f"Error getting currency pairs: {e}")
        return []

def add_or_update_currency_pair(pair_code: str, symbol: str, display_name: str, is_active: bool = True):
    """Добавить или обновить валютную пару."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO currency_pairs (pair_code, symbol, display_name, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pair_code) DO UPDATE
                    SET symbol = EXCLUDED.symbol,
                        display_name = EXCLUDED.display_name,
                        is_active = EXCLUDED.is_active
                    RETURNING id
                """, (pair_code, symbol, display_name, is_active))
                conn.commit()
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Error adding/updating currency pair: {e}")
        return None

def delete_currency_pair(pair_code: str):
    """Удалить валютную пару."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM currency_pairs
                    WHERE pair_code = %s
                    RETURNING id
                """, (pair_code,))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error deleting currency pair: {e}")
        return False

def update_currency_pair_status(pair_code: str, is_active: bool):
    """Обновить статус активности валютной пары."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE currency_pairs
                    SET is_active = %s
                    WHERE pair_code = %s
                    RETURNING id
                """, (is_active, pair_code))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error updating currency pair status: {e}")
        return False


# Функции для управления сообщениями бота
def get_all_bot_messages():
    """Получить все сообщения бота из базы данных."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, message_key, language_code, message_text, updated_at
                    FROM bot_messages
                    ORDER BY message_key, language_code
                """)
                messages = []
                for row in cur.fetchall():
                    messages.append({
                        'id': row[0],
                        'message_key': row[1],
                        'language_code': row[2],
                        'message_text': row[3],
                        'updated_at': row[4]
                    })
                return messages
    except Exception as e:
        logger.error(f"Error getting bot messages: {e}")
        return []

def get_message_for_key(message_key: str):
    """Получить все сообщения для указанного ключа на всех языках."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, language_code, message_text, updated_at
                    FROM bot_messages
                    WHERE message_key = %s
                    ORDER BY language_code
                """, (message_key,))
                messages = []
                for row in cur.fetchall():
                    messages.append({
                        'id': row[0],
                        'language_code': row[1],
                        'message_text': row[2],
                        'updated_at': row[3]
                    })
                return messages
    except Exception as e:
        logger.error(f"Error getting messages for key {message_key}: {e}")
        return []

def get_message_keys():
    """Получить список уникальных ключей сообщений."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT message_key
                    FROM bot_messages
                    ORDER BY message_key
                """)
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error getting message keys: {e}")
        return []

def get_bot_message(message_key: str, language_code: str):
    """Получить конкретное сообщение бота."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT message_text
                    FROM bot_messages
                    WHERE message_key = %s AND language_code = %s
                """, (message_key, language_code))
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting bot message: {e}")
        return None

def update_bot_message(message_key: str, language_code: str, message_text: str):
    """Обновить или добавить сообщение бота."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bot_messages (message_key, language_code, message_text, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (message_key, language_code) DO UPDATE
                    SET message_text = EXCLUDED.message_text,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (message_key, language_code, message_text))
                conn.commit()
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Error updating bot message: {e}")
        return None

def delete_bot_message(message_key: str, language_code: str):
    """Удалить сообщение бота."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM bot_messages
                    WHERE message_key = %s AND language_code = %s
                    RETURNING id
                """, (message_key, language_code))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error deleting bot message: {e}")
        return False


def import_default_currency_pairs():
    """Импортировать валютные пары по умолчанию, если таблица пуста."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверяем, пуста ли таблица
                cur.execute("SELECT COUNT(*) FROM currency_pairs")
                count = cur.fetchone()[0]
                if count == 0:
                    # Добавляем стандартные валютные пары
                    default_pairs = [
                        ("EURUSD", "EURUSD=X", "EUR/USD"),
                        ("GBPUSD", "GBPUSD=X", "GBP/USD"),
                        ("USDJPY", "USDJPY=X", "USD/JPY"),
                        ("USDCHF", "USDCHF=X", "USD/CHF"),
                        ("AUDUSD", "AUDUSD=X", "AUD/USD"),
                        ("USDCAD", "USDCAD=X", "USD/CAD"),
                        ("NZDUSD", "NZDUSD=X", "NZD/USD"),
                        ("EURGBP", "EURGBP=X", "EUR/GBP"),
                        ("EURCHF", "EURCHF=X", "EUR/CHF"),
                        ("EURJPY", "EURJPY=X", "EUR/JPY")
                    ]
                    
                    for pair in default_pairs:
                        cur.execute("""
                            INSERT INTO currency_pairs (pair_code, symbol, display_name, is_active)
                            VALUES (%s, %s, %s, TRUE)
                            ON CONFLICT (pair_code) DO NOTHING
                        """, pair)
                    
                    conn.commit()
                    logger.info(f"Imported {len(default_pairs)} default currency pairs")
                    return True
                return False
    except Exception as e:
        logger.error(f"Error importing default currency pairs: {e}")
        return False

# Новые функции для аналитики пользователей
def get_user_activity_stats():
    """Получить статистику активности пользователей"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Получаем общее количество пользователей
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_approved = TRUE THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as admins,
                        COUNT(CASE WHEN created_at > (CURRENT_TIMESTAMP - INTERVAL '7 day') THEN 1 END) as new_last_week
                    FROM users
                """)
                stats = cur.fetchone()
                
                # Получаем количество пользователей по языкам
                cur.execute("""
                    SELECT 
                        language_code,
                        COUNT(*) as count
                    FROM users
                    GROUP BY language_code
                    ORDER BY count DESC
                """)
                languages = []
                for row in cur.fetchall():
                    languages.append({
                        'language': row[0],
                        'count': row[1]
                    })
                
                return {
                    'total': stats[0] if stats else 0,
                    'approved': stats[1] if stats else 0,
                    'admins': stats[2] if stats else 0,
                    'new_last_week': stats[3] if stats else 0,
                    'languages': languages
                }
    except Exception as e:
        logger.error(f"Error getting user activity stats: {e}")
        return {
            'total': 0,
            'approved': 0,
            'admins': 0,
            'new_last_week': 0,
            'languages': []
        }

# Функции для управления режимом обслуживания
def get_bot_settings():
    """Получить настройки бота из базы данных"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Создаем таблицу настроек, если её еще нет
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        key VARCHAR(50) PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                
                # Получаем все настройки
                cur.execute("""
                    SELECT key, value, updated_at
                    FROM bot_settings
                """)
                
                settings = {}
                for row in cur.fetchall():
                    settings[row[0]] = {
                        'value': row[1],
                        'updated_at': row[2]
                    }
                
                # Если нет настройки режима обслуживания, создаем её со значением "off"
                if 'maintenance_mode' not in settings:
                    cur.execute("""
                        INSERT INTO bot_settings (key, value)
                        VALUES ('maintenance_mode', 'off')
                    """)
                    conn.commit()
                    settings['maintenance_mode'] = {
                        'value': 'off',
                        'updated_at': datetime.now()
                    }
                
                return settings
    except Exception as e:
        logger.error(f"Error getting bot settings: {e}")
        return {'maintenance_mode': {'value': 'off', 'updated_at': datetime.now()}}

def update_bot_setting(key, value):
    """Обновить настройку бота"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bot_settings (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING key
                """, (key, value))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error updating bot setting {key}: {e}")
        return False

def export_bot_data():
    """Экспортировать все настраиваемые данные бота"""
    try:
        data = {
            'currency_pairs': get_all_currency_pairs(),
            'bot_messages': get_all_bot_messages(),
            'bot_settings': get_bot_settings(),
            'export_date': datetime.now().isoformat()
        }
        return data
    except Exception as e:
        logger.error(f"Error exporting bot data: {e}")
        return None

def import_bot_data(data):
    """Импортировать настраиваемые данные бота"""
    try:
        with get_db_connection() as conn:
            # Импортируем валютные пары
            for pair in data.get('currency_pairs', []):
                add_or_update_currency_pair(
                    pair['pair_code'],
                    pair['symbol'],
                    pair['display_name'],
                    pair['is_active']
                )
            
            # Импортируем сообщения бота
            for msg in data.get('bot_messages', []):
                update_bot_message(
                    msg['message_key'],
                    msg['language_code'],
                    msg['message_text']
                )
            
            # Импортируем настройки бота
            for key, value_obj in data.get('bot_settings', {}).items():
                if isinstance(value_obj, dict) and 'value' in value_obj:
                    update_bot_setting(key, value_obj['value'])
                else:
                    update_bot_setting(key, value_obj)
            
            return True
    except Exception as e:
        logger.error(f"Error importing bot data: {e}")
        return False

# Функции для управления доступом модераторов
def get_moderator_permissions():
    """Получить список разрешений для модераторов"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Создаем таблицу разрешений, если её еще нет
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS moderator_permissions (
                        id SERIAL PRIMARY KEY,
                        permission_key VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT,
                        is_enabled BOOLEAN DEFAULT TRUE,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                
                # Получаем все разрешения
                cur.execute("""
                    SELECT permission_key, description, is_enabled, updated_at
                    FROM moderator_permissions
                    ORDER BY permission_key
                """)
                
                permissions = []
                for row in cur.fetchall():
                    permissions.append({
                        'key': row[0],
                        'description': row[1],
                        'is_enabled': row[2],
                        'updated_at': row[3]
                    })
                
                # Если таблица пуста, добавляем стандартные разрешения
                if not permissions:
                    default_permissions = [
                        ('approve_users', 'Одобрение новых пользователей', True),
                        ('reject_users', 'Отклонение новых пользователей', True),
                        ('send_broadcasts', 'Отправка массовых сообщений', False),
                        ('manage_currency', 'Управление валютными парами', False)
                    ]
                    
                    for perm in default_permissions:
                        cur.execute("""
                            INSERT INTO moderator_permissions (permission_key, description, is_enabled)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (permission_key) DO NOTHING
                        """, perm)
                    
                    conn.commit()
                    
                    # Получаем добавленные разрешения
                    cur.execute("""
                        SELECT permission_key, description, is_enabled, updated_at
                        FROM moderator_permissions
                        ORDER BY permission_key
                    """)
                    
                    permissions = []
                    for row in cur.fetchall():
                        permissions.append({
                            'key': row[0],
                            'description': row[1],
                            'is_enabled': row[2],
                            'updated_at': row[3]
                        })
                
                return permissions
    except Exception as e:
        logger.error(f"Error getting moderator permissions: {e}")
        return []

def update_moderator_permission(permission_key, is_enabled):
    """Обновить разрешение для модераторов"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE moderator_permissions
                    SET is_enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE permission_key = %s
                    RETURNING permission_key
                """, (is_enabled, permission_key))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error updating moderator permission {permission_key}: {e}")
        return False

# Initialize database tables
init_db()

# Функция для импорта стандартных сообщений бота
def import_default_bot_messages():
    """Импортировать стандартные сообщения бота, если таблица пуста."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверяем, есть ли уже какие-то сообщения
                cur.execute("SELECT COUNT(*) FROM bot_messages")
                result = cur.fetchone()
                count = result[0] if result else 0
                
                if count == 0:
                    # Добавляем стандартные сообщения на разных языках
                    default_messages = [
                        # welcome_message - приветственное сообщение
                        ("welcome_message", "ru", "Добро пожаловать в бот анализа рынка! Выберите валютную пару для анализа."),
                        ("welcome_message", "tg", "Ба боти таҳлили бозор хуш омадед! Ҷуфти асъорро барои таҳлил интихоб кунед."),
                        ("welcome_message", "uz", "Market tahlili botiga xush kelibsiz! Tahlil qilish uchun valyuta juftligini tanlang."),
                        ("welcome_message", "kk", "Нарық талдау ботына қош келдіңіз! Талдау үшін валюта жұбын таңдаңыз."),
                        ("welcome_message", "en", "Welcome to the Market Analysis Bot! Select a currency pair for analysis."),
                        
                        # access_request - запрос доступа
                        ("access_request", "ru", "Ваша заявка на доступ отправлена администратору. Ожидайте подтверждения."),
                        ("access_request", "tg", "Дархости шумо барои дастрасӣ ба маъмур фиристода шуд. Лутфан, тасдиқро интизор шавед."),
                        ("access_request", "uz", "Kirish so'rovingiz administratorga yuborildi. Tasdiqlashni kuting."),
                        ("access_request", "kk", "Кіру туралы өтінішіңіз әкімшіге жіберілді. Растауды күтіңіз."),
                        ("access_request", "en", "Your access request has been sent to the administrator. Please wait for confirmation."),
                        
                        # access_granted - доступ предоставлен
                        ("access_granted", "ru", "Ваша заявка одобрена! Теперь вы можете пользоваться ботом."),
                        ("access_granted", "tg", "Дархости шумо тасдиқ карда шуд! Акнун шумо метавонед аз бот истифода баред."),
                        ("access_granted", "uz", "So'rovingiz tasdiqlandi! Endi botdan foydalanishingiz mumkin."),
                        ("access_granted", "kk", "Сіздің өтінішіңіз мақұлданды! Енді ботты пайдалана аласыз."),
                        ("access_granted", "en", "Your request has been approved! You can now use the bot."),
                        
                        # access_denied - в доступе отказано
                        ("access_denied", "ru", "Ваша заявка отклонена. Для получения дополнительной информации обратитесь к администратору @tradeporu."),
                        ("access_denied", "tg", "Дархости шумо рад карда шуд. Барои маълумоти бештар, лутфан ба маъмур @tradeporu муроҷиат кунед."),
                        ("access_denied", "uz", "So'rovingiz rad etildi. Qo'shimcha ma'lumot olish uchun @tradeporu administratoriga murojaat qiling."),
                        ("access_denied", "kk", "Сіздің өтінішіңіз қабылданбады. Қосымша ақпарат алу үшін @tradeporu әкімшіге хабарласыңыз."),
                        ("access_denied", "en", "Your request has been denied. Please contact administrator @tradeporu for more information."),
                        
                        # language_change - смена языка
                        ("language_change", "ru", "Язык успешно изменен на русский."),
                        ("language_change", "tg", "Забон бо муваффақият ба тоҷикӣ тағйир дода шуд."),
                        ("language_change", "uz", "Til muvaffaqiyatli o'zbekchaga o'zgartirildi."),
                        ("language_change", "kk", "Тіл қазақ тіліне сәтті өзгертілді."),
                        ("language_change", "en", "Language successfully changed to English."),
                        
                        # admin_welcome - приветствие администратора
                        ("admin_welcome", "ru", "Добро пожаловать в панель администратора!"),
                        ("admin_welcome", "tg", "Хуш омадед ба панели администратор!"),
                        ("admin_welcome", "uz", "Administrator paneliga xush kelibsiz!"),
                        ("admin_welcome", "kk", "Әкімші панеліне қош келдіңіз!"),
                        ("admin_welcome", "en", "Welcome to the administrator panel!")
                    ]
                    
                    for msg in default_messages:
                        cur.execute("""
                            INSERT INTO bot_messages (message_key, language_code, message_text, updated_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (message_key, language_code) DO NOTHING
                        """, msg)
                    
                    conn.commit()
                    logger.info(f"Imported {len(default_messages)} default bot messages")
                    return True
                return False
    except Exception as e:
        logger.error(f"Error importing default bot messages: {e}")
        return False

# Import default data if needed
import_default_currency_pairs()
import_default_bot_messages()