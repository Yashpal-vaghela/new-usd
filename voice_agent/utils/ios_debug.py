import json
import os
from datetime import datetime

# Temporary iOS audio debugging. When an iOS client connects with ?ios_test=meter (WS query debug=1), its meter samples
# and key server events are appended, one JSON object per line, to <project root>/ios_debug_logs/<start>_<id>.jsonl
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ios_debug_logs")


def ios_debug_log(session, event, **data):
    if not getattr(session, "ios_debug", False):
        return
    if not session.ios_debug_path:
        os.makedirs(LOG_DIR, exist_ok=True)
        session.ios_debug_path = os.path.join(LOG_DIR, f"{datetime.now():%Y%m%d_%H%M%S}_{id(session) & 0xffff:04x}.jsonl")
    line = {"t": datetime.now().isoformat(timespec="milliseconds"), "ev": event, **data}
    try:
        with open(session.ios_debug_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[WARN] ios_debug_log failed: {e}")
