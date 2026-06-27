import logging
import os
import sys
import io


def _make_utf8_console_handler(level=logging.INFO):
    """Create a StreamHandler that writes UTF-8 (replace errors) to the console.

    Falls back to the default StreamHandler if stdout.buffer is unavailable.
    """
    try:
        buf = sys.stdout.buffer
        stream = io.TextIOWrapper(buf, encoding="utf-8", errors="replace", line_buffering=True)
        handler = logging.StreamHandler(stream)
    except Exception:
        handler = logging.StreamHandler()
    handler.setLevel(level)
    return handler


def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # File Handler (explicit UTF-8)
        os.makedirs('logs', exist_ok=True)
        fh = logging.FileHandler('logs/agent.log', encoding='utf-8')
        fh.setLevel(logging.DEBUG)

        # Console Handler (UTF-8 safe)
        ch = _make_utf8_console_handler(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger
