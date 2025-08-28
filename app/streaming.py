import time

def speak_while_generating(llm_iter, tts_start_after_tokens=20, tts_start_after_ms=400, token=None):
    buf = []
    t0 = time.time()
    started = False
    for tok in llm_iter:
        if token and token.is_cancelled():
            break
        buf.append(tok)
        if (not started) and (len(buf) >= tts_start_after_tokens or (time.time() - t0) * 1000 >= tts_start_after_ms):
            tts_start("".join(buf), token)
            started = True
        elif started:
            tts_append(tok, token)
    if not started and buf:
        tts_start("".join(buf), token)
    tts_finish(token)
