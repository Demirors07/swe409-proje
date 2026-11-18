import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

def encrypt_aes_gcm(plaintext: bytes, key: bytes, header_bytes: bytes) -> tuple[bytes, bytes]:
    """
    AES-256-GCM ile şifreleme yapar.
    - key: 32 baytlık AES anahtarı
    - plaintext: şifrelenecek ham veri (bytes)
    - header_bytes: AAD (Additional Authenticated Data) olarak kullanılacak header
    Döner: (nonce, ciphertext_with_tag)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # Her şifrelemede taze 12 baytlık rastgele nonce
    
    # AESGCM.encrypt otomatik olarak ciphertext ile tag'i birleştirip döndürür
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, header_bytes)
    return nonce, ciphertext_with_tag


def decrypt_aes_gcm(ciphertext_with_tag: bytes, key: bytes, nonce: bytes, header_bytes: bytes) -> bytes:
    """
    AES-256-GCM ile şifre çözme yapar.
    - ciphertext_with_tag: Şifreli metin + 16 baytlık tag
    - key: 32 baytlık AES anahtarı
    - nonce: Şifrelemede kullanılan 12 baytlık nonce
    - header_bytes: AAD olarak doğrulanacak header
    Döner: Ham plaintext baytları
    """
    aesgcm = AESGCM(key)
    # Tag uyuşmazlığı veya bozulma durumunda cryptography.exceptions.InvalidTag fırlatır
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, header_bytes)
    return plaintext


def derive_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Paroladan Argon2id kullanarak 32 baytlık AES anahtarı türetir.
    - salt verilmezse 16 baytlık taze salt üretilir.
    Döner: (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)  # Her şifrelemede taze 16 baytlık salt
        
    argon2 = Argon2id(
        salt=salt,
        length=32,          # AES-256 için 32 bayt
        iterations=2,       # Zaman maliyeti
        lanes=4,            # Paralellik
        memory_cost=65536   # Bellek maliyeti (64 MB)
    )
    key = argon2.derive(password.encode('utf-8'))
    return key, salt


def generate_rsa_keypair():
    """
    2048-bit RSA anahtar çifti üretir.
    Döner: (private_key, public_key)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    return private_key, public_key



def wrap_aes_key(aes_key: bytes, public_key) -> bytes:
    """
    32 baytlık AES anahtarını RSA-OAEP (SHA-256) ile sarmalar.
    Döner: 256 baytlık sarmalanmış anahtar (wrapped_key).
    """
    wrapped_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return wrapped_key


def unwrap_aes_key(wrapped_key: bytes, private_key) -> bytes:
    """
    RSA-OAEP (SHA-256) ile sarmalanmış AES anahtarını özel anahtar (private key) ile çözer.
    Döner: 32 baytlık orijinal AES anahtarı.
    """
    aes_key = private_key.decrypt(
        wrapped_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return aes_key