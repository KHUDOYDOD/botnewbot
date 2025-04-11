import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Генерируем хеш для пароля X12345x
password = "X12345x"
hashed_password = hash_password(password)
print(f"Пароль: {password}")
print(f"Хеш: {hashed_password}")