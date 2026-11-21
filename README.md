# SWE-409 Hybrid Steganography and Cryptography

Python CLI for encrypting a message and hiding the encrypted payload in a
lossless PNG image. AES mode uses AES-256-GCM with an Argon2id-derived key;
RSA mode wraps a random AES-256 key with the recipient's RSA public key.

## Setup

```bash
source .venv/bin/activate
```

The project dependencies are listed in `requirements.txt`. Run the test suite
from the repository root with:

```bash
pytest
```

## CLI usage

All commands are run from the repository root:

```bash
python src/main.py --help
```

### Generate an RSA key pair

```bash
python src/main.py keygen \
  --private-key keys/private.pem \
  --public-key keys/public.pem
```

To encrypt the private PEM file with a passphrase (prompted without echo):

```bash
python src/main.py keygen \
  --private-key keys/private.pem \
  --public-key keys/public.pem \
  --protect-private-key
```

The command refuses to overwrite existing key files. Keep the private key
secure; its file permissions are restricted to the owner.

### Check image capacity

Specify the encryption mode and payload bits per color channel (`1`, `2`, or
`3`):

```bash
python src/main.py capacity samples/cover.png --mode aes --bits 2
python src/main.py capacity samples/cover.png --mode rsa --bits 3
```

The output reports encrypted payload capacity and the estimated maximum
plaintext size after reserving 16 bytes for the AES-GCM authentication tag.

### Embed a message with AES

```bash
python src/main.py embed samples/cover.png message.txt \
  --output results/secret.png \
  --mode aes \
  --k 2
```

The AES passphrase is requested interactively and is not included in the
command-line arguments.

### Embed a message with RSA

```bash
python src/main.py embed samples/cover.png message.txt \
  --output results/secret.png \
  --mode rsa \
  --pubkey keys/public.pem \
  --k 2
```

`--public-key` is also accepted as an alias for `--pubkey`.

### Extract and decrypt a message

The embedded header supplies the mode and `k`; extraction does not take a
`--bits` option.

AES mode prompts for the passphrase:

```bash
python src/main.py extract results/secret.png \
  --output results/message.txt
```

RSA mode uses the matching private key:

```bash
python src/main.py extract results/secret.png \
  --output results/message.txt \
  --privkey keys/private.pem
```

`--private-key` is also accepted. If the private PEM is passphrase-protected,
the passphrase is requested interactively. Extracted plaintext is written to
the requested output file; a wrong passphrase/key or altered authenticated
data causes an authentication error.

## Experiment results

Experiment datasets and figures are stored under `results/`. The detailed
methodology, tables, and interpretation notes are in
[`EXPERIMENT_RESULTS.md`](EXPERIMENT_RESULTS.md); the CSV files provide
machine-readable copies of the capacity matrix, visual-quality metrics,
steganalysis, performance, robustness, and security results. Each table and
figure also has a short interpretation note in [`DECISIONS.md`](DECISIONS.md).
