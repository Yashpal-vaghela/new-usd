import os

# Limit native thread pools BEFORE numpy/cv2/torch load. On CloudLinux shared
# hosting every thread counts as a process (NPROC limit), so keep them at 1.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
os.environ.setdefault("GRPC_POLL_STRATEGY", "poll")

from hm.wsgi import application
