import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image

from container import pack_header
from crypto_module import (
    decrypt_aes_gcm,
    generate_rsa_keys,
    load_private_key,
    load_public_key,
    save_private_key,
    save_public_key,
    unwrap_aes_key,
)
from main import build_parser, main, parse_args
from stego_module import capacity, extract_message_from_image


def test_parser_defines_all_requested_commands() -> None:
    parser = build_parser()

    help_text = parser.format_help()
    for command in ("keygen", "embed", "extract", "capacity"):
        assert command in help_text


def test_keygen_arguments() -> None:
    args = parse_args(
        [
            "keygen",
            "--private-key",
            "private.pem",
            "--public-key",
            "public.pem",
            "--protect-private-key",
        ]
    )

    assert args.command == "keygen"
    assert str(args.private_key) == "private.pem"
    assert str(args.public_key) == "public.pem"
    assert args.protect_private_key is True


def test_embed_arguments() -> None:
    args = parse_args(
        [
            "embed",
            "cover.png",
            "message.bin",
            "--output",
            "stego.png",
            "--mode",
            "rsa",
            "--k",
            "3",
            "--public-key",
            "recipient.pem",
        ]
    )

    assert args.command == "embed"
    assert str(args.image) == "cover.png"
    assert str(args.message) == "message.bin"
    assert str(args.output) == "stego.png"
    assert args.mode == "rsa"
    assert args.k == 3
    assert str(args.public_key) == "recipient.pem"
    pubkey_alias_args = parse_args(
        [
            "embed",
            "cover.png",
            "message.bin",
            "--output",
            "stego.png",
            "--mode",
            "rsa",
            "--pubkey",
            "recipient.pem",
        ]
    )
    assert str(pubkey_alias_args.public_key) == "recipient.pem"


def test_extract_arguments() -> None:
    args = parse_args(
        ["extract", "stego.png", "--output", "plaintext.bin", "--private-key", "private.pem"]
    )

    assert args.command == "extract"
    assert str(args.image) == "stego.png"
    assert str(args.output) == "plaintext.bin"
    assert str(args.private_key) == "private.pem"


@pytest.mark.parametrize(("mode", "mode_id"), [("aes", 0x01), ("rsa", 0x02)])
@pytest.mark.parametrize("bits", [1, 2, 3])
def test_capacity_command_prints_encrypted_and_plaintext_limits(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
    mode: str,
    mode_id: int,
    bits: int,
) -> None:
    image_path = tmp_path / "cover.png"
    Image.new("RGB", (80, 72), color=(127, 127, 127)).save(image_path)
    expected_payload_capacity = capacity(image_path, mode_id, bits)
    expected_message_capacity = max(0, expected_payload_capacity - 16)

    args = parse_args(["capacity", str(image_path), "--mode", mode, "--bits", str(bits)])
    assert args.command == "capacity"
    assert args.image == image_path
    assert args.mode == mode
    assert args.bits == bits

    main(["capacity", str(image_path), "--mode", mode, "--bits", str(bits)])
    output = capsys.readouterr().out
    assert f"Maximum encrypted payload capacity: {expected_payload_capacity} bytes" in output
    assert f"Maximum plaintext message capacity: {expected_message_capacity} bytes" in output


def test_parser_rejects_unsupported_capacity_bits() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["capacity", "cover.png", "--mode", "aes", "--bits", "4"])

    assert exc_info.value.code == 2


def test_capacity_requires_bits() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["capacity", "cover.png", "--mode", "aes"])

    assert exc_info.value.code == 2


def test_parser_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args([])

    assert exc_info.value.code == 2


