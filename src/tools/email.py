import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_notification_email(subject: str, body: str, recipient: str = None, attachment_path: str = None) -> str:
    """Sends an email notification or application to the target recipient.
    """
    # Load configuration
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    
    default_recipient = recipient or os.getenv("NOTIFICATION_RECEIVER")
    
    if not default_recipient:
        # Fallback logging if no receiver specified
        print(f"⚠️ [MOCK EMAIL] No recipient address configured. Draft saved locally.\nSubject: {subject}\nRecipient: {recipient or 'N/A'}")
        return "Mock email saved (no receiver specified)."
        
    if not smtp_server or not smtp_username or not smtp_password:
        # Fallback mock logging if SMTP credentials are not present
        print(f"⚠️ [MOCK EMAIL] SMTP credentials missing. Logged application draft:\nTo: {default_recipient}\nSubject: {subject}\nAttachment: {attachment_path or 'None'}")
        
        # Save a copy locally on desktop for user visibility
        try:
            save_path = os.path.expanduser(f"~/Desktop/draft_email_{int(datetime.now().timestamp())}.txt")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"To: {default_recipient}\nSubject: {subject}\n\n{body}")
            return f"Mock email drafted and saved on Desktop at {save_path}"
        except Exception as e:
            return f"Mock email drafted. Desktop write failed: {str(e)}"

    try:
        # Prepare message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = default_recipient
        msg['Subject'] = subject
        
        # Attach email body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Attach resume/file if present
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf" if attachment_path.endswith(".pdf") else "octet-stream")
                attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attach)
                
        # Send via SMTP
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        if use_tls:
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, default_recipient, msg.as_string())
        server.quit()
        
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
