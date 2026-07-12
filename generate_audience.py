# -*- coding: utf-8 -*-
"""
generate_audience.py — مولّد الجمهور الحي + برهان المطابقة
==========================================================
يولّد N تقييمًا عبر ReviewGenerator المعاير، يحفظها، ويطبع تقرير مطابقة
كامل ضد بيانات المنافسين الحقيقية (competitor_reviews.json):

  • مدرّج الأطوال شريحة-بشريحة (مولَّد مقابل منافس).
  • اختبار χ² لحسن المطابقة (goodness of fit).
  • نسيج بشري: رمزية صرفة، تمطيط، إيموجي، وسيط الحروف.
  • تفرّد + أعلى العبارات تكرارًا (يجب أن يشبه تكرار المنافس لا صفرًا).
  • عيّنة عمياء: هل تميّز المولَّد عن الحقيقي؟

التشغيل:  python generate_audience.py [N]     (الافتراضي 1000)
"""
import sys
import json
import os
import re
import random
import collections

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
# المرجع = الكشط الشامل (452 نصًّا/25 متجرًا)، مع تدرّج للملف القديم
COMP = os.path.join(HERE, 'competitor_reviews_full.json')
if not os.path.exists(COMP):
    COMP = os.path.join(HERE, 'competitor_reviews.json')
OUT = os.path.join(HERE, 'generated_audience_1000.json')

import review_generator as rg
from realism_calibrator import BUCKETS, bucket_histogram, chi_square

_AR = re.compile('[؀-ۿ]')
_EMOJI = re.compile('[\U0001F000-\U0001FAFF\U00002600-\U000027BF❤✅\U0001F1E6-\U0001F1FF]')


def bucket_label(lo, hi):
    if lo == hi:
        return f'{lo}'
    if hi >= 999:
        return f'>{lo-1}'
    return f'{lo}-{hi}'


def texture(texts):
    n = len(texts) or 1
    return {
        'symbolic_pure': sum(1 for t in texts if not _AR.search(t)) / n,
        'elongation': sum(1 for t in texts if re.search(r'(.)\1\1', t)) / n,
        'emoji_any': sum(1 for t in texts if _EMOJI.search(t)) / n,
        'median_chars': sorted(len(t) for t in texts)[n // 2],
        'mean_words': sum(len(t.split()) for t in texts) / n,
    }


def main(n=1000, seed=None):
    if seed is not None:
        random.seed(seed)

    # ── بيانات المنافسين ──
    comp = json.load(open(COMP, encoding='utf-8'))
    comp_texts = [r['text'].strip() for r in comp['reviews'] if r.get('text', '').strip()]
    comp_lens = [len(t.split()) for t in comp_texts]
    comp_probs, comp_counts = bucket_histogram(comp_lens)

    # ── توليد الجمهور ──
    gen = rg.ReviewGenerator()
    products = [
        ('عطر العود الملكي الفاخر', 320, 'oud', 'male'),
        ('مسك الطهارة الأبيض', 89, 'musk', 'unisex'),
        ('عطر الياسمين النادر', 199, 'floral', 'female'),
        ('برفيوم أمواج الليل', 259, 'oriental', 'unisex'),
        ('عطر النخبة الصيفي المنعش', 149, 'fresh', 'male'),
    ]
    per = n // len(products)
    reviews = []
    for name, price, cat, gender in products:
        batch = gen.generate_reviews(name, price, category=cat, gender=gender,
                                     count=per, add_typos=True)
        for r in batch:
            r['product'] = name
            reviews.append(r)
    # إكمال أي نقص
    while len(reviews) < n:
        extra = gen.generate_reviews(products[0][0], products[0][1], count=n - len(reviews),
                                     add_typos=True)
        for r in extra:
            r['product'] = products[0][0]
            reviews.append(r)
    reviews = reviews[:n]

    gen_texts = [r['text'] for r in reviews]
    gen_lens = [len(t.split()) for t in gen_texts]
    gen_probs, gen_counts = bucket_histogram(gen_lens)

    # ── حفظ ──
    json.dump({'count': len(reviews), 'source': 'ReviewGenerator v3.1 (معاير)',
               'reviews': reviews}, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ── التقرير ──
    print('=' * 68)
    print(f'  برهان المطابقة — {len(gen_texts)} مولَّد مقابل {len(comp_texts)} منافس')
    print('=' * 68)
    print(f'\n{"الشريحة":>8} | {"منافس":>8} | {"مولَّد":>8} | فرق')
    print('-' * 44)
    for (lo, hi) in BUCKETS:
        c = comp_probs[(lo, hi)] * 100
        g = gen_probs[(lo, hi)] * 100
        print(f'{bucket_label(lo,hi):>8} | {c:7.1f}% | {g:7.1f}% | {g-c:+5.1f}')

    # χ² — درجات حرية = عدد الشرائح - 1 = 6 ؛ الحرج (p=0.05) = 12.59
    chi = chi_square(gen_counts, comp_probs, len(gen_texts))
    crit = 12.59
    verdict = 'مطابق ✅ (لا فرق دال)' if chi < crit else 'انحراف ⚠️'
    print(f'\nχ² = {chi:.2f}  (الحرج عند p=0.05 = {crit}) → {verdict}')

    # النسيج
    ct, gt = texture(comp_texts), texture(gen_texts)
    print(f'\n{"النسيج":>16} | {"منافس":>8} | {"مولَّد":>8}')
    print('-' * 40)
    for k, label in [('symbolic_pure', 'رمزية صرفة'), ('elongation', 'تمطيط'),
                     ('emoji_any', 'إيموجي'), ('mean_words', 'متوسط كلمات'),
                     ('median_chars', 'وسيط حروف')]:
        cv, gv = ct[k], gt[k]
        if k in ('mean_words',):
            print(f'{label:>16} | {cv:8.2f} | {gv:8.2f}')
        elif k in ('median_chars',):
            print(f'{label:>16} | {cv:8.0f} | {gv:8.0f}')
        else:
            print(f'{label:>16} | {cv*100:7.1f}% | {gv*100:7.1f}%')

    # التفرّد + أعلى تكرار (الواقع يكرّر القصير)
    uniq = len(set(gen_texts))
    print(f'\nتفرّد: {uniq}/{len(gen_texts)} ({uniq/len(gen_texts)*100:.1f}%)')
    print('أعلى العبارات تكرارًا (طبيعي في القصير):')
    for t, c in collections.Counter(gen_texts).most_common(6):
        print(f'   {c:>3}× {t!r}')

    # عيّنة عمياء
    print('\n— عيّنة عمياء (خُلطت حقيقي/مولَّد): —')
    mix = [('C', t) for t in random.sample(comp_texts, 6)] + \
          [('G', t) for t in random.sample(gen_texts, 6)]
    random.shuffle(mix)
    for i, (src, t) in enumerate(mix, 1):
        print(f'  {i:>2}. [{src}] {t}')

    print(f'\n💾 حُفظت في: {os.path.basename(OUT)}')
    return chi < crit


if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    ok = main(N)
    sys.exit(0 if ok else 1)
