import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

def derive_key(password: str, salt: bytes) -> bytes:
    """Argon2id ile paroladan 32 baytlık AES anahtarı türetir."""
    kdf = Argon2id(
        salt=salt,
        length=32,
        iterations=2,
        lanes=1,
        memory_cost=65536,
    )
    return kdf.derive(password.encode('utf-8'))



class EmptyMessageError(ValueError):
    """Şifrelenecek mesaj boş olduğunda fırlatılır."""
    pass

def validate_plaintext(plaintext: bytes):
    if not plaintext or len(plaintext.strip()) == 0:
        raise EmptyMessageError("Şifrelenecek veya gizlenecek mesaj boş olamaz.")

def encrypt_aes_gcm(plaintext: bytes, password: str, aad: bytes = None) -> tuple[bytes, bytes, bytes]:
    """
    Rastgele salt ve nonce üretir. Argon2id ile anahtar türetir.
    AES-256-GCM ile şifreler (Header'ı AAD olarak korumaya alır).
    Dönüş: (ciphertext_plus_tag, nonce, salt)
    """
    validate_plaintext(plaintext)  # <--- İşte bu eksikti
    
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive_key(password, salt)
    
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, aad)
    return ciphertext_and_tag, nonce, salt


def decrypt_aes_gcm(ciphertext_and_tag: bytes, password: str, nonce: bytes, salt: bytes, aad: bytes = None) -> bytes:
    """
    Argon2id ile anahtarı yeniden türetir.
    AES-256-GCM ile çözer ve AAD (Header) bütünlüğünü doğrular.
    """
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_and_tag, aad)


def generate_rsa_keys():
    """2048-bit RSA anahtar çifti üretir."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    return private_key, public_key

def wrap_aes_key(aes_key: bytes, public_key) -> bytes:
    """Rastgele 32 baytlık AES anahtarını RSA-OAEP-SHA256 ile sarar (256 bayt)."""
    return public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def unwrap_aes_key(wrapped_key: bytes, private_key) -> bytes:
    """Sarılmış AES anahtarını RSA özel anahtarı ile çözer."""
    return private_key.decrypt(
        wrapped_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def save_private_key(private_key, filepath: str, password: str = None):
    """Özel anahtarı PEM formatında kaydeder. İsteğe bağlı parola ile şifreler."""
    encryption = (
        serialization.BestAvailableEncryption(password.encode()) 
        if password else serialization.NoEncryption()
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    with open(filepath, "wb") as f:
        f.write(pem)

def load_private_key(filepath: str, password: str = None):
    """PEM formatındaki özel anahtarı dosyadan okur."""
    with open(filepath, "rb") as f:
        pem_data = f.read()
    return serialization.load_pem_private_key(pem_data, password=password.encode() if password else None)

def save_public_key(public_key, filepath: str):
    """Genel anahtarı PEM formatında kaydeder."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(filepath, "wb") as f:
        f.write(pem)

def load_public_key(filepath: str):
    """PEM formatındaki genel anahtarı dosyadan okur."""
    with open(filepath, "rb") as f:
        pem_data = f.read()
    return serialization.load_pem_public_key(pem_data)