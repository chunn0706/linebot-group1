# utils/sm2.py
def update_sm2(ease_factor, interval, repetition, quality):
    # SM2 演算法邏輯
    if quality >= 3:
        if repetition == 0:
            interval = 1
        elif repetition == 1:
            interval = 6
        else:
            interval = int(interval * ease_factor)
        repetition += 1
    else:
        repetition = 0
        interval = 1

    ease_factor += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    if ease_factor < 1.3:
        ease_factor = 1.3

    return ease_factor, interval, repetition