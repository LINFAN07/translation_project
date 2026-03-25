"""
合併分段譯文：若下一段開頭與上一段結尾重複（重疊區），則裁掉重複前綴。
僅在足夠長的完全相符後綴／前綴時才裁切，以降低誤傷。
"""
from __future__ import annotations

# 與切段重疊同數量級太短易誤判；太長則較難對齊
_MIN_SPLICE_LEN = 28
_MAX_SPLICE_LEN = 480


def join_translated_chunks(translations: list[str]) -> str:
    if not translations:
        return ""
    parts: list[str] = []
    first = translations[0].strip()
    if first:
        parts.append(first)
    for nxt_raw in translations[1:]:
        nxt = nxt_raw.strip()
        if not nxt:
            continue
        if not parts:
            parts.append(nxt)
            continue
        prev = parts[-1]
        upper = min(len(prev), len(nxt), _MAX_SPLICE_LEN)
        trimmed = nxt
        for length in range(upper, _MIN_SPLICE_LEN - 1, -1):
            if prev.endswith(nxt[:length]):
                trimmed = nxt[length:].lstrip()
                break
        if trimmed:
            parts.append(trimmed)
        elif not trimmed and upper >= _MIN_SPLICE_LEN:
            # 整段皆與前段結尾重疊，略過
            continue
        else:
            parts.append(nxt)
    return "\n\n".join(parts)
