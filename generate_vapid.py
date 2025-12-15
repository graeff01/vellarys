from py_vapid import Vapid01

vapid = Vapid01()
vapid.generate_keys()

print("\n=== VAPID KEYS ===\n")
print("PUBLIC KEY:\n")
print(vapid.public_key)
print("\nPRIVATE KEY:\n")
print(vapid.private_key)
