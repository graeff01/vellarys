import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def generate_vapid_keys():
    # Gerar chave privada EC curva SECP256R1
    private_key = ec.generate_private_key(ec.SECP256R1())
    
    # Pegar o valor privado como bytes (32 bytes)
    private_value = private_key.private_numbers().private_value
    private_key_bytes = private_value.to_bytes(32, byteorder='big')
    
    # Pegar a chave pública no formato uncompressed point (65 bytes)
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    def b64url(b):
        return base64.urlsafe_b64encode(b).decode('utf-8').rstrip('=')
    
    print(f"VAPID_PUBLIC_KEY={b64url(public_key_bytes)}")
    print(f"VAPID_PRIVATE_KEY={b64url(private_key_bytes)}")

if __name__ == "__main__":
    generate_vapid_keys()
