"""Pure Bot API 10.3 payload builders; no network or SDK dependency."""

def rich_message(*, html=None, markdown=None, blocks=None):
    values = {key: value for key, value in {"html": html, "markdown": markdown, "blocks": blocks}.items() if value is not None}
    if len(values) != 1:
        raise ValueError("Choose exactly one rich representation")
    key, value = next(iter(values.items()))
    if key == "blocks":
        if not isinstance(value, list) or not value or not all(isinstance(x, dict) for x in value):
            raise ValueError("blocks must be a nonempty list of block objects")
    elif not isinstance(value, str) or not value:
        raise ValueError("Rich text must be nonempty")
    return values

def final_rich_payload(chat_id, **representation):
    return {"chat_id": chat_id, "rich_message": rich_message(**representation)}

def draft_payload(chat_id, draft_id, content, *, rich=False, thread_id=None, can_stop=False, keep_on_stop=False):
    if not isinstance(chat_id, int) or isinstance(chat_id, bool) or chat_id <= 0:
        raise ValueError("Drafts require a private chat ID")
    if not isinstance(draft_id, int) or isinstance(draft_id, bool) or draft_id == 0:
        raise ValueError("draft_id must be a nonzero integer")
    if rich:
        if not isinstance(content, dict):
            raise ValueError("Rich draft content must be an input representation")
        content = rich_message(**content)
    elif not isinstance(content, str):
        raise ValueError("Plain draft content must be text")
    result = {"chat_id": chat_id, "draft_id": draft_id, "rich_message" if rich else "text": content,
              "can_stop": bool(can_stop), "keep_on_stop": bool(keep_on_stop)}
    if thread_id is not None:
        if not isinstance(thread_id, int) or isinstance(thread_id, bool) or thread_id <= 0:
            raise ValueError("thread_id must be positive")
        result["message_thread_id"] = thread_id
    return result
