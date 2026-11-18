# veriyi PNG piksellerinin içine görünmez bir şekilde nakşedeceğimiz Steganografi Çekirdeği


from PIL import Image

def calculate_capacity(image_path: str, bits_per_pixel: int = 1) -> int:
    """
    Verilen bir görselin LSB ile kaç bayt veri taşıyabileceğini hesaplar.
    - image_path: Resmin dosya yolu
    - bits_per_pixel: Her piksel kanalından kaç bit kullanılacağı (varsayılan: 1)
    Döner: Maksimum bayt kapasitesi
    """
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    
    # Toplam renk kanalı (Her pikselde R, G, B olmak üzere 3 kanal var)
    total_channels = width * height * 3
    total_bits = total_channels * bits_per_pixel
    
    # 8 bite bölünerek bayt cinsinden kapasite bulunur
    capacity_bytes = total_bits // 8
    return capacity_bytes



