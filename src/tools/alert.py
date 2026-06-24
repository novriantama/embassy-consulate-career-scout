import os

def send_local_alert(title: str, message: str) -> str:
    """Sends a native Mac OS notification banner.
    """
    try:
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')
        cmd = f'osascript -e \'display notification "{escaped_message}" with title "{escaped_title}"\''
        os.system(cmd)
        return "Notification sent successfully."
    except Exception as e:
        return f"Failed to send native notification: {str(e)}"
