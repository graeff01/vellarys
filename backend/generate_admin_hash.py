import bcrypt

senha = "14180218Aa".encode()  # coloque aqui a senha desejada

hash = bcrypt.hashpw(senha, bcrypt.gensalt(rounds=12))
print(hash.decode())
