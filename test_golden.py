# -*- coding: utf-8 -*-
"""اختبار شامل لمنظومة جمهور حي V2 — القصص الإنسانية"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

print('=' * 70)
print('🧪 اختبار منظومة القصص الإنسانية — V2')
print('=' * 70)

errors = []

# ═══════════════════════════════════════════════════════════
#  فحص 1: استيراد golden_reviews
# ═══════════════════════════════════════════════════════════
print('\n📦 فحص الاستيرادات...')
try:
    from golden_reviews import (
        GOLDEN_REVIEWS, pick_golden_review, pick_golden_exemplars,
        get_story_types, get_stats
    )
    print(f'   ✅ golden_reviews: {len(GOLDEN_REVIEWS)} تقييم')
except ImportError as e:
    errors.append(f'golden_reviews: {e}')
    print(f'   ❌ golden_reviews: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 2: تنوع القصص
# ═══════════════════════════════════════════════════════════
print('\n📖 فحص تنوع القصص...')
try:
    stats = get_stats()
    story_types = stats['story_types']
    print(f'   📊 أنواع القصص: {len(story_types)}')
    for st, count in sorted(story_types.items(), key=lambda x: -x[1]):
        print(f'      {st}: {count} تقييم')
    
    # يجب أن يكون هناك 7+ أنواع قصص
    if len(story_types) >= 7:
        print(f'   ✅ تنوع القصص: {len(story_types)} نوع')
    else:
        errors.append(f'أنواع القصص فقط {len(story_types)} (المطلوب 7+)')
        print(f'   ❌ أنواع القصص: {len(story_types)} (المطلوب 7+)')
except Exception as e:
    errors.append(f'story_types: {e}')
    print(f'   ❌ {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 3: توزيع النجوم
# ═══════════════════════════════════════════════════════════
print('\n⭐ فحص توزيع النجوم...')
try:
    rating_dist = stats['ratings']
    total = sum(rating_dist.values())
    for rating in sorted(rating_dist.keys()):
        count = rating_dist[rating]
        pct = count / total * 100
        print(f'   {rating}⭐: {count} ({pct:.1f}%)')
    
    # يجب أن يكون هناك تقييمات 3 و 4 نجوم
    has_3_4 = (rating_dist.get(3, 0) + rating_dist.get(4, 0)) > 0
    if has_3_4:
        print(f'   ✅ تقييمات متوازنة موجودة')
    else:
        errors.append('لا توجد تقييمات 3-4 نجوم')
except Exception as e:
    errors.append(f'ratings: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 4: جودة القصص (أهم اختبار)
# ═══════════════════════════════════════════════════════════
print('\n🎯 فحص جودة القصص (الأهم)...')

# كلمات تدل على قصة حقيقية
STORY_MARKERS = [
    'لما', 'وقت', 'يوم', 'مرة', 'قبل', 'بعد',  # زمن
    'أبوي', 'أمي', 'زوجتي', 'زوجي', 'خويي', 'صاحبتي', 'أختي', 'أخوي', 'بنتي', 'ولدي', 'زميلتي', 'زميلي',  # أشخاص
    'قال', 'قالت', 'سأل', 'سألني', 'سألتني',  # حوار
    'فرح', 'فرحت', 'ابتسم', 'ابتسمت', 'حسيت', 'حسست',  # مشاعر
    'الدوام', 'المسجد', 'العزيمة', 'الاجتماع', 'السيارة', 'المقهى',  # أماكن
    'هدية', 'هديت', 'جبته', 'جبتها',  # هدايا
    'أول', 'ثاني', 'ثالث', 'خامس', 'سادس',  # مراحل رحلة العميل
]

DETAIL_MARKERS = [
    'ساعات', 'أيام', 'شهور', 'أسبوع',  # زمن محدد
    'ريال', 'السعر', 'أرخص',  # سعر
    'تابي', 'تمارا', 'واتساب', 'سناب', 'انستقرام', 'تيك توك',  # تقنية
    'الرياض', 'جدة', 'الدمام',  # مدن
    'رابط', 'كرت', 'عينة', 'عينات',  # تفاصيل متجر
]

try:
    story_count = 0
    detail_count = 0
    for r in GOLDEN_REVIEWS:
        text = r['text']
        has_story = any(marker in text for marker in STORY_MARKERS)
        has_detail = any(marker in text for marker in DETAIL_MARKERS)
        if has_story:
            story_count += 1
        if has_detail:
            detail_count += 1
    
    story_pct = story_count / len(GOLDEN_REVIEWS) * 100
    detail_pct = detail_count / len(GOLDEN_REVIEWS) * 100
    
    print(f'   📊 تقييمات تحتوي قصة: {story_count}/{len(GOLDEN_REVIEWS)} ({story_pct:.0f}%)')
    print(f'   📊 تقييمات تحتوي تفاصيل: {detail_count}/{len(GOLDEN_REVIEWS)} ({detail_pct:.0f}%)')
    
    if story_pct >= 50:
        print(f'   ✅ نسبة القصص: {story_pct:.0f}% (المستهدف 50%+)')
    else:
        errors.append(f'نسبة القصص فقط {story_pct:.0f}%')
except Exception as e:
    errors.append(f'story_quality: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 5: الكلمات المحترقة
# ═══════════════════════════════════════════════════════════
print('\n🔥 فحص الكلمات المحترقة...')
try:
    burned_words = ['فخم', 'يجنن', 'خرافي', 'دمار', 'ممتاز']
    for word in burned_words:
        count = sum(1 for r in GOLDEN_REVIEWS if word in r['text'])
        pct = count / len(GOLDEN_REVIEWS) * 100
        status = '✅' if pct <= 10 else '❌'
        print(f'   {status} "{word}": {count} ({pct:.1f}%)')
except Exception as e:
    errors.append(f'burned_words: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 6: التنوع (لا تقييمات متكررة)
# ═══════════════════════════════════════════════════════════
print('\n🎲 فحص التنوع...')
try:
    texts = [r['text'] for r in GOLDEN_REVIEWS]
    unique = len(set(texts))
    print(f'   📊 تقييمات فريدة: {unique}/{len(texts)}')
    if unique == len(texts):
        print(f'   ✅ لا تقييمات مكررة')
    else:
        dup_count = len(texts) - unique
        errors.append(f'{dup_count} تقييمات مكررة')
        print(f'   ❌ {dup_count} تقييمات مكررة')
    
    # تنوع البدايات
    starts = [t.split()[0] if t.split() else '' for t in texts]
    unique_starts = len(set(starts))
    print(f'   📊 بدايات فريدة: {unique_starts}')
except Exception as e:
    errors.append(f'uniqueness: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 7: أطوال متنوعة
# ═══════════════════════════════════════════════════════════
print('\n📏 فحص توزيع الأطوال...')
try:
    lengths = [len(r['text'].split()) for r in GOLDEN_REVIEWS]
    short = sum(1 for l in lengths if l <= 4)
    medium = sum(1 for l in lengths if 5 <= l <= 12)
    long_ = sum(1 for l in lengths if l > 12)
    
    short_pct = short / len(lengths) * 100
    medium_pct = medium / len(lengths) * 100
    long_pct = long_ / len(lengths) * 100
    
    print(f'   قصير (1-4): {short} ({short_pct:.0f}%)')
    print(f'   متوسط (5-12): {medium} ({medium_pct:.0f}%)')
    print(f'   طويل (13+): {long_} ({long_pct:.0f}%)')
    
    avg = sum(lengths) / len(lengths)
    print(f'   المتوسط: {avg:.1f} كلمة')
except Exception as e:
    errors.append(f'lengths: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 8: أهداف تسويقية
# ═══════════════════════════════════════════════════════════
print('\n📣 فحص الأهداف التسويقية...')
try:
    from collections import Counter
    goals = Counter(r.get('marketing_goal', 'unknown') for r in GOLDEN_REVIEWS)
    print(f'   📊 أهداف تسويقية متنوعة: {len(goals)}')
    for goal, count in goals.most_common(10):
        print(f'      {goal}: {count}')
except Exception as e:
    errors.append(f'marketing: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 9: رحلة العميل (stages)
# ═══════════════════════════════════════════════════════════
print('\n🗺️ فحص رحلة العميل...')
try:
    stages = Counter(r.get('stage', 'unknown') for r in GOLDEN_REVIEWS)
    print(f'   📊 مراحل العميل: {len(stages)}')
    for stage, count in stages.most_common():
        print(f'      {stage}: {count}')
except Exception as e:
    errors.append(f'stages: {e}')

# ═══════════════════════════════════════════════════════════
#  فحص 10: عينة من التقييمات الذهبية
# ═══════════════════════════════════════════════════════════
print('\n📝 عينة من كل نوع:')
try:
    for st in get_story_types():
        r = pick_golden_review(story_type=st)
        stars = '⭐' * r['rating']
        print(f'   [{st}] {stars}')
        print(f'   "{r["text"][:80]}..."')
        print()
except Exception as e:
    errors.append(f'sample: {e}')

# ═══════════════════════════════════════════════════════════
#  النتيجة النهائية
# ═══════════════════════════════════════════════════════════
print('=' * 70)
if not errors:
    print('✅ جميع الاختبارات نجحت!')
else:
    print(f'❌ {len(errors)} مشاكل:')
    for e in errors:
        print(f'   - {e}')
print('=' * 70)
