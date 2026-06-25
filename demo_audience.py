# -*- coding: utf-8 -*-
"""عرض توضيحي لمنظومة جمهور حي — توليد 50 تقييم ومقارنة"""
import sys
import random
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from audience_engine import AudienceEngine, NATURAL_FLAWS
from audience_db import AudienceDB
from review_patterns import (
    pick_pattern, pick_rating, pick_store_pattern, pick_honest_pattern,
    get_ai_directive, get_pattern_description, REVIEW_PATTERNS,
    LOW_RATING_REASONS, is_store_pattern, RATING_DISTRIBUTION
)
from real_reviews_bank import (
    MALE_NEGATIVE, FEMALE_NEGATIVE, BALANCED_4STAR,
    STORE_REVIEWS_BANK, SCENT_FAMILY_REVIEWS
)
from short_texts_bank import NEGATIVE_SHORTS, NEUTRAL_SHORTS, OUD_OCCASIONS, FRESH_DAILY, FEMININE_SWEET, GENERAL_ADMIRATION
from anti_repeat import (
    TRACKED_WORDS, TRACKED_PATTERNS, TRACKED_CONTEXTS,
    register_review_full, get_burned_words, reset_session_texts,
    is_context_burned, get_available_contexts
)
from personas_engine import (
    ARCHETYPES, cross_product_variation, generate_writing_fingerprint,
    generate_persona
)
from dialects import NEGATIVE_DIALECT_EXPRESSIONS, COMPLAINT_PATTERNS, get_negative_expression

# ═══════════════════════════════════════════════════════════
#  توليد 50 تقييم متنوع
# ═══════════════════════════════════════════════════════════

def generate_demo_batch(count=50):
    """توليد دفعة تقييمات متنوعة من البنوك المختلفة"""
    engine = AudienceEngine(':memory:')
    reset_session_texts()
    
    # توزيع النجوم
    ratings = engine._assign_ratings(count)
    
    reviews = []
    used_texts = set()
    
    # مصادر التقييمات حسب النجوم
    all_positive_shorts = OUD_OCCASIONS + FRESH_DAILY + FEMININE_SWEET + GENERAL_ADMIRATION
    
    for i, rating in enumerate(ratings):
        review = None
        review_type = 'product'
        
        # 15% تقييمات متجر
        if random.random() < 0.15:
            review_type = 'store'
            review = random.choice(STORE_REVIEWS_BANK)
        elif rating == 5:
            # تنويع مصادر تقييمات 5 نجوم
            source = random.choices(
                ['short_positive', 'scent_family', 'positive_bank'],
                weights=[50, 25, 25], k=1
            )[0]
            if source == 'short_positive':
                review = random.choice(all_positive_shorts)
            elif source == 'scent_family':
                family = random.choice(list(SCENT_FAMILY_REVIEWS.keys()))
                review = random.choice(SCENT_FAMILY_REVIEWS[family])
            else:
                review = random.choice(BALANCED_4STAR)  # some 4-star texts work as 5
        elif rating == 4:
            source = random.choices(
                ['balanced_4star', 'scent_family'], weights=[70, 30], k=1
            )[0]
            if source == 'balanced_4star':
                review = random.choice(BALANCED_4STAR)
            else:
                family = random.choice(list(SCENT_FAMILY_REVIEWS.keys()))
                review = random.choice(SCENT_FAMILY_REVIEWS[family])
        elif rating == 3:
            source = random.choices(
                ['male_neg', 'female_neg', 'neutral_short'], weights=[40, 40, 20], k=1
            )[0]
            if source == 'male_neg':
                # Pick 3-star reviews from MALE_NEGATIVE (second half)
                review = random.choice(MALE_NEGATIVE[10:])
            elif source == 'female_neg':
                review = random.choice(FEMALE_NEGATIVE[10:])
            else:
                review = random.choice(NEUTRAL_SHORTS)
        elif rating == 2:
            source = random.choices(
                ['male_neg', 'female_neg', 'neg_short'], weights=[40, 40, 20], k=1
            )[0]
            if source == 'male_neg':
                review = random.choice(MALE_NEGATIVE[:10])
            elif source == 'female_neg':
                review = random.choice(FEMALE_NEGATIVE[:10])
            else:
                review = random.choice(NEGATIVE_SHORTS)
        elif rating == 1:
            source = random.choices(
                ['neg_short', 'complaint'], weights=[60, 40], k=1
            )[0]
            if source == 'neg_short':
                review = random.choice(NEGATIVE_SHORTS)
            else:
                dialect = random.choice(list(COMPLAINT_PATTERNS.keys()))
                review = random.choice(COMPLAINT_PATTERNS[dialect])
        
        # حقن عيب طبيعي (30% للتقييمات 4-5 نجوم)
        if rating >= 4 and engine.should_inject_flaw():
            flaw = engine._get_random_flaw()
            review = f"{review} {flaw}" if review else flaw
        
        # تجنب التكرار
        attempts = 0
        while review in used_texts and attempts < 5:
            # إعادة اختيار
            if rating >= 4:
                family = random.choice(list(SCENT_FAMILY_REVIEWS.keys()))
                review = random.choice(SCENT_FAMILY_REVIEWS[family])
            elif rating == 3:
                review = random.choice(MALE_NEGATIVE[10:] + FEMALE_NEGATIVE[10:])
            else:
                review = random.choice(NEGATIVE_SHORTS)
            attempts += 1
        
        used_texts.add(review)
        
        # تسجيل في نظام مكافحة التكرار
        register_review_full(review, f'persona_{i}')
        
        stars = '⭐' * rating
        reviews.append({
            'index': i + 1,
            'text': review,
            'rating': rating,
            'stars': stars,
            'type': review_type,
            'word_count': len(review.split()),
        })
    
    return reviews

