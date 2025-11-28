from django.core.mail import EmailMessage
from django.conf import settings

def send_mail(to_email, subject, context_dict):
    # Create body dynamically
    lines = ["New Form Submission Received\n"]

    for key, val in context_dict.items():
        lines.append(f"{key.capitalize()}: {val}")

    email_body = "\n".join(lines)

    email_msg = EmailMessage(
        subject=subject,
        body=email_body,
        from_email=settings.EMAIL_HOST_USER,
        to=[to_email],
    )
    email_msg.send(fail_silently=False)