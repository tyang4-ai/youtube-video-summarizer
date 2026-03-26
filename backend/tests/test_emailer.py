from unittest.mock import patch, MagicMock
from app.services.emailer import encrypt_password, decrypt_password, send_summary_email


def test_encrypt_decrypt_roundtrip():
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    encrypted = encrypt_password("my_secret", key)
    assert encrypted != "my_secret"
    decrypted = decrypt_password(encrypted, key)
    assert decrypted == "my_secret"


@patch("app.services.emailer.smtplib.SMTP")
def test_send_email_calls_smtp(mock_smtp_cls, tmp_path):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    # Create a dummy PDF
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test content")

    send_summary_email(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        sender_email="sender@test.com",
        recipients=["recipient@test.com"],
        video_title="Test Video",
        channel_name="Test Channel",
        summary_text="A summary",
        video_url="https://youtube.com/watch?v=abc",
        pdf_path=str(pdf_path),
    )
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user", "pass")
    mock_smtp.send_message.assert_called_once()