def test_keygen_creates_rsa_pem_files_and_restricts_private_key_permissions(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "nested" / "private.pem"
    public_path = tmp_path / "nested" / "public.pem"

    main(
        [
            "keygen",
            "--private-key",
            str(private_path),
            "--public-key",
            str(public_path),
        ]
    )

    private_key = load_private_key(str(private_path))
    public_key = load_public_key(str(public_path))
    assert private_key.key_size == public_key.key_size == 2048
    assert private_key.public_key().public_numbers() == public_key.public_numbers()
    assert private_path.stat().st_mode & 0o777 == 0o600
    assert "RSA-2048 private key saved" in capsys.readouterr().out


def test_keygen_protects_private_key_with_confirmed_passphrase(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    passphrases = iter(("correct horse", "correct horse"))
    monkeypatch.setattr("main.getpass", lambda _prompt: next(passphrases))
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"

    main(
        [
            "keygen",
            "--private-key",
            str(private_path),
            "--public-key",
            str(public_path),
            "--protect-private-key",
        ]
    )

    assert load_private_key(str(private_path), "correct horse").key_size == 2048


@pytest.mark.parametrize(
    ("private_name", "public_name", "passphrases", "error"),
    [
        ("private.key", "public.pem", (), ".pem extension"),
        ("same.pem", "same.pem", (), "must be different"),
        ("private.pem", "public.pem", ("first", "second"), "do not match"),
        ("private.pem", "public.pem", ("",), "must not be empty"),
    ],
)
def test_keygen_rejects_invalid_paths_or_passphrase(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    private_name: str,
    public_name: str,
    passphrases: tuple[str, ...],
    error: str,
) -> None:
    responses = iter(passphrases)
    monkeypatch.setattr("main.getpass", lambda _prompt: next(responses))
    args = [
        "keygen",
        "--private-key",
        str(tmp_path / private_name),
        "--public-key",
        str(tmp_path / public_name),
    ]
    if passphrases:
        args.append("--protect-private-key")

    with pytest.raises(SystemExit) as exc_info:
        main(args)

    assert exc_info.value.code == 2
    assert error in capsys.readouterr().err


def test_keygen_refuses_to_overwrite_existing_keys(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    private_path.write_text("existing private key")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "keygen",
                "--private-key",
                str(private_path),
                "--public-key",
                str(public_path),
            ]
        )

    assert exc_info.value.code == 2
    assert "Refusing to overwrite" in capsys.readouterr().err
    assert private_path.read_text() == "existing private key"
    assert not public_path.exists()


def test_extract_does_not_accept_manual_bits_argument() -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["extract", "stego.png", "--output", "plaintext.bin", "--bits", "3"])

    assert exc_info.value.code == 2


def test_embed_aes_encrypts_with_embedded_header_as_aad(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    output_path = tmp_path / "stego.png"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    plaintext = b"secret AES message"
    message_path.write_bytes(plaintext)
    monkeypatch.setattr("main.getpass", lambda _prompt: "test passphrase")

    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(output_path),
            "--mode",
            "aes",
            "--k",
            "2",
        ]
    )

    ciphertext, mode, k, nonce, salt = extract_message_from_image(output_path)
    header = pack_header(mode, k, nonce, len(ciphertext), salt)
    assert mode == 0x01
    assert k == 2
    assert decrypt_aes_gcm(ciphertext, "test passphrase", nonce, salt, aad=header) == plaintext
    assert "Encrypted message embedded" in capsys.readouterr().out


def test_embed_rsa_encrypts_and_wraps_key_with_embedded_header_as_aad(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.bin"
    public_key_path = tmp_path / "recipient.pem"
    output_path = tmp_path / "stego.png"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    plaintext = b"secret RSA hybrid message"
    message_path.write_bytes(plaintext)
    private_key, public_key = generate_rsa_keys()
    save_public_key(public_key, str(public_key_path))

    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(output_path),
            "--mode",
            "rsa",
            "--k",
            "3",
            "--pubkey",
            str(public_key_path),
        ]
    )

    ciphertext, mode, k, nonce, wrapped_key = extract_message_from_image(output_path)
    header = pack_header(mode, k, nonce, len(ciphertext), wrapped_key)
    aes_key = unwrap_aes_key(wrapped_key, private_key)
    assert mode == 0x02
    assert k == 3
    assert AESGCM(aes_key).decrypt(nonce, ciphertext, header) == plaintext
    assert "Encrypted message embedded" in capsys.readouterr().out


