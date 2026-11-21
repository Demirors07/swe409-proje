# DECISIONS — SWE-409 Projesi

Proje boyunca alınan kararların kronolojik kaydı. Adım 1'de "Design and
Methodology" belgesine taşınacak kararlar burada birikir. Her yeni karar
tarih + gerekçe ile eklenir.

---

## Adım 0 — Hazırlık (kapandı: 17 Kasım 2026)

### Ortam
- İşletim sistemi: Ubuntu Linux
- Python: 3.10.12 (`python3 --version`)
- Sanal ortam: `.venv` (proje kökünde)
- Aktivasyon: `source .venv/bin/activate`
- Paket yöneticisi: pip (venv içinde)

### Git / GitHub
- Yerel klasör: `swe409-proje`
- GitHub repo: `Demirors07/swe409-proje` (private)
- Branch: `main`
- Git kimliği: user.name = `karne07`, user.email = `d3mirors.07@gmail.com`
- Commit dili: ilk commit Türkçe; bundan sonrakiler İngilizce
- Commit mesajı formatı: `Step X: kısa açıklama`
- .gitignore kapsamı: `__pycache__/`, `*.py[cod]`, `.venv/`, `venv/`,
  `*.pem`, `*.key`, `.env`, `.DS_Store`, `results/tmp/`
- Temiz teslim kopyası: `git archive --format=zip -o swe409-teslim.zip HEAD`
- Lisans: eklenmeyecek (private repo)

### Proje / rapor
- Rapor dili: İngilizce
- Rapor formatı: PDF
- Sayfa sınırı: yok
- Atıf stili: APA 7
- Çalışma modu: tek kişi (onaylı)

### Açık konular — Ek B (hocaya sorulacak)
- Klasör adı (yalnız öğrenci numarası yeterli mi?)
- Arşiv formatı (.rar zorunlu mu, .zip kabul mü?)
- Kaynak kod ve örnek görseller teslime dahil mi?
- Zamanlama: Adım 9 (18–19 Aralık 2026), plandaki gibi
- Risk notu: Cevap geç gelirse paketleme yeniden yapılabilir; kabul edildi.

---

## A–F kararları (onaylandı; detaylar Adım 1'de)

- A — Header her zaman k=1 ile gömülür; `extract --bits` yok. Payload
  header'daki k ile.
- B — Header, AES-GCM'e AAD olarak verilir.
- C — KDF: `cryptography` içindeki Argon2id; parametreler kodda sabit ve
  `version` alanına bağlı. OWASP güncel değerleri Adım 1'de belgelenir.
- D — Boş mesaj açık hatayla reddedilir; test edilir.
- E — Girdi RGB'ye çevrilir, çıktı her zaman PNG. Alfa davranışı Adım 1'de
  netleşecek (öneri: beyaz üstüne bindir).
- F — PRNG'li dağınık gömme ertelendi (zaman kalırsa Adım 7 sonrası).

## Adım 1'de kilitlenecekler (yol haritası gereği ertelendi)
- Bit sırası: MSB-first (kilitlendi)
- Gömme sırası: satır satır, soldan sağa, üstten alta, R→G→B

---

## Değişiklik geçmişi

| Tarih       | Karar                                              | Gerekçe                                  |
|-------------|----------------------------------------------------|------------------------------------------|
| 2026-11-17  | Proje iskeleti + .gitignore + ilk commit           | Adım 0                                   |
| 2026-11-17  | Python 3.10.12 kabul edildi                        | Tüm hedef kütüphaneler 3.10'u destekliyor |
| 2026-11-17  | `.venv` adı korundu                                | Modern konvansiyon, .gitignore uyumlu    |
| 2026-11-17  | Repo adı `swe409-proje` olarak kilitlendi          | Ders koduyla uyumlu, değiştirmek gereksiz |
| 2026-11-17  | Commit dili İngilizceye çevrildi                   | Rapor İngilizce, tutarlılık              |
| 2026-11-17  | Ek B mesajı Adım 9'da gönderilecek                 | Kullanıcı plana sadık kalma tercihi      |



