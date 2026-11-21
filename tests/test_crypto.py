import pytest
from cryptography.exceptions import InvalidTag
from src.crypto_module import (
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    generate_rsa_keys,
    wrap_aes_key,
    unwrap_aes_key
)
from src.container import pack_header, unpack_header_prefix, unpack_header_rest
from src.crypto_module import EmptyMessageError, save_private_key, load_private_key, save_public_key, load_public_key

def test_aes_gcm_roundtrip():
    plaintext = b"Gizli mesaj: Merhaba Dunya!"
    password = "guclu_parola_123"
    aad = b"header_mock_data"

    ct_tag, nonce, salt = encrypt_aes_gcm(plaintext, password, aad=aad)
    decrypted = decrypt_aes_gcm(ct_tag, password, nonce, salt, aad=aad)

    assert decrypted == plaintext

def test_aes_gcm_wrong_password():
    plaintext = b"Gizli mesaj"
    password = "dogru_parola"
    wrong_password = "yanlis_parola"

    ct_tag, nonce, salt = encrypt_aes_gcm(plaintext, password)
    
    with pytest.raises(InvalidTag):
        decrypt_aes_gcm(ct_tag, wrong_password, nonce, salt)

def test_aes_gcm_aad_tamper():
    plaintext = b"Gizli mesaj"
    password = "parola"
    aad = b"orijinal_header"
    tampered_aad = b"bozulmus_header"

    ct_tag, nonce, salt = encrypt_aes_gcm(plaintext, password, aad=aad)
    
    # Header (AAD) değiştirildiğinde GCM bütünlük kontrolü patlamalı
    with pytest.raises(InvalidTag):
        decrypt_aes_gcm(ct_tag, password, nonce, salt, aad=tampered_aad)

@pytest.mark.parametrize("tamper_offset", [0, -1], ids=["ciphertext", "tag"])
def test_aes_gcm_single_bit_tamper_is_rejected(tamper_offset: int):
    plaintext = b"Gizli mesaj"
    password = "parola"

    ct_tag, nonce, salt = encrypt_aes_gcm(plaintext, password)
    tampered_ct_tag = bytearray(ct_tag)
    tampered_ct_tag[tamper_offset] ^= 0x01

    with pytest.raises(InvalidTag):
        decrypt_aes_gcm(bytes(tampered_ct_tag), password, nonce, salt)

def test_rsa_hybrid_roundtrip():
    priv_key, pub_key = generate_rsa_keys()
    aes_key = b"A" * 32  # 32 bayt rastgele AES anahtarı simülasyonu

    wrapped = wrap_aes_key(aes_key, pub_key)
    unwrapped = unwrap_aes_key(wrapped, priv_key)

    assert unwrapped == aes_key








def test_empty_message_error():
    """Boş mesaj durumunda EmptyMessageError fırlatıldığını test eder."""
    with pytest.raises(EmptyMessageError):
        encrypt_aes_gcm(b"", "parola")

def test_invalid_magic_error():
    """Geçersiz magic (imza) durumunda ValueError fırlatıldığını test eder."""
    bad_header = b"BAD1" + b"\x01" * 20  # Hatalı magic
    with pytest.raises(ValueError, match="Geçersiz dosya imzası"):
        unpack_header_prefix(bad_header)

def test_pem_key_save_load_encrypted(tmp_path):
    """RSA özel anahtarının parolalı olarak PEM formatına kaydedilip okunabilmesini test eder."""
    priv_key, pub_key = generate_rsa_keys()
    key_path = tmp_path / "private_encrypted.pem"
    password = "guclu_rsa_parolasi"

    save_private_key(priv_key, str(key_path), password=password)
    loaded_priv = load_private_key(str(key_path), password=password)

    # Anahtar doğrulaması için test sarmalama/çözme
    aes_key = b"B" * 32
    wrapped = wrap_aes_key(aes_key, pub_key)
    unwrapped = unwrap_aes_key(wrapped, loaded_priv)
    assert unwrapped == aes_key

def test_pem_key_save_load_unencrypted(tmp_path):
    """RSA anahtarlarının şifresiz PEM olarak kaydedilip okunabilmesini test eder."""
    priv_key, pub_key = generate_rsa_keys()
    priv_path = tmp_path / "private.pem"
    pub_path = tmp_path / "public.pem"

    save_private_key(priv_key, str(priv_path))
    save_public_key(pub_key, str(pub_path))

    loaded_priv = load_private_key(str(priv_path))
    loaded_pub = load_public_key(str(pub_path))

    aes_key = b"C" * 32
    wrapped = wrap_aes_key(aes_key, loaded_pub)
    unwrapped = unwrap_aes_key(wrapped, loaded_priv)
    assert unwrapped == aes_key



def test_rsa_wrong_private_key_error():
    """Yanlış özel anahtar ile RSA anahtar çözme denemesinde hata (OAEP/ValueError) alındığını test eder."""
    priv_key_1, pub_key_1 = generate_rsa_keys()
    priv_key_2, _ = generate_rsa_keys()  # Farklı bir anahtar
    
    aes_key = b"D" * 32
    wrapped = wrap_aes_key(aes_key, pub_key_1)
    
    # Yanlış özel anahtar ile çözmeye çalışmak cryptographically decryption hatası (ValueError) vermeli
    with pytest.raises(ValueError):
        unwrap_aes_key(wrapped, priv_key_2)