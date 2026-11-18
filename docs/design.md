# System Design and Methodology

## 1. Overview
This document defines the architectural design, cryptographic specifications, binary header layout, capacity constraints, error handling model, and data flow for the Hybrid Steganography & Cryptography application (SWE-409). The system combines authenticated encryption with Least Significant Bit (LSB) image steganography to ensure both confidentiality and visual imperceptibility.

---

## 2. Core Architectural Decisions

* **Symmetric Encryption:** AES-256-GCM (Galois/Counter Mode) providing authenticated encryption with a 12-byte random nonce and a 16-byte authentication tag.
* **Key Derivation Function (KDF):** Argon2id (for password-based mode `0x01`) using a 16-byte cryptographically secure random salt.
* **Asymmetric Key Wrapping:** RSA-2048 with OAEP padding (SHA-256) to wrap a randomly generated 256-bit AES session key (for hybrid mode `0x02`).
* **Steganography Technique:** Spatial-domain LSB embedding across RGB color channels (`R`, `G`, `B`) of lossless carrier images (PNG/BMP).
* **Bit Ordering:** **MSB-first** (Most Significant Bit first) when serializing bytes into bit streams and mapping them onto pixel LSB slots.
* **Two-Stage Read Architecture:** The header is strictly embedded using **$k = 1$** (1 LSB per channel), while the encrypted payload uses the user-selected **$k \in \{1, 2, 3\}$** specified inside the header.

---

## 3. Binary Header Schema

The header acts as a fixed-format metadata envelope embedded at the very beginning of the image's pixel channel stream.

* **Total Header Size ($H_{\text{bytes}}$):**
  * **40 bytes** in Password Mode (`mode = 0x01`)
  * **280 bytes** in RSA Hybrid Mode (`mode = 0x02`)

| Offset | Field Name | Size (Bytes) | Description |
| :--- | :--- | :---: | :--- |
| `0` | `magic` | 4 | Fixed protocol signature (`0x53 0x54 0x47 0x31` / ASCII `"STG1"`). |
| `4` | `version` | 1 | Protocol & KDF parameter version identifier (`0x01`). |
| `5` | `mode` | 1 | Encryption mode: `0x01` (AES-GCM + Argon2id) or `0x02` (RSA-OAEP + AES-GCM). |
| `6` | `k` | 1 | Number of LSBs per color channel used for the payload (`1`, `2`, or `3`). |
| `7` | `reserved` | 1 | Reserved byte for future alignment/flags (`0x00`). |
| `8` | `nonce` | 12 | Cryptographically random 96-bit nonce for AES-GCM. |
| `20` | `ct_len` | 4 | Big-endian unsigned integer (`uint32`) representing total byte length of `ciphertext + 16-byte GCM tag`. |
| `24` | `salt` | 16 | *(Mode `0x01` only)* Random 128-bit salt for Argon2id key derivation. |
| `24` | `wrapped_key` | 256 | *(Mode `0x02` only)* RSA-2048 OAEP-encrypted 32-byte AES session key. |

---

## 4. Capacity Calculation Model

For a carrier RGB image of width $W$ and height $H$, each pixel provides 3 independent color channels (`R`, `G`, `B`), yielding a total channel count of:

$$C_{\text{total}} = W \times H \times 3$$

Because the header is always embedded at $k = 1$, it consumes $H_{\text{bytes}} \times 8$ channels. The remaining channels each store $k$ bits of payload data. The maximum payload capacity in bytes is defined as:

$$\text{MaxPayloadBytes} = \left\lfloor \frac{((W \times H \times 3) - (H_{\text{bytes}} \times 8)) \times k}{8} \right\rfloor$$

*Note: Since AES-GCM appends a 16-byte authentication tag to the ciphertext, the maximum plaintext byte length is $\text{MaxPayloadBytes} - 16$.*

---

## 5. Error Handling Specification

The system defines four explicit exception types to enforce fail-fast validation and clear diagnostics:

1. **`EmptyMessageError`**: Raised prior to encryption if the input message or file payload is empty (`0` bytes).
2. **`CapacityError`**: Raised during embedding if the required `ct_len` exceeds $\text{MaxPayloadBytes}$ for the given carrier image dimensions and $k$ value.
3. **`InvalidHeader`**: Raised during extraction if the first 4 bytes do not match the `STG1` magic signature, or if `version`, `mode`, `k`, or `ct_len` values are malformed/out of bounds.
4. **`DecryptionError`**: Raised during extraction if AES-GCM tag verification fails (due to an incorrect password, mismatched RSA private key, or tampered stego image pixels).

---

## 6. Operational Data Flows

### 6.1 Embedding Flow (`embed`)
1. **Input Validation:** Verify the plaintext payload is non-empty (`EmptyMessageError` if empty) and $k \in \{1, 2, 3\}$.
2. **Cryptographic Processing:**
   * Generate a 12-byte random `nonce`.
   * *If Mode `0x01`:* Generate a 16-byte random `salt` and derive a 32-byte key via Argon2id.
   * *If Mode `0x02`:* Generate a random 32-byte session key and encrypt it with the recipient's RSA public key (`wrapped_key`).
   * Encrypt the plaintext using AES-256-GCM to produce `ciphertext || tag` and record its byte length in `ct_len`.
3. **Capacity Check:** Compute $\text{MaxPayloadBytes}$ using $W$, $H$, $H_{\text{bytes}}$, and $k$. Raise `CapacityError` if `ct_len > MaxPayloadBytes`.
4. **Header Serialization:** Pack `magic`, `version`, `mode`, `k`, `reserved`, `nonce`, `ct_len`, and `salt`/`wrapped_key` into a contiguous byte buffer.
5. **Two-Stage LSB Embedding (MSB-first):**
   * Embed the header bit stream into the first $H_{\text{bytes}} \times 8$ RGB channels using **$k = 1$**.
   * Embed the `ciphertext || tag` bit stream into subsequent RGB channels using the selected **$k$**.
6. **Output:** Save the modified pixel array to a lossless image format (PNG).

### 6.2 Extraction Flow (`extract`)
1. **Stage 1 — Partial Header Read ($k = 1$):** Read the first 64 bits (8 bytes) from the image's RGB channels at $k = 1$ (MSB-first).
2. **Header Validation:** Verify `magic == b"STG1"`, `version == 0x01`, `mode in {0x01, 0x02}`, and `k in {1, 2, 3}`. Raise `InvalidHeader` on any mismatch.
3. **Stage 2 — Full Header Read ($k = 1$):** Based on `mode`, read the remaining 32 bytes (AES) or 272 bytes (RSA) at $k = 1$ to obtain `nonce`, `ct_len`, and `salt`/`wrapped_key`. Validate that `ct_len` fits within the image's remaining capacity (`InvalidHeader` if out of bounds).
4. **Payload Extraction:** Read `ct_len * 8` bits from the subsequent RGB channels using the extracted **$k$** value (MSB-first) and reconstruct `ciphertext || tag`.
5. **Cryptographic Decryption & Verification:**
   * Re-derive the 32-byte key via Argon2id (Mode `0x01`) or unwrap the session key via RSA private key (Mode `0x02`).
   * Decrypt and verify the GCM authentication tag using `nonce`. Raise `DecryptionError` if authentication fails.
6. **Output:** Return the verified plaintext bytes.