## Adım 1: Tasarım ve Metodoloji — TAMAMLANDI
* **Dokümantasyon:** Tüm teknik tasarım kararları ve sistem mimarisi `docs/design.md` dosyasına işlendi.
* **Header Şeması:** AES modu için **40 bayt**, RSA hibrit modu için **280 bayt** sabit boyutlu yapı (`magic="STG1"`, `version`, `mode`, `k`, `reserved`, `nonce`, `ct_len`, `salt`/`wrapped_key`) onaylandı.
* **Kapasite Formülü:** Header'ın her zaman **$k = 1$** ile gömülmesi esasına dayalı $\text{MaxPayloadBytes} = \lfloor (((W \times H \times 3) - (H_{\text{bytes}} \times 8)) \times k) / 8 \rfloor$ formülü kesinleştirildi.
* **Hata Yönetimi:** `EmptyMessageError`, `CapacityError`, `InvalidHeader` ve `DecryptionError` olmak üzere 4 temel hata türü tanımlandı.
* **Veri Akışları:** Tek aşamalı gömme (`embed`) ve iki aşamalı okuma/doğrulama (`extract`) akış mantığı netleştirildi.
* **Sıradaki Adım:** Adım 2 (Proje klasör iskeletinin oluşturulması ve çekirdek modüllerin kodlanması).


## Adım 2: Proje İskeleti ve Güvenlik Altyapısı - TAMAMLANDI
- **Dizin Yapısı:** `src/` (çekirdek modüller), `samples/` (test görselleri) olarak modüler bir ayrım yapıldı. Temiz mimari (Clean Architecture) prensibiyle sorumluluklar birbirinden izole edildi.
## *. Test Görselleri ve Örnek Varlık Üretimi (`samples/create_samples.py`)
- **Otomatik Test Varlıkları:** Dışarıdan rastgele veya uygun boyutta görsel aramak yerine, Pillow (`PIL`) kütüphanesi kullanılarak programatik olarak test görselleri (`samples/`) üreten bir betik (`create_samples.py`) tasarlandı.
- **Çeşitlilik ve Sınır Testleri:** Farklı renk paletlerine ve çözünürlüklere sahip test görselleri sayesinde, stüdyo ortamında kapasite sınırları (`calculate_capacity`) ve LSB veri gömme/çıkarma hassasiyeti güvenle test edilebilir hale getirildi.
- **Git Güvenliği (.gitignore):** Hassas kriptografik anahtarların (`*.pem`, `*.key`), sanal ortamların (`.venv/`) ve geçici steganografi çıktıları ile önbelleklerin (`__pycache__/`, `samples/*_stego.png`) uzaktaki depoya (GitHub) sızmasını engellemek için katı kurallar tanımlandı.




## Adım 3: Kriptografik Katman Gerçekleşimi (Implementation → Cryptographic Layer)

Projenin güvenli veri gizleme mekanizmasının temelini oluşturan kriptografik katman (`src/crypto_module.py` ve `src/container.py`), gizliliğin yanı sıra bütünlük (integrity) ve kimlik doğrulama (authenticity) sağlamak üzere hibrit bir yaklaşımla tasarlanmıştır. Bu katman, simetrik ve asimetrik şifreleme algoritmalarını güvenli bir anahtar türetme fonksiyonu ve sıkı hata denetim mekanizmalarıyla birleştirir.