@pytest.mark.parametrize("message", [b"", b" \t\r\n"])
def test_embed_rejects_empty_or_whitespace_message(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    message: bytes,
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "empty.txt"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(message)
    monkeypatch.setattr("main.getpass", lambda _prompt: "test passphrase")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "embed",
                str(image_path),
                str(message_path),
                "--output",
                str(tmp_path / "stego.png"),
                "--mode",
                "aes",
            ]
        )

    assert exc_info.value.code == 2
    assert "boş olamaz" in capsys.readouterr().err


def test_embed_rsa_requires_public_key(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(b"message")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "embed",
                str(image_path),
                str(message_path),
                "--output",
                str(tmp_path / "stego.png"),
                "--mode",
                "rsa",
            ]
        )

    assert exc_info.value.code == 2
    assert "--pubkey is required" in capsys.readouterr().err


def test_extract_aes_authenticates_header_and_writes_plaintext(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    stego_path = tmp_path / "stego.png"
    plaintext_path = tmp_path / "nested" / "plaintext.txt"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(b"round-trip through CLI")
    passphrases = iter(("correct password", "correct password"))
    monkeypatch.setattr("main.getpass", lambda _prompt: next(passphrases))

    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(stego_path),
            "--mode",
            "aes",
            "--k",
            "2",
        ]
    )
    plaintext = main(
        [
            "extract",
            str(stego_path),
            "--output",
            str(plaintext_path),
        ]
    )

    assert plaintext == b"round-trip through CLI"
    assert plaintext_path.read_bytes() == b"round-trip through CLI"
    output = capsys.readouterr().out
    assert "Extracted aes message" in output
    assert "k=2" in output


def test_extract_rsa_reads_privkey_alias_and_decrypts_with_protected_key(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    public_key_path = tmp_path / "recipient.pem"
    private_key_path = tmp_path / "private.pem"
    stego_path = tmp_path / "stego.png"
    plaintext_path = tmp_path / "plaintext.txt"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(b"RSA encrypted CLI message")
    private_key, public_key = generate_rsa_keys()
    save_private_key(private_key, str(private_key_path), password="private passphrase")
    save_public_key(public_key, str(public_key_path))
    monkeypatch.setattr("main.getpass", lambda _prompt: "private passphrase")

    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(stego_path),
            "--mode",
            "rsa",
            "--pubkey",
            str(public_key_path),
            "--k",
            "3",
        ]
    )
    main(
        [
            "extract",
            str(stego_path),
            "--output",
            str(plaintext_path),
            "--privkey",
            str(private_key_path),
        ]
    )

    assert plaintext_path.read_bytes() == b"RSA encrypted CLI message"


def test_extract_reports_authentication_failure_for_wrong_password(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    stego_path = tmp_path / "stego.png"
    output_path = tmp_path / "plaintext.txt"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(b"authenticated data")
    passphrases = iter(("correct password", "wrong password"))
    monkeypatch.setattr("main.getpass", lambda _prompt: next(passphrases))

    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(stego_path),
            "--mode",
            "aes",
        ]
    )
    with pytest.raises(SystemExit) as exc_info:
        main(["extract", str(stego_path), "--output", str(output_path)])

    assert exc_info.value.code == 2
    assert "Message authentication failed" in capsys.readouterr().err
    assert not output_path.exists()


def test_extract_rsa_requires_private_key(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    image_path = tmp_path / "cover.png"
    message_path = tmp_path / "message.txt"
    stego_path = tmp_path / "stego.png"
    Image.new("RGB", (128, 128), color=(127, 127, 127)).save(image_path)
    message_path.write_bytes(b"RSA message")
    _, public_key = generate_rsa_keys()
    public_key_path = tmp_path / "recipient.pem"
    save_public_key(public_key, str(public_key_path))
    main(
        [
            "embed",
            str(image_path),
            str(message_path),
            "--output",
            str(stego_path),
            "--mode",
            "rsa",
            "--pubkey",
            str(public_key_path),
        ]
    )

    with pytest.raises(SystemExit) as exc_info:
        main(["extract", str(stego_path), "--output", str(tmp_path / "out.txt")])

    assert exc_info.value.code == 2
    assert "--privkey is required" in capsys.readouterr().err
