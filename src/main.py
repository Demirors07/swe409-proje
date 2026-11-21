from __future__ import annotations

import argparse
from getpass import getpass
import os
from pathlib import Path
from typing import Sequence

from cryptography.exceptions import InvalidTag

from crypto_module import (
    decrypt_aes_gcm,
    decrypt_aes_gcm_with_key,
    derive_key,
    encrypt_aes_gcm_with_key,
    generate_rsa_keys,
    load_private_key,
    load_public_key,
    save_private_key,
    save_public_key,
    unwrap_aes_key,
    validate_plaintext,
    wrap_aes_key,
)
from container import pack_header
from stego_module import capacity as calculate_payload_capacity
from stego_module import embed_message, extract_message_from_image

_MODE_IDS = {"aes": 0x01, "rsa": 0x02}
_MODE_NAMES = {mode_id: name for name, mode_id in _MODE_IDS.items()}
_AES_GCM_TAG_BYTES = 16


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser and its keygen, embed, extract, and capacity commands."""
    parser = argparse.ArgumentParser(
        prog="stego",
        description="Encrypt data and hide it in an image.",
    )
    commands = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="{keygen,embed,extract,capacity}",
        required=True,
    )

    keygen = commands.add_parser(
        "keygen",
        help="Generate an RSA key pair.",
        description="Generate and save an RSA public/private key pair.",
    )
    keygen.add_argument(
        "--private-key",
        type=Path,
        required=True,
        metavar="PATH",
        help="Output path for the private PEM key.",
    )
    keygen.add_argument(
        "--public-key",
        type=Path,
        required=True,
        metavar="PATH",
        help="Output path for the public PEM key.",
    )
    keygen.add_argument(
        "--protect-private-key",
        action="store_true",
        help="Protect the private key with an interactively requested passphrase.",
    )

    embed = commands.add_parser(
        "embed",
        help="Embed a message file in an image.",
        description="Encrypt a message and embed it in a lossless PNG image.",
    )
    embed.add_argument("image", type=Path, help="Input cover image.")
    embed.add_argument("message", type=Path, help="File containing the message to embed.")
    embed.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        metavar="PATH",
        help="Output stego image path (saved as PNG).",
    )
    embed.add_argument(
        "--mode",
        choices=("aes", "rsa"),
        required=True,
        help="Encryption mode: password-based AES-GCM or RSA hybrid encryption.",
    )
    embed.add_argument(
        "--k",
        type=int,
        choices=(1, 2, 3),
        default=1,
        help="Payload bits embedded per color channel (default: 1). The header always uses k=1.",
    )
    embed.add_argument(
        "--public-key",
        "--pubkey",
        dest="public_key",
        type=Path,
        metavar="PATH",
        help="RSA recipient public PEM key (required when --mode=rsa).",
    )

    extract = commands.add_parser(
        "extract",
        help="Extract and decrypt a message from an image.",
        description="Extract the embedded payload and decrypt it.",
    )
    extract.add_argument("image", type=Path, help="Input stego image.")
    extract.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        metavar="PATH",
        help="Output path for the extracted plaintext.",
    )
    extract.add_argument(
        "--private-key",
        "--privkey",
        dest="private_key",
        type=Path,
        metavar="PATH",
        help="RSA recipient private PEM key (required for RSA-mode images).",
    )

    capacity = commands.add_parser(
        "capacity",
        help="Calculate the maximum payload size for an image.",
        description="Calculate payload capacity after reserving space for the selected header.",
    )
    capacity.add_argument("image", type=Path, help="Cover image to inspect.")
    capacity.add_argument(
        "--mode",
        choices=("aes", "rsa"),
        required=True,
        help="Header/encryption mode whose capacity should be calculated.",
    )
    capacity.add_argument(
        "--bits",
        type=int,
        choices=(1, 2, 3),
        required=True,
        metavar="{1,2,3}",
        help="Payload bits embedded per color channel.",
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments, optionally using an explicit argument sequence."""
    return build_parser().parse_args(argv)


def run_keygen(args: argparse.Namespace) -> None:
    """Generate an RSA-2048 key pair and save it as PEM files."""
    private_path: Path = args.private_key
    public_path: Path = args.public_key

    if private_path.suffix.lower() != ".pem" or public_path.suffix.lower() != ".pem":
        raise ValueError("Both key output paths must use the .pem extension.")
    if private_path.resolve() == public_path.resolve():
        raise ValueError("Private and public key paths must be different.")
    if private_path.exists() or public_path.exists():
        raise FileExistsError("Refusing to overwrite an existing key file.")

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    passphrase = None
    if args.protect_private_key:
        passphrase = getpass("Private key passphrase: ")
        if not passphrase:
            raise ValueError("Private key passphrase must not be empty.")
        confirmation = getpass("Confirm private key passphrase: ")
        if passphrase != confirmation:
            raise ValueError("Passphrases do not match.")

    private_key, public_key = generate_rsa_keys()
    save_private_key(private_key, str(private_path), password=passphrase)
    os.chmod(private_path, 0o600)
    save_public_key(public_key, str(public_path))

    print(f"RSA-2048 private key saved to: {private_path}")
    print(f"RSA-2048 public key saved to: {public_path}")