### 1. Simetrik Şifreleme Katmanı (AES-256-GCM)
* **Algoritma ve Mod:** Verinin şifrelenmesinde **AES-256-GCM** (Galois/Counter Mode) tercih edilmiştir. GCM modu, hem gizlilik hem de AEAD (Authenticated Encryption with Associated Data) özelliği sayesinde bütünlük koruması sağlar.
* **Nonce Yönetimi:** Her şifreleme işleminde `os.urandom(12)` kullanılarak benzersiz ve rastgele **12 baytlık bir nonce** üretilir. Bu sayede aynı anahtarla yapılan şifrelemelerde bile (IV reuse zafiyeti önlenerek) farklı ciphertext çıktıları elde edilir.
* **Şifreleme ve Boyut Hesabı:** Şifreleme işleminden hemen önce ciphertext uzunluğu `ct_len = len(plaintext) + 16` formülüyle kesin olarak hesaplanır (16 bayt GCM kimlik doğrulama etiketini - tag - ifade eder). Şifreleme sırasında header baytları AAD (Associated Data) olarak fonksiyona (`AESGCM.encrypt`) dahil edilir:
  $$\text{ciphertext\_and\_tag} = \text{AESGCM}(key).\text{encrypt}(nonce, plaintext, aad=header\_bytes)$$

### 2. Parola Tabanlı Anahtar Türetme (Parola Modu)
* Parola modu tercih edildiğinde, düz metin paroladan doğrudan anahtar türetilmez; kriptografik güvenliği artırmak için **Argon2id** anahtar türetme fonksiyonu (KDF) kullanılır.
* **İşlem Adımları:**
  1. Rastgele **16 baytlık bir salt** (tuz) üretilir ve bu salt doğrudan container header alanına yazılır.
  2. Kullanıcı parolası ve bu salt, Argon2id algoritmasından geçirilerek güvenli **32 baytlık (256-bit) AES anahtarı** türetilir.

### 3. Asimetrik Şifreleme ve Anahtar Sarma Katmanı (RSA-2048)
* RSA modu seçildiğinde, sistem rastgele üretilen **32 baytlık simetrik AES anahtarını** asimetrik olarak koruma altına alır.
* **Anahtar Çifti Yönetimi:** RSA-2048 anahtar çifti üretimi (`generate_rsa_keys`) desteklenmekte olup, özel anahtarlar (`private key`) PEM formatında şifresiz veya isteğe bağlı parola korumasıyla (`PKCS8` / `BestAvailableEncryption`) dosyaya kaydedilebilmekte ve okunabilmektedir.
* **Anahtar Sarma (Key Wrapping):** Rastgele üretilen 32 baytlık AES anahtarı, alıcının genel anahtarı ile **RSA-OAEP-SHA256** padding şeması kullanılarak sarılır ve tam **256 baytlık** `wrapped_key` verisi elde edilir. Çözme aşamasında ise karşılık gelen özel anahtar ile OAEP çözme işlemi gerçekleştirilerek orijinal AES anahtarına ulaşılır.

### 4. Konteyner ve Header Paketleme (`container.py`)
* İkilik (binary) veri yapısının düzenli okunabilmesi için `struct` modülü kullanılmıştır. Okuma işlemi iki aşamalı olarak tasarlanmıştır:
  1. **Ön Okuma (Prefix):** İlk 8 bayt okunarak dosya imzası (`magic` = `b"STG1"`), versiyon, şifreleme modu ve $k$ (LSB bit sayısı) parametreleri doğrulanır.
  2. **Gövde Okuma (Rest):** Seçilen moda göre (Parola veya RSA) kalan header alanları (`salt` veya `wrapped_key`, `nonce`, `ct_len`) çözümlenir.

