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














