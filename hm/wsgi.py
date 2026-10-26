"""
WSGI config for hm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

# Limit native thread pools BEFORE numpy/cv2/torch load. On CloudLinux shared
# hosting every thread counts as a process (NPROC limit), so keep them at 1.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
os.environ.setdefault("GRPC_POLL_STRATEGY", "poll")

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hm.settings')

application = get_wsgi_application()

# Send any emails still pending from before a restart
try:
    from home.utils import start_email_worker
    start_email_worker()
except Exception:
    pass