def run_capacity(args: argparse.Namespace) -> None:
    """Calculate and print encrypted-payload and plaintext message capacities."""
    payload_capacity = calculate_payload_capacity(
        args.image,
        mode=_MODE_IDS[args.mode],
        k=args.bits,
    )
    message_capacity = max(0, payload_capacity - _AES_GCM_TAG_BYTES)

    print(f"Maximum encrypted payload capacity: {payload_capacity} bytes")
    print(
        "Maximum plaintext message capacity: "
        f"{message_capacity} bytes (subtracting the {_AES_GCM_TAG_BYTES}-byte AES-GCM tag)"
    )


def run_embed(args: argparse.Namespace) -> Path:
    """Encrypt a non-empty message and embed it in a PNG image."""
    plaintext = args.message.read_bytes()
    validate_plaintext(plaintext)

    mode = _MODE_IDS[args.mode]
    nonce = os.urandom(12)
    ciphertext_length = len(plaintext) + _AES_GCM_TAG_BYTES

    if args.mode == "aes":
        password = getpass("Encryption passphrase: ")
        if not password:
            raise ValueError("Encryption passphrase must not be empty.")
        extra_data = os.urandom(16)
        key = derive_key(password, extra_data)
    else:
        if args.public_key is None:
            raise ValueError("--pubkey is required when --mode=rsa.")
        public_key = load_public_key(str(args.public_key))
        key = os.urandom(32)
        extra_data = wrap_aes_key(key, public_key)

    header = pack_header(mode, args.k, nonce, ciphertext_length, extra_data)
    ciphertext_and_tag = encrypt_aes_gcm_with_key(plaintext, key, nonce, aad=header)
    saved_path = embed_message(
        image_path=args.image,
        output_path=args.output,
        payload=ciphertext_and_tag,
        mode=mode,
        k=args.k,
        nonce=nonce,
        extra_data=extra_data,
    )
    print(f"Encrypted message embedded in: {saved_path}")
    return saved_path


def run_extract(args: argparse.Namespace) -> bytes:
    """Extract, authenticate, decrypt, save, and return a message from an image."""
    ciphertext, mode, k, nonce, extra_data = extract_message_from_image(args.image)
    header = pack_header(mode, k, nonce, len(ciphertext), extra_data)

    if mode == _MODE_IDS["aes"]:
        password = getpass("Decryption passphrase: ")
        if not password:
            raise ValueError("Decryption passphrase must not be empty.")
        plaintext = decrypt_aes_gcm(ciphertext, password, nonce, extra_data, aad=header)
    elif mode == _MODE_IDS["rsa"]:
        if args.private_key is None:
            raise ValueError("--privkey is required for an RSA-mode image.")
        try:
            private_key = load_private_key(str(args.private_key))
        except TypeError:
            passphrase = getpass("Private key passphrase: ")
            private_key = load_private_key(str(args.private_key), passphrase)
        key = unwrap_aes_key(extra_data, private_key)
        plaintext = decrypt_aes_gcm_with_key(ciphertext, key, nonce, aad=header)
    else:
        raise ValueError(f"Unsupported encryption mode: {mode}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(plaintext)
    print(
        f"Extracted {_MODE_NAMES[mode]} message ({len(plaintext)} bytes) "
        f"with k={k} to: {args.output}"
    )
    return plaintext


def main(argv: Sequence[str] | None = None) -> bytes | None:
    """Parse arguments and execute the commands that are currently implemented."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "keygen":
        try:
            run_keygen(args)
        except (FileExistsError, OSError, ValueError) as exc:
            parser.error(str(exc))
        return

    if args.command == "capacity":
        try:
            run_capacity(args)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return

    if args.command == "embed":
        try:
            run_embed(args)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return

    if args.command == "extract":
        try:
            return run_extract(args)
        except InvalidTag:
            parser.error("Message authentication failed: wrong passphrase/key or corrupted data.")
        except (OSError, TypeError, ValueError) as exc:
            parser.error(str(exc))
        return

    parser.error(
        f"'{args.command}' argument parsing is ready, but command execution "
        "has not been implemented yet"
    )


if __name__ == "__main__":
    main()
