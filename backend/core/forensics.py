import sys
import traceback
import json
import os
import uuid
import logging
from datetime import datetime, timezone
import inspect

logger = logging.getLogger("QLM.Forensics")

class CrashRecorder:
    """
    Captures full system state (stack trace, local variables) upon critical failure.
    """
    def __init__(self, dump_dir: str = "logs/crashes"):
        self.dump_dir = dump_dir
        if not os.path.exists(dump_dir):
            os.makedirs(dump_dir)

    def record_crash(self, exception: Exception, context: dict = None) -> str:
        """
        Snapshot the crash state to a JSON file.
        Returns the path to the dump file.
        """
        crash_id = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()

        # Get traceback info
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)

        # Capture locals from the frame where exception occurred
        # Be careful with sensitive data or unserializable objects
        local_vars = {}
        try:
            if exc_traceback:
                # Walk down to the last frame
                tb = exc_traceback
                while tb.tb_next:
                    tb = tb.tb_next
                frame = tb.tb_frame

                for k, v in frame.f_locals.items():
                    try:
                        # Attempt simple serialization
                        if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                            local_vars[k] = v
                        else:
                            local_vars[k] = str(v)
                    except Exception:
                        local_vars[k] = "<Unserializable>"
        except Exception as e:
            local_vars = {"error_capturing_locals": str(e)}

        report = {
            "crash_id": crash_id,
            "timestamp": timestamp,
            "exception_type": str(exc_type.__name__) if exc_type else "Unknown",
            "exception_message": str(exc_value) if exc_value else "Unknown",
            "traceback": tb_lines,
            "context_args": context or {},
            "local_variables": local_vars
        }

        filename = f"crash_{timestamp.replace(':','-')}_{crash_id}.json"
        filepath = os.path.join(self.dump_dir, filename)

        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
            logger.critical(f"Crash dump saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to write crash dump: {e}")
            return ""

# Singleton
crash_recorder = CrashRecorder()
