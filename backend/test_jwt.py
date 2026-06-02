import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "test_key"
ALGORITHM = "HS256"

data = {"sub": "123"}
expire = datetime.now(timezone.utc) + timedelta(minutes=15)
to_encode = data.copy()
to_encode.update({"exp": expire})
token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

print(f"Token: {token}")

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"Payload: {payload}")
except Exception as e:
    print(f"Error: {e}")
