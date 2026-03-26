import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from cryptography.fernet import Fernet


def encrypt_password(plain: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plain.encode()).decode()


def decrypt_password(cipher: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(cipher.encode()).decode()


def send_summary_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender_email: str,
    recipients: list[str],
    video_title: str,
    channel_name: str,
    summary_text: str,
    video_url: str,
    pdf_path: str,
) -> None:
    subject = f"[YT Summary] {video_title} — {channel_name}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    body = f"""New video summary available!

Video: {video_title}
Channel: {channel_name}
Link: {video_url}

Summary:
{summary_text}

Full timestamped summary attached as PDF.
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF
    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        with open(pdf_file, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header("Content-Disposition", "attachment", filename=pdf_file.name)
            msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