# ═══════════════════════════════════════════════════════════
#  التشغيل
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 70)
    print('🎯 عرض توضيحي — منظومة جمهور حي')
    print('=' * 70)
    
    reviews = generate_demo_batch(50)
    
    # عرض التقييمات
    print(f'\n📝 50 تقييم متنوع:\n')
    for r in reviews:
        type_tag = ' [متجر]' if r['type'] == 'store' else ''
        print(f"  {r['index']:2d}. {r['stars']} ({r['word_count']} كلمة){type_tag}")
        print(f"      \"{r['text']}\"")
        print()
    
    # إحصائيات
    print('=' * 70)
    print('📊 إحصائيات الدفعة:')
    print('=' * 70)
    
    # توزيع النجوم
    from collections import Counter
    rating_dist = Counter(r['rating'] for r in reviews)
    print(f'\n⭐ توزيع النجوم:')
    for stars in sorted(rating_dist.keys(), reverse=True):
        count = rating_dist[stars]
        pct = count / len(reviews) * 100
        bar = '█' * int(pct / 2)
        target = RATING_DISTRIBUTION.get(stars, 0)
        print(f"   {stars}⭐: {count:2d} ({pct:4.1f}%) {bar}  [مستهدف: {target}%]")
    
    # توزيع الأطوال
    lengths = [r['word_count'] for r in reviews]
    short = sum(1 for l in lengths if l <= 3)
    medium = sum(1 for l in lengths if 4 <= l <= 8)
    long_ = sum(1 for l in lengths if 9 <= l <= 15)
    very_long = sum(1 for l in lengths if l > 15)
    
    print(f'\n📏 توزيع الأطوال:')
    print(f'   1-3 كلمات:  {short:2d} ({short/len(reviews)*100:.0f}%)')
    print(f'   4-8 كلمات:  {medium:2d} ({medium/len(reviews)*100:.0f}%)')
    print(f'   9-15 كلمة:  {long_:2d} ({long_/len(reviews)*100:.0f}%)')
    print(f'   15+ كلمة:   {very_long:2d} ({very_long/len(reviews)*100:.0f}%)')
    
    # نوع التقييم
    store_reviews = sum(1 for r in reviews if r['type'] == 'store')
    product_reviews = len(reviews) - store_reviews
    print(f'\n🏪 نوع التقييم:')
    print(f'   منتج: {product_reviews} ({product_reviews/len(reviews)*100:.0f}%)')
    print(f'   متجر: {store_reviews} ({store_reviews/len(reviews)*100:.0f}%)')
    
    # فحص تكرار الكلمات
    all_texts = ' '.join(r['text'] for r in reviews)
    burned_words_check = ['فخم', 'يجنن', 'خرافي', 'والله', 'دمار', 'بطل']
    print(f'\n🔥 فحص الكلمات المحترقة:')
    for word in burned_words_check:
        count = sum(1 for r in reviews if word in r['text'])
        pct = count / len(reviews) * 100
        status = '✅' if pct <= 15 else '❌'
        print(f'   {status} "{word}": {count} مرات ({pct:.1f}%)')
    
    # فحص التنوع
    unique = len(set(r['text'] for r in reviews))
    print(f'\n🎯 التنوع:')
    print(f'   تقييمات فريدة: {unique}/{len(reviews)} ({unique/len(reviews)*100:.0f}%)')
    
    # فحص تقييمات المتجر
    store_texts = [r['text'] for r in reviews if r['type'] == 'store']
    scent_words = ['ريحة', 'ريحته', 'ثبات', 'ثباته', 'فوحان']
    violations = sum(1 for t in store_texts if any(w in t for w in scent_words))
    print(f'   تقييمات متجر تذكر الريحة: {violations} ✅' if violations == 0 else f'   تقييمات متجر تذكر الريحة: {violations} ❌')
    
    # Bell Curve
    engine = AudienceEngine(':memory:')
    schedule = engine.schedule_bell_curve(reviews, days=7)
    print(f'\n📅 جدولة Bell Curve (7 أيام):')
    day_dist = Counter(s.strftime('%A') for s in schedule)
    for day, count in sorted(day_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f'   {day}: {count} تقييمات')
    
    print(f'\n   ⏰ نطاق الساعات: {min(s.hour for s in schedule)}:00 — {max(s.hour for s in schedule)}:00')
    print(f'   📆 أول موعد: {schedule[0].strftime("%Y-%m-%d %H:%M")}')
    print(f'   📆 آخر موعد: {schedule[-1].strftime("%Y-%m-%d %H:%M")}')
    
    print('\n' + '=' * 70)
    print('✅ عرض توضيحي مكتمل!')
    print('=' * 70)
