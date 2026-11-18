import struct

# Formatlar: 
# Ortak önek (8 bayt): 4s (magic), B (version), B (mode), B (k), B (reserved)
# AES kalanı (32 bayt): 12s (nonce), I (ct_len), 16s (salt) -> Toplam 40
# RSA kalanı (272 bayt): 12s (nonce), I (ct_len), 256s (wrapped_key) -> Toplam 280

HEADER_PREFIX_FORMAT = "!4sBBBB"
HEADER_PREFIX_SIZE = struct.calcsize(HEADER_PREFIX_FORMAT) # 8 bayt

def pack_header(mode: int, k: int, nonce: bytes, ct_len: int, extra_data: bytes) -> bytes:
    """
    mode: 0x01 (AES) veya 0x02 (RSA)
    extra_data: AES için 16 bayt salt, RSA için 256 bayt wrapped_key
    """
    magic = b"STG1"
    version = 1
    reserved = 0
    prefix = struct.pack(HEADER_PREFIX_FORMAT, magic, version, mode, k, reserved)
    
    # extra_data içinde salt veya wrapped_key var
    rest_format = f"!12sI{len(extra_data)}s"
    rest = struct.pack(rest_format, nonce, ct_len, extra_data)
    
    return prefix + rest


def unpack_header_prefix(data: bytes):
    """İlk 8 baytlık öneki çözer ve validasyon yapar."""
    if len(data) < HEADER_PREFIX_SIZE:
        raise ValueError("Veri header öneki için çok kısa.")
    
    magic, version, mode, k, reserved = struct.unpack(HEADER_PREFIX_FORMAT, data[:HEADER_PREFIX_SIZE])
    
    if magic != b"STG1":
        raise ValueError(f"Geçersiz dosya imzası (Magic): {magic}. Beklenen: b'STG1'")
    if version != 1:
        raise ValueError(f"Desteklenmeyen sürüm: {version}")
    if mode not in (0x01, 0x02):
        raise ValueError(f"Geçersiz şifreleme modu: {mode}")
    if k not in (1, 2, 3):
        raise ValueError(f"Geçersiz k değeri: {k} (1, 2 veya olmalı)")
        
    return magic, version, mode, k, reserved

def unpack_header_rest(data: bytes, mode: int):
    """Moda göre kalan header kısmını (nonce, ct_len, salt/wrapped_key) çözer."""
    if mode == 0x01: # AES modu (kalan 32 bayt)
        # 12s (nonce), I (ct_len), 16s (salt)
        rest_format = "!12sI16s"
        rest_size = struct.calcsize(rest_format)
        if len(data) < rest_size:
            raise ValueError("AES header için veri yetersiz.")
        nonce, ct_len, salt = struct.unpack(rest_format, data[:rest_size])
        return nonce, ct_len, salt, rest_size
        
    elif mode == 0x02: # RSA modu (kalan 272 bayt)
        # 12s (nonce), I (ct_len), 256s (wrapped_key)
        rest_format = "!12sI256s"
        rest_size = struct.calcsize(rest_format)
        if len(data) < rest_size:
            raise ValueError("RSA header için veri yetersiz.")
        nonce, ct_len, wrapped_key = struct.unpack(rest_format, data[:rest_size])
        return nonce, ct_len, wrapped_key, rest_size
    else:
        raise ValueError(f"Geçersiz şifreleme modu: {mode}")

def calculate_max_payload_bytes(width: int, height: int, header_bytes_len: int, k: int) -> int:
    """
    Kapasite formülü (Seçenek A):
    Header her zaman k=1 ile gömülür. Payload ise header'daki k ile gömülür.
    N = W * H * 3 (Toplam kanal değeri sayısı)
    Header'ın tükettiği kanal değeri: 8 * header_bytes_len (çünkü k=1)
    Kalan kapasite bit cinsinden k ile çarpılır, bayta çevrilir.
    """
    total_channels = width * height * 3
    header_channel_consumption = header_bytes_len * 8  # k=1 olduğu için her bayt 8 kanal tüketir
    
    available_channels_for_payload = total_channels - header_channel_consumption
    if available_channels_for_payload < 0:
        return 0
        
    max_payload_bits = available_channels_for_payload * k
    max_payload_bytes = max_payload_bits // 8
    
    # Tag (16 bayt) payload'a dahil olduğu için net düz metin kapasitesi bundan 16 çıkarılarak bulunur
    return max_payload_bytes