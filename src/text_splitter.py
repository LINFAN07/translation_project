# 由右而左尋找較自然的斷點（換行、中英句讀）
_BREAK_DELIMS: tuple[str, ...] = (
    "\n",
    "。",
    "！",
    "？",
    "．",
    ".",
    "!",
    "?",
)


def _rfind_any_break(s: str) -> int:
    best = -1
    for d in _BREAK_DELIMS:
        j = s.rfind(d)
        if j > best:
            best = j
    return best


def split_text_with_overlap(text, chunk_size=2000, overlap_size=500):
    """
    將文本切分為帶有重疊區間的段落。
    確保每次切割後，下一個起點 (start) 都比上一個起點大，避免死循環。
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # 計算預期結束位置
        end = start + chunk_size
        
        # 如果不是最後一段，嘗試尋找合適的切分點
        if end < text_length:
            # 在預期結束點附近尋找換行符或句號
            search_start = max(start, end - 100)
            search_end = min(text_length, end + 100)
            search_range = text[search_start:search_end]
            
            break_point = _rfind_any_break(search_range)

            if break_point != -1:
                end = search_start + break_point + 1
        else:
            end = text_length
            
        # 加入切分後的文本
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        
        # 如果已經到達結尾，則跳出
        if end >= text_length:
            break
            
        # 計算下一個起點
        next_start = end - overlap_size
        
        # 關鍵安全性檢查：確保 next_start 至少比當前 start 大
        # 避免因為 overlap_size 大於 chunk_size 導致死循環
        if next_start <= start:
            next_start = start + (chunk_size // 2)
            
        start = next_start
        
    return chunks