### 5. Hata Yönetimi ve Güvenlik Kontrolleri
Sistem olası saldırılara ve hatalı kullanımlara karşı sıkı bir doğrulama katmanına sahiptir:
* **GCM Bütünlük ve Parola Hataları:** Yanlış parola girişi veya ciphertext/tag üzerinde yapılacak herhangi bir yetkisiz değişiklik (bitflip), `cryptography` kütüphanesinin GCM mekanizması tarafından `InvalidTag` istisnası ile yakalanır. *Not: GCM yapısı gereği yanlış parola ile bozulmuş veri durumu birbirinden matematiksel olarak ayırt edilemez; her ikisi de bütünlük doğrulaması hatası (`InvalidTag`) olarak raporlanır.*
* **RSA Çözme Hataları:** Yanlış özel anahtar kullanılması durumunda RSA-OAEP çözme hatası (`ValueError`) tetiklenir.
* **Header ve Bütünlük Doğrulamaları:** Header çözme aşamasında `magic` (`b"STG1"`), desteklenmeyen sürüm, geçersiz mod veya hatalı `ct_len` değerleri anında yakalanarak `ValueError` fırlatılır.
* **Boş Mesaj Koruması:** Şifrelenecek veya gizlenecek verinin boş olması durumunda açık bir hata fırlatılması için `EmptyMessageError` mekanizması entegre edilmiştir.

### 6. Doğrulama, Test Senaryoları ve Modül Çıktısı
* Kriptografik modül, görüntü taşıyıcı katmanından bağımsız olarak `pytest` ile uçtan uca test edilmiştir[cite: 1].
* Kapsanan temel test senaryoları[cite: 1]:
  * Parola ve RSA modları için şifreleme-çözme gidiş-dönüş (`round-trip`) doğrulaması[cite: 1].
  * Yanlış parola ve yanlış RSA özel anahtarı ile çözme denemelerinde beklenen hataların alınması[cite: 1].
  * Ciphertext üzerinde tek bit değişikliği ve kimlik doğrulama etiketi (`tag`) bozulmalarında `InvalidTag` hatası üretilmesi[cite: 1].
  * Header alanında yapılan değişikliklerde AAD bütünlük doğrulaması sayesinde kimlik doğrulama hatası alınması[cite: 1].
  * Geçersiz `magic` imzası ve boş mesaj girişlerinde açık hata (`ValueError` / `EmptyMessageError`) fırlatılması[cite: 1].
* Modül resim bağımlılığı olmadan çalışmakta ve tüm birim testlerini başarıyla geçmektedir[cite: 1].




## Adım 4: Steganografi Katmanı Gerçekleşimi (Implementation → Steganographic Layer & Kapasite Analizi)[cite: 1, 2]

Projenin taşıyıcı görüntü katmanını oluşturan steganografi modülü (`src/stego_module.py`), şifrelenmiş `payload` baytlarını ve header meta verilerini kayıpsız `PNG` görsellerinin `RGB` renk kanallarındaki en düşük anlamlı bitlere (`LSB`) vektörize olarak gömer ve geri çıkarır[cite: 1, 2]. Bu katman, şifreleme (`crypto_module.py`) ve paketleme/kapasite (`container.py`) katmanlarından ayrık çalışacak şekilde tasarlanmıştır[cite: 2].

### 1. Girdi Dönüşümü, Bit Sırası ve Kayıpsız Kayıt
* **Görsel Yükleme (`load_rgb_array`):** Girdi dosyası `Pillow` ile açılır; şeffaflık (`A` / `RGBA`) içeriyorsa `(255, 255, 255, 255)` beyaz zemin üzerinde `alpha_composite` ile birleştirilir ve bağımsız `(height, width, 3)` `uint8` `RGB` NumPy dizisine dönüştürülür[cite: 2].
* **MSB-First Bit ↔ Bayt Dönüşümü (`bytes_to_bits_msb`, `bits_to_bytes_msb`):** Bayt dizileri `MSB-first` (`bitorder="big"`) sırasıyla `0/1` bit dizilerine açılır; `8` bit hizalı bit dizileri tekrar baytlara paketlenir[cite: 2].
* **Kayıpsız PNG Kaydı (`save_rgb_png`):** Gömme işlemi sonrası çıktı uzantısı `.png` olacak şekilde normalize edilir ve `(H, W, 3)` `uint8` dizi kayıpsız `PNG` (`format="PNG", compress_level=6`) olarak kaydedilir[cite: 1, 2].

