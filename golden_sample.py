# -*- coding: utf-8 -*-
"""
golden_sample.py — العينة الذهبية (Golden Sample)
==================================================
يولّد 30 تقييمًا هي الشفرة الوراثية التي يُقاس عليها كل توليد لاحق، عبر ثلاثة مرشّحات:

1. إحصائي : 22×5★ + 7×4★ + 1×3★  (≈ 74/22/4 — خط الأساس)
2. دلالي  : semantic_guard — صفر نزيف، صفر بتر، صفر تكرار (حرفي أو دلالي ≥0.80)
3. عاطفي  : 20% إيموجي طبيعي، 30% سياق استخدام، 10% تحفّظ إيجابي (3-4★ بنّاء)

temperature = 0.3 مثبّتة على كل استدعاء AI — لا تساوم.

الاستخدام:  python -X utf8 golden_sample.py
المخرج:    golden_sample.json (المواصفة + البصمة المقاسة + الثلاثون)
"""
import sys
import json
import random
import difflib
import collections
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from semantic_guard import guard_violations, has_context, has_reservation

GOLDEN_TEMPERATURE = 0.3
SPEC = {
    'ratings': {5: 22, 4: 7, 3: 1},          # المرشّح الإحصائي (74/22/4 على 30)
    'emoji_rate': 0.20,                        # المرشّح العاطفي — بأمر العقل المدبّر
    'context_rate': 0.30,
    'reservation_rate': 0.10,
    'max_words': 4,
    'similarity_ceiling': 0.80,                # فوقها = استنساخ جيني مرفوض
    'first_word_cap': 3,                       # تنويع الافتتاحيات
}
# لوحة الإيموجي الطبيعية — مستخرجة من كوربوس المنافسين الحقيقي (752 نصًّا)
EMOJI_PALETTE = [('😍', 19), ('👍🏻', 11), ('❤️', 4), ('💎', 4),
                 ('👌', 3), ('🤩', 3), ('🤍', 3), ('🔥', 2)]

MAX_POOL_ROUNDS = 30       # سقف جولات _gen (كل جولة شخصية كاملة = 2-5 تقييمات)
MAX_TARGETED = 20          # سقف التوليدات الموجَّهة لسدّ النواقص

CONTEXT_DIRECTIVE = ('## توجيه إجباري:\n- اذكر مناسبة استخدام واقعية واحدة '
                     '(مسجد/دوام/سهرة/مشوار/عيد/طلعة) داخل التقييم — ٤ كلمات كحد أقصى.')
RESERVATION_DIRECTIVE = ('## توجيه إجباري:\n- تحفّظ إيجابي بنّاء: مدح صادق مع ملاحظة لطيفة '
                         'بصيغة «بس» أو «ودي» — ٤ كلمات كحد أقصى.')


def _norm(t):
    return ' '.join((t or '').split())


