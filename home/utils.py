import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)

# Emails are saved in the EmailOutbox table first, then ONE background worker
# per process sends them. Nothing is lost on crash/restart: pending rows are
# picked up again, and failed sends are retried with back-off.
MAX_ATTEMPTS = 20
POLL_SECONDS = 60
STUCK_AFTER = timedelta(minutes=10)

_wake = threading.Event()
_worker_lock = threading.Lock()
_worker_thread = None


def _build_message(to_email, subject, context_dict, connection=None):
    lines = ["New Form Submission Received\n"]
    for key, val in context_dict.items():
        lines.append(f"{key.capitalize()}: {val}")

    if isinstance(to_email, str):
        to_email = [to_email]

    return EmailMessage(
        subject=subject,
        body="\n".join(lines),
        from_email=settings.EMAIL_HOST_USER,
        to=to_email,
        connection=connection,
    )


def _send_now(to_email, subject, context_dict):
    connection = get_connection(timeout=getattr(settings, "EMAIL_TIMEOUT", 20))
    _build_message(to_email, subject, context_dict, connection=connection).send(fail_silently=False)


def _claim_next():
    """Atomically take one due email, so two processes never send the same one."""
    from django.db.models import Q
    from django.utils import timezone
    from .models import EmailOutbox

    now = timezone.now()
    # recover rows left in "sending" by a process that died mid-send
    EmailOutbox.objects.filter(
        status=EmailOutbox.STATUS_SENDING, updated_at__lt=now - STUCK_AFTER
    ).update(status=EmailOutbox.STATUS_PENDING)

    due = EmailOutbox.objects.filter(status=EmailOutbox.STATUS_PENDING).filter(
        Q(next_try_at__isnull=True) | Q(next_try_at__lte=now)
    ).order_by("created_at")
    for pk in due.values_list("pk", flat=True)[:5]:
        if EmailOutbox.objects.filter(pk=pk, status=EmailOutbox.STATUS_PENDING).update(
            status=EmailOutbox.STATUS_SENDING, updated_at=now
        ):
            return EmailOutbox.objects.get(pk=pk)
    return None


def _process_one():
    from django.utils import timezone
    from .models import EmailOutbox

    job = _claim_next()
    if job is None:
        return False
    try:
        _send_now(job.to_emails, job.subject, job.context)
        job.status = EmailOutbox.STATUS_SENT
        job.sent_at = timezone.now()
        job.last_error = ""
    except Exception as e:
        job.attempts += 1
        job.last_error = str(e)[:2000]
        if job.attempts >= MAX_ATTEMPTS:
            job.status = EmailOutbox.STATUS_FAILED
        else:
            job.status = EmailOutbox.STATUS_PENDING
            # 1, 2, 4, 8 ... minutes, capped at 1 hour
            job.next_try_at = timezone.now() + timedelta(minutes=min(2 ** (job.attempts - 1), 60))
        logger.error("Email %s failed (attempt %s): %s", job.pk, job.attempts, e)
    job.save()
    return True


def _email_worker():
    import time
    from django.db import close_old_connections

    while True:
        try:
            close_old_connections()
            while _process_one():
                time.sleep(1)  # gentle pace so Gmail does not rate-limit bursts
        except Exception as e:
            logger.error("Email worker error: %s", e)
        finally:
            close_old_connections()
        _wake.wait(POLL_SECONDS)
        _wake.clear()


def _ensure_worker():
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=_email_worker, name="email-worker", daemon=True)
            _worker_thread.start()


# Used when a caller passes no usable recipient
DEFAULT_RECIPIENTS = ["bhavinparmar005@gmail.com"]
DEFAULT_SUBJECT = "New Form Submission"

# Accepted argument names, so a caller using a different name never crashes a form
_TO_KEYS = ("to_email", "queue_mail", "to_emails", "to", "recipient_list", "recipients")
_SUBJECT_KEYS = ("subject",)
_CONTEXT_KEYS = ("context_dict", "context", "data", "message", "body")


def _pick(kwargs, keys):
    for key in keys:
        if kwargs.get(key) is not None:
            return kwargs[key]
    return None


def _clean_recipients(value):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return list(DEFAULT_RECIPIENTS)
    emails = [str(v).strip() for v in value if isinstance(v, str) and "@" in v]
    return emails or list(DEFAULT_RECIPIENTS)


def _clean_context(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(k): "" if v is None else str(v) for k, v in value.items()}
    return {"Message": str(value)}


def _normalize(args, kwargs):
    """Turn any calling style - positional or keyword, any of the accepted names - into
    (recipients, subject, context)."""
    args = list(args) + [None] * 3
    to_email = args[0] if args[0] is not None else _pick(kwargs, _TO_KEYS)
    subject = args[1] if args[1] is not None else _pick(kwargs, _SUBJECT_KEYS)
    context = args[2] if args[2] is not None else _pick(kwargs, _CONTEXT_KEYS)
    subject = str(subject).strip() if subject else DEFAULT_SUBJECT
    return _clean_recipients(to_email), subject[:500], _clean_context(context)


def queue_mail(*args, **kwargs):
    """Non-blocking and never raises: save email to outbox and wake the worker.

    Usual call: queue_mail(to_email=[...], subject="...", context_dict={...})
    """
    try:
        to_email, subject, context = _normalize(args, kwargs)
    except Exception as e:
        logger.error("Could not read email arguments: %s", e)
        return
    try:
        from .models import EmailOutbox
        EmailOutbox.objects.create(to_emails=to_email, subject=subject, context=context)
    except Exception as e:
        # DB unavailable: last resort, try sending directly in the worker thread
        logger.error("Could not save email to outbox, sending directly: %s", e)
        try:
            threading.Thread(target=_safe_direct_send, args=(to_email, subject, context), daemon=True).start()
        except Exception as e2:
            logger.error("Could not start direct email thread: %s", e2)
        return
    try:
        _ensure_worker()
        _wake.set()
    except Exception as e:
        logger.error("Could not start email worker: %s", e)


def _safe_direct_send(to_email, subject, context):
    try:
        _send_now(to_email, subject, context)
    except Exception as e:
        logger.error("Direct email send failed: %s", e)


def start_email_worker():
    """Called on app startup so emails pending from before a restart get sent."""
    try:
        _ensure_worker()
    except Exception as e:
        logger.error("Could not start email worker: %s", e)


def send_mail(*args, **kwargs):
    """Kept for backward compatibility; same as queue_mail (non-blocking, never raises)."""
    queue_mail(*args, **kwargs)
