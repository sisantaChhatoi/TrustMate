"""Quick manual test: prints only the chat answer, no logs/warnings/progress bars.

A fresh random session is used by default on every run, so repeated manual
testing doesn't keep piling unrelated conversations into one giant, confusing
thread. Pass --session <id> to deliberately resume a specific one instead.

Usage:
    python -m src.rag.ask "Mujhe CBI se call aaya, digital arrest bola"   # one-shot
    python -m src.rag.ask                                                # interactive, keeps memory
    python -m src.rag.ask --stream "..."                                 # one-shot, streamed output
    python -m src.rag.ask --session cli-test "..."                       # resume a specific session
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
import warnings

os.environ.setdefault("HF_HOME", "D:/digital-arrest-shield/.cache/huggingface")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

from src.rag.chat import chat_turn, chat_turn_stream  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    stream = "--stream" in args
    if stream:
        args.remove("--stream")

    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    if "--session" in args:
        idx = args.index("--session")
        session_id = args[idx + 1]
        del args[idx : idx + 2]

    query = " ".join(args)
    print(f"(session: {session_id})")

    if stream and query:
        for delta in chat_turn_stream(session_id, query):
            print(delta, end="", flush=True)
        print()
    elif query:
        print(chat_turn(session_id, query))
    else:
        print("Interactive mode — Ctrl+C to quit.")
        while True:
            try:
                line = input("> ")
            except (KeyboardInterrupt, EOFError):
                break
            if line.strip():
                print(chat_turn(session_id, line))