### 2. Vektörize `k`-Bit LSB Gömme ve Çıkarma
* **Gömme (`embed_kbits_lsb`):** `k` değeri gömme/çıkarma yardımcılarında `1..8` aralığında, wire/header formatında ise `1..3` aralığında doğrulanır. Hedef kanallardaki en düşük `k` bit maskelenerek temizlenir (`& (0xFF ^ mask)`) ve `MSB-first` bit gruplarıyla doldurulur[cite: 1, 2]. Son grupta eksik bit kalırsa sıfır ile doldurulur (`np.pad`) ve `inplace=False` iken orijinal dizi korunur[cite: 2].
* **Çıkarma (`extract_kbits_lsb`):** İlgili kanal aralığından maskelenen `k` bitlik değerler `MSB-first` sırasıyla bitlere ayrıştırılır ve `[:n_bits]` ile istenen tam bit sayısına kırpılır[cite: 2].

### 3. Hibrit `k` Gömme ve İki Aşamalı Header Okuma
* **Gömme Akışı (`embed_message`):** `mode` (`0x01` için `40` bayt header / `16` bayt `extra_data`; `0x02` için `280` bayt header / `256` bayt `extra_data`), `12` bayt `nonce` ve `payload` tipi/uzunluğu doğrulanır; `ensure_capacity` ile kapasite kontrolü yapılır[cite: 2]. Header her zaman `k=1` ile başlangıçtan itibaren gömülür, ardından `payload` header'da belirtilen `k` (`1`, `2` veya `3`) değeriyle kaldığı kanal ofsetinden devam edilerek gömülür[cite: 1, 2].
* **Çıkarma Akışı (`extract_stego_payload`, `extract_message_from_image`):** Önce `k=1` ile `HEADER_PREFIX_SIZE` (`8` bayt) önek çıkarılıp `unpack_header_prefix` ile `mode` ve `k` elde edilir[cite: 2]. Ardından `mode`'a göre kalan header baytları yine `k=1` ile okunup `unpack_header_rest` ile `nonce`, `payload_size` (`ct_len`) ve `extra_data` çözümlenir; son olarak `payload_size * 8` bit `k` derinliğiyle okunarak `(payload, mode, k, nonce, extra_data)` döndürülür[cite: 2].

### 4. Kapasite Analizi ve Sınır Koşulları
* Genişliği $W$, yüksekliği $H$ olan bir `RGB` görselde toplam kanal sayısı $W \times H \times 3$'tür[cite: 2]. Header her zaman $k=1$ ile gömüldüğünden `mode = 0x01` için `320` kanal (`40` bayt) ve `mode = 0x02` için `2240` kanal (`280` bayt) header'a ayrılır[cite: 2].
* Maksimum payload kapasitesi (bayt cinsinden), `container.py` içindeki `calculate_max_payload_bytes` ile şu formüle göre hesaplanır[cite: 1, 2]:
  $$\text{Capacity}_{\text{max}}(W, H, L_{\text{header}}, k) = \left\lfloor \frac{((W \times H \times 3) - (L_{\text{header}} \times 8)) \times k}{8} \right\rfloor$$
* **Taşma Kontrolü (`ensure_capacity`, `CapacityError`):** Gerekli `payload` bayt sayısı mevcut kapasiteyi aştığında `CapacityError` fırlatılır ve hata mesajında hem gerekli (`required`) hem mevcut (`available`) bayt sayısı açıkça belirtilir[cite: 1, 2].
* **Kapasite Yardımcıları (`capacity`, `calculate_capacity`):** `capacity(image, mode, k)` dosya yolu, `PIL.Image` veya `(H, W, 3)` `uint8` dizi girdileri için header payını düşerek net payload kapasitesini döndürür; `calculate_capacity(image_path, bits_per_pixel)` ise header düşülmemiş ham kanal kapasitesini (`W * H * 3 * bits_per_pixel // 8`) verir[cite: 2].

