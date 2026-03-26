import resend
from pathlib import Path
from cryptography.fernet import Fernet
import base64


def encrypt_password(plain: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plain.encode()).decode()


def decrypt_password(cipher: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(cipher.encode()).decode()


def send_summary_email(
    resend_api_key: str,
    sender_email: str,
    recipients: list[str],
    video_title: str,
    channel_name: str,
    summary_text: str,
    video_url: str,
    pdf_path: str,
    **kwargs,  # Accept and ignore legacy SMTP params
) -> None:
    resend.api_key = resend_api_key

    body = f"""New video summary available!

Video: {video_title}
Channel: {channel_name}
Link: {video_url}

Summary:
{summary_text}

Full timestamped summary attached as PDF.
"""

    params = {
        "from": sender_email,
        "to": recipients,
        "subject": f"[YT Summary] {video_title} — {channel_name}",
        "text": body,
    }

    # Attach PDF if it exists
    pdf_file = Path(pdf_path) if pdf_path else None
    if pdf_file and pdf_file.is_file():
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()
        params["attachments"] = [
            {
                "filename": pdf_file.name,
                "content": list(pdf_data),
            }
        ]

    resend.Emails.send(params)