class GoldenCurator:
    def __init__(self):
        self.pool = []          # مرشّحون ناجون من المرشّح الدلالي
        self.seen = []          # نصوص مقبولة (لفحص التشابه)

    def offer(self, rv, source):
        """يعرض تقييمًا على المرشّح الدلالي + مرشّح الاستنساخ. يرجع True إن قُبل."""
        text = _norm(rv.get('text', ''))
        rating = int(rv.get('rating', 5))
        if rating not in SPEC['ratings']:
            return False
        if guard_violations(text, max_words=SPEC['max_words']):
            return False
        for s in self.seen:
            if difflib.SequenceMatcher(None, text, s).ratio() >= SPEC['similarity_ceiling']:
                return False
        self.seen.append(text)
        self.pool.append({
            'text': text, 'rating': rating,
            'context': has_context(text), 'reservation': has_reservation(text),
            'product': rv.get('product', ''), 'source': source,
        })
        return True

    def shortfalls(self):
        """ماذا ينقص المحصول لسدّ الحصص؟"""
        by_rating = collections.Counter(x['rating'] for x in self.pool)
        need_res = max(0, 3 - sum(1 for x in self.pool if x['reservation'] and x['rating'] in (3, 4)))
        need_ctx = max(0, 9 - sum(1 for x in self.pool if x['context']))
        need_rating = {r: max(0, q + 2 - by_rating[r]) for r, q in SPEC['ratings'].items()}
        return need_rating, need_ctx, need_res

    def select_30(self):
        """الانتقاء النهائي: حصص النجوم + سياق ≥9 + تحفّظ ≥3 + تنويع الافتتاحيات."""
        need = dict(SPEC['ratings'])
        first_words = collections.Counter()
        chosen, remaining = [], list(self.pool)

        def take(item):
            chosen.append(item)
            need[item['rating']] -= 1
            first_words[item['text'].split()[0]] += 1
            remaining.remove(item)

        def pickable(item, relax=False):
            if need.get(item['rating'], 0) <= 0:
                return False
            if not relax and first_words[item['text'].split()[0]] >= SPEC['first_word_cap']:
                return False
            return True

        # 1) التحفّظ الإيجابي: 1×3★ ثم 2×4★
        for want_rating, count in ((3, 1), (4, 2)):
            got = 0
            for item in list(remaining):
                if got >= count:
                    break
                if item['rating'] == want_rating and item['reservation'] and pickable(item):
                    take(item); got += 1

        # 2) السياق حتى 9
        for item in sorted(remaining, key=lambda x: -x['rating']):
            if sum(1 for c in chosen if c['context']) >= 9:
                break
            if item['context'] and pickable(item):
                take(item)

        # 3) إكمال الحصص مع تنويع الافتتاحيات (ثم تخفيف القيد إن لزم)
        for relax in (False, True):
            for item in list(remaining):
                if len(chosen) >= 30:
                    break
                if pickable(item, relax=relax):
                    take(item)

        return chosen if len(chosen) == 30 else None