### 5. Doğrulama, Test Senaryoları ve Modül Çıktısı
* `pytest.ini` (`pythonpath = . src`) yapılandırması altında steganografi modülü bit seviyesi, kapasite sınırları, bozuk/eksik girdi ve uçtan uca `round-trip` testleriyle doğrulanmıştır[cite: 1, 2].
* Kapsanan temel test senaryoları[cite: 1, 2]:
  * Rastgele `payload`, `mode` (`0x01` / `0x02`), `k` (`1`, `2`, `3`), `nonce` ve `extra_data` alanlarının farklı boyutlarda ve `RGB`/`RGBA` girdilerde birebir korunması (`round-trip`)[cite: 1, 2].
  * Eksik kalan son `k` bit grubunun sıfırla doldurulması, kullanılmayan üst bitlerin ve `inplace=False` iken orijinal dizinin değişmemesi ile `0/1` dışı bitlerin reddedilmesi[cite: 2].
  * Maksimum kapasiteye tam eşit veride başarı; `max + 1` baytta gerekli ve mevcut bayt sayılarını içeren `CapacityError` fırlatılması[cite: 1, 2].
  * Bozuk `magic`/header öneki, kesik/eksik kanal dizisi ve kapasiteyi aşan `ct_len` değerlerinde hata üretilmesi[cite: 1, 2].
* Modül belirlenen kapasite sınırlarına uygun şekilde veri gömüp birebir geri çıkarmakta ve tüm birim testlerini başarıyla geçmektedir[cite: 1, 2].

## Adım 5: CLI İskeleti ve Argüman Ayrıştırıcı
* `src/main.py`, `argparse` ile `keygen`, `embed`, `extract` ve `capacity` alt komutlarını tanımlar.
* Alt komutların dosya yolları, şifreleme modu, payload `k` değeri ve RSA anahtar yolları gibi temel argümanları ayrıştırılır; parola komut satırında verilmez, gerektiğinde `getpass` ile etkileşimli ve gizli biçimde alınır.
* `keygen` komutu RSA-2048 anahtar çifti üretir; PEM dosyalarını kaydeder, mevcut dosyaların üzerine yazmayı reddeder ve özel anahtar dosyasını `0600` izinleriyle sınırlar.
* `--protect-private-key` seçeneğinde parola terminalden gizli biçimde iki kez alınır ve eşleşmesi doğrulanır; parola komut satırı argümanı olarak kullanılmaz.
* `capacity IMAGE --mode {aes,rsa} --bits {1,2,3}` görsel ve header moduna göre şifreli payload kapasitesini hesaplayıp bayt cinsinden yazdırır; ayrıca AES-GCM tag'i için 16 bayt düşerek plaintext mesaj kapasitesini bildirir.
* `embed` boş olmayan dosya içeriğini alır; AES modunda parolayı `getpass` ile gizli ister, RSA modunda `--pubkey`/`--public-key` PEM anahtarını okur. AES-GCM ciphertext ve tag, `container.pack_header` ile oluşturulan tam header'ı AAD kullanarak üretilir ve `stego_module.embed_message` ile PNG'ye gömülür.
* RSA modunda AES-256 anahtarı rastgele üretilir ve alıcının RSA genel anahtarıyla sarılır; AES modu Argon2id ile paroladan 256-bit anahtar türetir. Her iki modda header'daki `ct_len`, ciphertext ile 16 baytlık GCM tag'inin toplam uzunluğudur.
* `extract` iki aşamalı header okuyucusuyla mod ve `k` değerini görüntüden alır; ayrıca `--bits` kabul etmez. AES modunda parola `getpass` ile istenir; RSA modunda `--privkey`/`--private-key` PEM anahtarı okunur ve şifreliyse anahtar parolası gizli olarak istenir. Header yeniden oluşturulup GCM AAD doğrulamasına verilir; plaintext `--output` dosyasına yazılır.
* Argüman ayrıştırma, keygen, capacity, AES/RSA embed ve extract round-trip, yanlış parola ve özel anahtar akışları `tests/test_cli.py` içinde test edilir.
