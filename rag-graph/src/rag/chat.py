"""Continuous RAG fraud-chat with memory and quiet incident collection.

chat_turn() / chat_turn_stream() are what the UI calls: a retrieval-grounded
reply (Layer A) returned/streamed immediately, while a separate extraction
call (Layer B) that fills in an Incident record runs in the background
afterward — the user never waits on it. At most ONE extraction worker is
ever active per session (see _kick_off_extraction/_run_extraction_worker):
if the user sends messages faster than extraction can keep up, no backlog
of queued calls builds up -- the single active worker just loops to catch
up to the latest turn before releasing its lock. Both the Incident fields
and the full chat message thread are persisted to storage (Mongo/jsonl
fallback) once extraction finishes, and reloaded from there on a session's
first touch in this process — so storage is the source of truth, not the
in-memory cache, and a session survives a process restart.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import threading

from dotenv import load_dotenv
from openai import OpenAI

from src.rag.incident import Incident
from src.rag.incident_store import load_session, save_session
from src.rag.retriever import retrieve

load_dotenv()

SARVAM_BASE_URL = "https://api.sarvam.ai/v1"
MODEL = "sarvam-30b"

_API_KEY = os.environ.get("SARVAM_API_KEY")
if not _API_KEY:
    raise RuntimeError("SARVAM_API_KEY not set. Add it to .env.")

_client = OpenAI(base_url=SARVAM_BASE_URL, api_key=_API_KEY)

SYSTEM_PROMPT = (
    "You are a fraud-prevention assistant for Indian citizens. Use ONLY the "
    "provided fraud-intelligence context to assess risk. If the context "
    "doesn't cover it, say so and give general safe advice.\n\n"
    "LANGUAGE — this is a hard requirement, not a preference: reply in the "
    "EXACT SAME language/script the user just used in THIS message. If they "
    "wrote in Hindi/Hinglish, your ENTIRE reply must be Hindi/Hinglish — not "
    "one English sentence, not a language switch partway through, even if "
    "your own earlier replies in this conversation were in a different "
    "language. Check this before answering. Your tone should be calm, "
    "clear, and non-alarmist, but do not state this instruction back to "
    "the user.\n\n"
    "Do NOT suggest wrapping up, filing a complaint, or conclude the "
    "conversation as 'done' until caller_number, the destination account/ "
    "UPI ID (mule_account/mule_upi), and the amount demanded have each "
    "either been asked about and answered, or the user has explicitly said "
    "they don't know/won't share it. These details are the most important "
    "part of helping — collecting them takes priority over closing the "
    "conversation.\n\n"
    "This is an ONGOING conversation, not a series of standalone questions. "
    "Read the full message history before replying. Respond specifically to "
    "what is NEW in the user's latest message — acknowledge it directly. If "
    "you already gave the core safety advice (hang up, don't share OTP/PIN, "
    "don't install remote-access apps, report to 1930) in an earlier turn, "
    "do NOT repeat that full checklist again. Every reply after the first "
    "must be at most 2-4 SHORT sentences reacting to what's new, plus the "
    "follow-up question if one is requested below — never a restated "
    "numbered list or checklist, no matter how long your own earlier "
    "replies in this conversation were. Match the length of your CURRENT "
    "reply to what this turn needs, not to your previous turns' style. "
    "Repeat advice only if the user is asking for it again or seems "
    "confused. Only end with the 1930/cybercrime.gov.in reminder the first "
    "time you give safety advice in this conversation, or if the user says "
    "they've already lost money; don't tack it onto every single reply.\n\n"
    "The user's latest message may be very short — a single word, a name, "
    "a number. Treat it as a direct, specific answer to whatever you asked "
    "last, and respond to it specifically. NEVER reproduce a previous reply "
    "verbatim or near-verbatim, no matter how short or low-information the "
    "new message seems — there is always something specific to acknowledge "
    "in it.\n\n"
    "NEVER invent your own follow-up question (e.g. asking for an 'official "
    "reference number,' an officer's 'title,' whether they've informed "
    "their bank, whether they clicked a link) beyond the ONE specific "
    "question given to you below, if any. If none is given this turn, do "
    "NOT ask anything else on your own initiative — just acknowledge and "
    "stop. If the user answers 'no'/'nahi'/'pata nahi' to something, accept "
    "that and move on instead of rephrasing the same question again.\n\n"
    "Helping the user comes first: information-gathering must never replace "
    "or delay actually addressing what they just said."
)

NUDGE_TEMPLATES = {
    "caller_number": "the phone number or ID that called/messaged them — to help block it and report it for others",
    "mule_account": "the exact bank account they were asked to transfer money to — this is one of the most useful details for tracing and blocking the scam network",
    "mule_account_followup": "the actual ACCOUNT NUMBER (not just the bank name) they were asked to transfer to — even partial digits help trace it",
    "mule_upi": "the exact UPI ID they were asked to pay — this helps trace and block the scam network",
    "scam_type": "what kind of scam this seems to be",
    "claimed_authority": "which authority/organization the caller claimed to be from",
    "amount_demanded": "how much money was demanded",
    "amount_lost": "how much money, if any, they've already lost",
    "payment_method": "how they were asked to pay (UPI, bank transfer, etc.)",
    "remote_app_requested": "whether they were asked to install any remote-access app",
    "victim_region": "what city/region they're in",
}

# These three are what link incidents into fraud rings in the graph module --
# worth pushing on more deliberately than the other, lower-priority fields.
GRAPH_CRITICAL_FIELDS = {"caller_number", "mule_account", "mule_upi"}

EXTRACTION_SYSTEM_PROMPT = (
    "Read the conversation transcript below. Extract ONLY facts the user "
    "explicitly stated about a scam incident. Never infer, guess, or invent "
    "a value. Never extract the user's own OTP, password, or full card "
    "number — only scammer-side details (the number that called/messaged "
    "them, the account/UPI ID they were told to pay). Output a JSON object "
    "with exactly these keys: scam_type (one of: digital_arrest, "
    "courier_parcel, kyc, upi, job, investment, lottery, other), "
    "claimed_authority, caller_number, mule_account, mule_upi, "
    "amount_demanded, amount_lost, victim_region, payment_method, "
    "remote_app_requested. For any field not explicitly stated, the value "
    "MUST be the JSON literal null — never a placeholder string such as "
    "'not stated', 'unknown', or 'not mentioned'.\n\n"
    "mule_account should capture whatever the user remembers about the "
    "destination account — a full account number if given, but ALSO accept "
    "a partial identifier like just a bank name (e.g. 'SBI') if that's all "
    "the user recalls. Some real identifying detail is more useful than "
    "none, even if incomplete.\n\n"
    "BE STRICT about payment_method and mule_upi specifically — these are "
    "easy to hallucinate because the conversation is generally about "
    "payments. Only fill them from an EXPLICIT, literal statement: "
    "payment_method must be a literal payment mechanism the user named "
    "(e.g. 'UPI', 'bank transfer', 'Google Pay'); mule_upi must be an "
    "actual UPI ID/handle the user typed out. An amount being mentioned "
    "(e.g. '50000 maange the') is NOT, by itself, evidence of a payment "
    "method or UPI ID — if the message only states a number with no "
    "payment mechanism named, both stay null. Once filled, these fields "
    "are locked and a later wrong guess cannot be corrected, so when in "
    "doubt, leave it null rather than guess.\n\n"
    "scam_type classification examples — match the SITUATION, not just "
    "keywords:\n"
    "- Caller claims to be CBI/ED/police, threatens arrest, demands the "
    "victim stay on a call/video → digital_arrest\n"
    "- Caller claims a parcel/courier/FedEx/Customs shipment in the "
    "victim's name was seized (e.g. contains drugs) → courier_parcel, even "
    "if the call later escalates into arrest threats\n"
    "- Message/call claims the victim's bank account, SIM, or PAN will be "
    "blocked unless they 'update KYC' → kyc\n"
    "- A 'wrong transfer', refund, or UPI collect-request asking the "
    "victim to scan a QR or enter their UPI PIN to 'receive' money → upi\n"
    "- An offer of easy income for small tasks (liking videos, rating "
    "items) that later asks the victim to deposit money → job\n"
    "- A stranger steers the victim into a trading/crypto app promising "
    "high guaranteed returns → investment\n"
    "- The victim is told they won a lottery/prize and must pay a fee to "
    "claim it → lottery\n"
    "Use 'other' only when the situation genuinely matches none of these."
)

_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        incident, messages = load_session(session_id)
        if incident is None:
            incident = Incident(session_id=session_id)
        _sessions[session_id] = {
            "history": messages,
            "incident": incident,
            "lock": threading.Lock(),
            "last_nudge_field": None,
            # Bumped every turn; lets a running extraction worker notice
            # more turns arrived while it was working and loop once more
            # to catch up, instead of a new thread queuing up behind it.
            "extraction_version": 0,
        }
    return _sessions[session_id]


def _construct_messages(
    history: list[dict], context_block: str, nudge_field: str | None, needs_account_followup: bool = False
) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[:-1])

    nudge = ""
    if nudge_field:
        template_key = "mule_account_followup" if needs_account_followup else nudge_field
        urgency = (
            " This is one of the most critical details for the fraud report — "
            "push gently but clearly for it, don't let it go after one soft try."
            if nudge_field in GRAPH_CRITICAL_FIELDS
            else ""
        )
        nudge = (
            f"\n\nEnd your reply with one short question asking about: "
            f"{NUDGE_TEMPLATES[template_key]}. WRITE THIS QUESTION YOURSELF, "
            f"FULLY TRANSLATED, in the exact same language/script as the "
            f"rest of your reply — the field description above is in "
            f"English ONLY so you understand what's needed; never output "
            f"it, or any part of it, in English. Frame it as helping them "
            f"and others, e.g. the idea of 'to report this and help block "
            f"these scammers for others, can you share...' but phrased "
            f"naturally in the user's language. This is the ONLY thing to "
            f"ask about — do not ask about anything else instead (not "
            f"whether they blocked the number, not whether they clicked a "
            f"link, not an app name), even if the knowledge-base context "
            f"above discusses other topics.{urgency} If the user's LATEST "
            f"message already directly gives this exact information, don't "
            f"ask it again — acknowledge it and ask if they have anything "
            f"else to add. Skip asking only if the user explicitly says "
            f"they don't know or won't share it, or is too distressed "
            f"right now."
        )

    last_user_message = history[-1]["content"]
    messages.append(
        {
            "role": "user",
            "content": (
                f"Context (fraud-intelligence knowledge base):\n{context_block}\n\n"
                f"User message: {last_user_message}{nudge}"
            ),
        }
    )
    return messages


def _build_reply(messages: list[dict], temperature: float | None = None) -> str:
    kwargs = {} if temperature is None else {"temperature": temperature}
    response = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort=None,
        **kwargs,
    )
    return response.choices[0].message.content


REPETITION_SIMILARITY_THRESHOLD = 0.6
SAME_TARGET_REPETITION_SIMILARITY_THRESHOLD = 0.8
TAIL_QUESTION_SIMILARITY_THRESHOLD = 0.55


def _tail_question(text: str) -> str:
    """Returns the last sentence containing a '?', or the last sentence if
    none has one. Short repeated answers ("haa", "yes") often leave most of
    a reply different but the trailing QUESTION identical -- comparing just
    that tail catches repeats that whole-text similarity misses."""
    sentences = re.split(r"(?<=[.?!])\s+", text.strip())
    for sentence in reversed(sentences):
        if "?" in sentence:
            return sentence
    return sentences[-1] if sentences else text


def _is_too_similar(a: str, b: str, same_target_as_before: bool = False) -> bool:
    """same_target_as_before=True means this turn is legitimately asking
    about the same still-missing field as last turn -- a similar
    acknowledgment + trailing question is then expected, not a sign of
    being stuck, so a much higher whole-reply threshold applies and the
    tail-question check (which would otherwise fire on the repeated
    question alone) is skipped entirely."""
    a, b = a.strip(), b.strip()
    threshold = SAME_TARGET_REPETITION_SIMILARITY_THRESHOLD if same_target_as_before else REPETITION_SIMILARITY_THRESHOLD
    if difflib.SequenceMatcher(None, a, b).ratio() > threshold:
        return True
    if same_target_as_before:
        return False
    return (
        difflib.SequenceMatcher(None, _tail_question(a), _tail_question(b)).ratio()
        > TAIL_QUESTION_SIMILARITY_THRESHOLD
    )


def _recent_assistant_messages(history: list[dict], n: int = 3) -> list[str]:
    """Last n assistant replies, most recent first. Checking more than just
    the immediately preceding turn catches a repeat that skips one turn
    (e.g. turn 8 and turn 10 are near-identical but turn 9 happened to
    differ, which a single-turn-back check would miss entirely)."""
    found = []
    for turn in reversed(history):
        if turn["role"] == "assistant":
            found.append(turn["content"])
            if len(found) == n:
                break
    return found


def _fallback_reply(nudge_field: str | None, same_target_as_before: bool = False) -> str:
    """Guaranteed non-repeating fallback if the model keeps repeating even
    after a corrective retry. Deliberately plain English, not localized to
    the user's language -- this is a rare last resort, and a clean English
    sentence beats a broken mix of translated wrapper text plus an
    untranslated English field description.

    When same_target_as_before is True, the repeat almost always means the
    nudge field was stale (the user's last message likely already answered
    it, but extraction hadn't caught up yet when this turn's prompt was
    built) -- re-asking the same question yet again would be visibly wrong,
    so this acknowledges instead of repeating it."""
    if same_target_as_before:
        return "Got it, thank you for sharing that. Is there anything else about this you'd like to add?"
    if nudge_field:
        return f"Got it, thank you. Could you tell me {NUDGE_TEMPLATES[nudge_field]}?"
    return "Got it, thank you. What else would you like to know?"


def _build_reply_guarded(
    messages: list[dict], history: list[dict], nudge_field: str | None, same_target_as_before: bool = False
) -> tuple[str, bool]:
    """Sarvam-30B can fall into a repetition loop: once it produces two
    near-identical replies in a row, it tends to keep repeating that exact
    text even when the nudge target has since changed. Detect that against
    the last few assistant turns (not just the immediately preceding one --
    a repeat can skip one turn if that turn happened to differ), retry once
    with extra randomness, and fall back to a guaranteed-fresh templated
    reply if even the retry repeats.

    Returns (reply, nudge_was_shown). _fallback_reply has two variants: the
    same_target_as_before one is a generic "anything else?" with NO real
    question in it, but the other variant DOES pose the actual templated
    question (just in plain English) -- only the former should count as
    "nudge not shown," or a real question that WAS asked (via fallback
    wording) gets wrongly forgotten and re-asked on a later turn."""
    reply = _build_reply(messages)
    recent_replies = _recent_assistant_messages(history[:-1])
    if not any(_is_too_similar(reply, prev, same_target_as_before) for prev in recent_replies):
        return reply, True

    retry_messages = messages + [
        {"role": "assistant", "content": reply},
        {
            "role": "user",
            "content": (
                "[This is an internal correction note, not from the user -- "
                "do not reference, mention, or apologize for it in your "
                "reply.] That draft repeated an earlier response almost "
                "word-for-word. Write a genuinely different reply that "
                "specifically reacts to my last real message above, "
                "following the system instructions. Do NOT mention that a "
                "previous draft was repetitive or apologize for it -- just "
                "answer naturally as if this were your first attempt."
            ),
        },
    ]
    reply = _build_reply(retry_messages, temperature=1.0)
    if any(_is_too_similar(reply, prev, same_target_as_before) for prev in recent_replies):
        fallback = _fallback_reply(nudge_field, same_target_as_before)
        # The "same target" fallback is the only variant with no real
        # question in it; the other variant DOES ask the real thing.
        nudge_was_shown = not same_target_as_before and nudge_field is not None
        return fallback, nudge_was_shown
    return reply, True


def _stream_reply(messages: list[dict]):
    """Yields text deltas as they arrive from Sarvam."""
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort=None,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _extract_incident_fields(history: list[dict]) -> dict:
    transcript = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        reasoning_effort=None,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {}


def _run_extraction_worker(session_id: str) -> None:
    """Runs extraction+save, then loops to catch up if more turns arrived
    while it was working, instead of letting a new thread queue up behind
    this one. At most one of these is ever active per session -- see the
    non-blocking lock.acquire() at the call site in chat_turn/_stream."""
    session = _sessions[session_id]
    try:
        while True:
            version_at_start = session["extraction_version"]
            history = session["history"]
            incident: Incident = session["incident"]
            try:
                updates = _extract_incident_fields(history)
                incident.merge_extracted(updates)
                incident.raw_conversation = "\n".join(f"{t['role']}: {t['content']}" for t in history)
                save_session(incident, history)
            except Exception:
                # Extraction/storage is best-effort background work -- a
                # failure here must never surface to the user, who already
                # has their reply.
                pass
            if session["extraction_version"] == version_at_start:
                return
            # Else: at least one more turn arrived while we were working --
            # loop again on the now-current history before giving up the
            # lock, so a backlog can never build up.
    finally:
        session["lock"].release()


_BARE_NEGATION_TOKENS = {
    "no",
    "nope",
    "nahi",
    "nhi",
    "naa",
    "na",
    "pata nahi",
    "pata nhi",
    "i don't know",
    "i dont know",
    "idk",
}


def _is_bare_negation(text: str) -> bool:
    """True for a short, plain 'no'/'nahi'/'I don't know' type answer with
    nothing else of substance in it. Used as a deterministic backstop: the
    model is told not to invent extra follow-up questions, but it doesn't
    always listen over a long conversation -- this guarantees that when the
    user flatly declines, no nudge is injected that turn at all, so there
    is nothing left for the model to loop on."""
    cleaned = text.strip().lower().strip(".!?")
    return len(cleaned) <= 20 and cleaned in _BARE_NEGATION_TOKENS


def _prepare_turn(session_id: str, user_message: str, k: int) -> tuple[dict, list[dict], str | None, bool, str | None, bool]:
    session = _get_session(session_id)
    history = session["history"]
    incident: Incident = session["incident"]

    previous_nudge_field = session["last_nudge_field"]

    history.append({"role": "user", "content": user_message})
    session["extraction_version"] += 1

    context_chunks = retrieve(user_message, k=k)
    context_block = (
        "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(context_chunks))
        if context_chunks
        else "(no relevant context found)"
    )

    nudge_field = incident.next_missing_field()
    needs_account_followup = nudge_field == "mule_account" and incident.needs_account_number_followup()

    # If the user just gave a bare "no"/"nahi"/"I don't know", don't inject
    # ANY nudge this turn -- a deterministic backstop against the model
    # rephrasing and re-asking the same (or an invented) question despite
    # being told to drop it. nudge_field itself still tracks the real
    # underlying state (for session continuity / same_target_as_before);
    # only what's shown to the model this turn is suppressed.
    prompt_nudge_field = None if _is_bare_negation(user_message) else nudge_field
    messages = _construct_messages(history, context_block, prompt_nudge_field, needs_account_followup)

    # Used only by the repetition guard, to recognize "legitimately asking
    # about the same still-unanswered field two turns in a row" as distinct
    # from "stuck in a loop" -- see _is_too_similar.
    same_target_as_before = nudge_field is not None and nudge_field == previous_nudge_field
    session["last_nudge_field"] = nudge_field

    return session, messages, nudge_field, same_target_as_before, prompt_nudge_field, needs_account_followup


def _mark_nudge_asked(incident: Incident, prompt_nudge_field: str | None, needs_account_followup: bool) -> None:
    """Called only once we know the nudge question was ACTUALLY shown to the
    user (not swallowed by the generic repetition-guard fallback, which
    never poses the intended question) -- marking it asked beforehand would
    permanently skip a field the user was never really asked about."""
    if not prompt_nudge_field:
        return
    if prompt_nudge_field not in incident.fields_asked:
        incident.fields_asked.append(prompt_nudge_field)
    if needs_account_followup:
        incident.mule_account_followup_asked = True


def _kick_off_extraction(session_id: str, session: dict) -> None:
    """Starts the coalescing extraction worker if none is currently active
    for this session; otherwise does nothing -- the already-running worker
    will pick up this turn in its catch-up loop once its current pass
    finishes. This bounds in-flight extraction work to one call at a time
    per session, no matter how fast the user sends messages."""
    if session["lock"].acquire(blocking=False):
        # Not a daemon thread: a daemon gets killed the instant the process
        # exits, which would silently drop the save in a short-lived process
        # (a script, a serverless invocation). A long-running server just
        # keeps running, so this costs nothing there.
        threading.Thread(target=_run_extraction_worker, args=(session_id,)).start()


def chat_turn(session_id: str, user_message: str, k: int = 4) -> str:
    session, messages, nudge_field, same_target_as_before, prompt_nudge_field, needs_account_followup = (
        _prepare_turn(session_id, user_message, k)
    )
    reply, nudge_was_shown = _build_reply_guarded(messages, session["history"], nudge_field, same_target_as_before)
    session["history"].append({"role": "assistant", "content": reply})

    if nudge_was_shown:
        _mark_nudge_asked(session["incident"], prompt_nudge_field, needs_account_followup)

    _kick_off_extraction(session_id, session)

    return reply


def chat_turn_stream(session_id: str, user_message: str, k: int = 4):
    """Same as chat_turn, but yields reply text deltas as they're generated.
    Extraction still runs in the background after the stream finishes.

    NOTE: unlike chat_turn, this has no repetition guard -- by the time a
    repeated reply could be detected, its text has already been streamed to
    the user, so there's nothing to retry. If repetition shows up here too,
    it needs a fix upstream (shorter history window, a different model
    setting), not a post-hoc retry. Since there's no fallback path here, the
    nudge (if any) is always genuinely shown, so it's marked asked
    unconditionally once the stream completes."""
    session, messages, _nudge_field, _same_target_as_before, prompt_nudge_field, needs_account_followup = (
        _prepare_turn(session_id, user_message, k)
    )

    chunks: list[str] = []
    for delta in _stream_reply(messages):
        chunks.append(delta)
        yield delta

    session["history"].append({"role": "assistant", "content": "".join(chunks)})
    _mark_nudge_asked(session["incident"], prompt_nudge_field, needs_account_followup)

    _kick_off_extraction(session_id, session)
