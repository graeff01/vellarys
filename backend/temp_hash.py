from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

senha = "14180218Aab."
print(pwd.hash(senha))