def main():
    import app  # يطبع حالة المحركات

    # ══ تثبيت الحرارة الذهبية على كل استدعاء — لا تساوم ══
    _orig_call = app._ai_call

    def _pinned_call(prompt, max_tokens=1200, temperature=None):
        return _orig_call(prompt, max_tokens=max_tokens, temperature=GOLDEN_TEMPERATURE)
    app._ai_call = _pinned_call
    print(f'🌡️ temperature مثبّتة = {GOLDEN_TEMPERATURE}')

    curator = GoldenCurator()

    def gen_persona_batch():
        """شخصية كاملة → تقييمات عطور فقط (بلا تقييم متجر — توفير استدعاءات)."""
        arch = random.choice(app.ARCHETYPES)
        persona = app._make_persona_for_arch(arch)
        perfumes = app._pick_products(arch)
        return app._ai_reviews(persona, perfumes)

    def gen_targeted(rating_set, directive, label):
        """توليد موجَّه: يعيد سحب params محليًا حتى يطابق النجوم، ثم يكتب بالـ AI."""
        arch = random.choice(app.ARCHETYPES)
        persona = app._make_persona_for_arch(arch)
        perfumes = app._pick_products(arch)
        pf = random.choice(perfumes)
        used = app._used_texts_block(limit=15, persona_name=persona.get('name'))
        prompt, params = app._make_master_prompt(persona, pf['name'], used, extra_block=directive)
        for _ in range(60):
            if params.get('rating') in rating_set:
                break
            prompt, params = app._make_master_prompt(persona, pf['name'], used, extra_block=directive)
        rv = app._write_review(persona, pf, prompt, params)
        rv['rating'] = params.get('rating', rv.get('rating', 5))
        return curator.offer(rv, label)

    # ── المرحلة 1: المحصول الحر ──
    for round_no in range(1, MAX_POOL_ROUNDS + 1):
        try:
            for rv in gen_persona_batch():
                curator.offer(rv, 'pool')
        except app.AIUnavailable as e:
            print(f'⛔ AI متوقف: {e}')
            sys.exit(1)
        except Exception as e:
            print(f'⚠️ جولة {round_no} فشلت: {e}')
            continue
        need_rating, need_ctx, need_res = curator.shortfalls()
        print(f'جولة {round_no}: محصول={len(curator.pool)} '
              f'نقص_نجوم={need_rating} نقص_سياق={need_ctx} نقص_تحفّظ={need_res}', flush=True)
        # السياق مسؤولية التوليد الموجَّه (لا يأتي عضويًا بحرارة 0.3) — لا ننتظره هنا
        if not any(need_rating.values()) and not need_res:
            break

    # ── المرحلة 2: سدّ النواقص بتوليد موجَّه ──
    budget = MAX_TARGETED
    while budget > 0:
        need_rating, need_ctx, need_res = curator.shortfalls()
        if not any(need_rating.values()) and not need_ctx and not need_res:
            break
        try:
            if need_res:
                gen_targeted({3, 4} if need_rating.get(3) else {4}, RESERVATION_DIRECTIVE, 'targeted:reservation')
            elif need_ctx:
                gen_targeted({5, 4}, CONTEXT_DIRECTIVE, 'targeted:context')
            else:
                want = next(r for r, n in need_rating.items() if n)
                gen_targeted({want}, '', f'targeted:rating{want}')
        except app.AIUnavailable as e:
            print(f'⛔ AI متوقف: {e}')
            sys.exit(1)
        except Exception as e:
            print(f'⚠️ توليد موجَّه فشل: {e}')
        budget -= 1
        print(f'موجَّه (متبقٍّ {budget}): محصول={len(curator.pool)}', flush=True)

    # ── المرحلة 3: الانتقاء الذهبي ──
    chosen = curator.select_30()
    if not chosen:
        print(f'❌ المحصول لا يكفي حصص الذهب — {len(curator.pool)} مرشّحًا فقط.')
        sys.exit(1)

    # ── المرحلة 4: المرشّح العاطفي — 20% إيموجي طبيعي (6 من 30) ──
    emojis, weights = zip(*EMOJI_PALETTE)
    candidates = [c for c in chosen if c['rating'] == 5]
    for item in random.sample(candidates, 6):
        item['emoji'] = random.choices(emojis, weights=weights, k=1)[0]
        item['text'] = f"{item['text']} {item['emoji']}"
    for item in chosen:
        item.setdefault('emoji', '')

    random.shuffle(chosen)

    # ── البصمة المقاسة ──
    ratings = collections.Counter(c['rating'] for c in chosen)
    fingerprint = {
        'count': len(chosen),
        'ratings': {str(k): v for k, v in sorted(ratings.items(), reverse=True)},
        'emoji_texts': sum(1 for c in chosen if c['emoji']),
        'context_texts': sum(1 for c in chosen if c['context']),
        'reservation_texts': sum(1 for c in chosen if c['reservation']),
        'avg_words': round(sum(len(c['text'].split()) - (1 if c['emoji'] else 0)
                               for c in chosen) / len(chosen), 2),
        'unique_first_words': len({c['text'].split()[0] for c in chosen}),
        'guard_violations': 0,
        'duplicates': 0,
    }

    out = {
        'version': 'golden-1.0',
        'created': date.today().isoformat(),
        'temperature': GOLDEN_TEMPERATURE,
        'spec': {
            'ratings': {str(k): v for k, v in SPEC['ratings'].items()},
            'emoji_rate': SPEC['emoji_rate'],
            'context_rate': SPEC['context_rate'],
            'reservation_rate': SPEC['reservation_rate'],
            'max_words': SPEC['max_words'],
            'similarity_ceiling': SPEC['similarity_ceiling'],
            'negative_backdoor_live': 0.01,
        },
        'market_reference': {
            'corpus_file': 'competitor_reviews.json', 'corpus_texts': 752,
            'measured_emoji_rate': 0.04, 'measured_digit_rate': 0.02,
            'top_emoji': [e for e, _ in EMOJI_PALETTE],
        },
        'fingerprint': fingerprint,
        'reviews': [{'text': c['text'], 'rating': c['rating'], 'emoji': c['emoji'],
                     'context': c['context'], 'reservation': c['reservation'],
                     'product': c['product'], 'source': c['source']} for c in chosen],
    }
    with open('golden_sample.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print('\n🏆 golden_sample.json مكتوب')
    print('البصمة:', json.dumps(fingerprint, ensure_ascii=False))


if __name__ == '__main__':
    main()
