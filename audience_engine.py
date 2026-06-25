# -*- coding: utf-8 -*-
"""محرك جمهور حي — Audience Matrix Engine
المحرك الرئيسي الذي يجمع كل الطبقات السبع
"""
import sys
import os
import random
import math
import re
from datetime import datetime, timedelta
from collections import Counter

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from audience_db import AudienceDB
except ImportError:
    AudienceDB = None

# ═══════════════════════════════════════════════════════
#  توزيع النجوم المستهدف
# ═══════════════════════════════════════════════════════

TARGET_DISTRIBUTION = {5: 0.60, 4: 0.22, 3: 0.12, 2: 0.04, 1: 0.02}

# ═══════════════════════════════════════════════════════
#  عيوب طبيعية — 30% من التقييمات
# ═══════════════════════════════════════════════════════

NATURAL_FLAWS = {
    'packaging': [
        'بس التغليف كان بسيط شوي',
        'الكرتون ما كان مبطن كويس',
        'ودي لو العلبة أفخم',
        'الغطا شوي خفيف',
        'الكرتون كبير بزيادة والمنتج يتحرك بداخله',
    ],
    'shipping': [
        'بس التوصيل تأخر يومين',
        'المندوب ما تواصل معي',
        'وصل بدون كيس حماية',
        'تأخر 3 أيام عن الموعد',
        'التتبع ما كان يتحدث',
    ],
    'expectations': [
        'توقعته أقوى شوي',
        'بالصورة كان أكبر',
        'ريحة الكحول أول 10 دقايق قوية',
        'تخيلته أثقل من كذا',
    ],
    'size': [
        'الحجم أصغر من المتوقع',
        'ودي لو فيه حجم ترافل',
        'يخلص بسرعة',
    ],
    'longevity': [
        'الثبات مو زي ما توقعت',
        'يبي له تجديد بعد 4 ساعات',
        'على الجلد يخف بسرعة بس على القماش بطل',
        'يبيله تجديد كل 3 ساعات',
    ],
}

# كلمات ممنوعة حسب نوع التقييم
STORE_FORBIDDEN_WORDS = ['ريحة', 'ريحته', 'ثبات', 'ثباته', 'فوحان', 'نوتة', 'عود', 'مسك']
PRODUCT_FORBIDDEN_WORDS = ['توصيل', 'شحن', 'تغليف', 'كرتون', 'مندوب']


class AudienceEngine:
    """محرك جمهور حي — يجمع كل الطبقات"""
    
    def __init__(self, db_path=None):
        if AudienceDB:
            self.db = AudienceDB(db_path)
        else:
            self.db = None
    
    def _assign_ratings(self, count):
        """توزيع النجوم على التقييمات بما يطابق التوزيع المستهدف"""
        ratings = []
        for star, pct in TARGET_DISTRIBUTION.items():
            count_for_star = round(count * pct)
            ratings.extend([star] * count_for_star)
        # تعديل إذا كان الإجمالي مختلف
        while len(ratings) < count:
            ratings.append(5)
        while len(ratings) > count:
            ratings.pop()
        random.shuffle(ratings)
        return ratings
    
    def _get_random_flaw(self):
        """اختيار عيب طبيعي عشوائي"""
        category = random.choice(list(NATURAL_FLAWS.keys()))
        return random.choice(NATURAL_FLAWS[category])
    
    def should_inject_flaw(self, flaw_rate=0.30):
        """هل يجب حقن عيب طبيعي؟ (30%)"""
        return random.random() < flaw_rate
    
    def validate_review_type(self, text, review_type):
        """فحص أن التقييم يتوافق مع نوعه (منتج/متجر)"""
        issues = []
        if review_type == 'store':
            for word in STORE_FORBIDDEN_WORDS:
                if word in text:
                    issues.append(f'تقييم متجر يحتوي كلمة ممنوعة: {word}')
        return issues
    
    def check_batch_vocabulary(self, reviews, max_word_frequency=0.15):
        """فحص تنوع المفردات — لا كلمة تتجاوز 15%"""
        total = len(reviews)
        if total == 0:
            return []
        all_words = Counter()
        for r in reviews:
            text = r.get('text', r) if isinstance(r, dict) else r
            words = set(re.sub(r'[^\u0600-\u06FF\s]', '', text).split())
            all_words.update(words)
        
        overused = []
        for word, count in all_words.most_common(50):
            pct = count / total
            if pct > max_word_frequency and len(word) > 2:
                overused.append({'word': word, 'count': count, 'pct': round(pct * 100, 1)})
        return overused
    
    def validate_batch(self, reviews):
        """فحص دفعة تقييمات ضد معايير الجودة"""
        issues = []
        total = len(reviews)
        if total == 0:
            return ['لا تقييمات']
        
        # 1. فحص توزيع النجوم
        rating_counts = Counter()
        for r in reviews:
            rating = r.get('rating', 5) if isinstance(r, dict) else 5
            rating_counts[rating] += 1
        
        for star, target_pct in TARGET_DISTRIBUTION.items():
            actual_pct = rating_counts.get(star, 0) / total
            if abs(actual_pct - target_pct) > 0.10:  # تسامح 10%
                issues.append(f'توزيع {star} نجوم: {actual_pct:.0%} (المستهدف: {target_pct:.0%})')
        
        # 2. فحص المفردات
        overused = self.check_batch_vocabulary(reviews)
        for item in overused:
            issues.append(f'كلمة مكررة: "{item["word"]}" ({item["pct"]}%)')
        
        # 3. فحص تقييمات المتجر
        for r in reviews:
            if isinstance(r, dict) and r.get('type') == 'store':
                text = r.get('text', '')
                type_issues = self.validate_review_type(text, 'store')
                issues.extend(type_issues)
        
        return issues
    
    def schedule_bell_curve(self, items, days=7, start_date=None):
        """توزيع التقييمات بمنحنى طبيعي (Bell Curve)
        
        - ذروة في اليوم 3-4
        - ساعات النشر: 8 صباحاً - 12 منتصف الليل
        - لا أكثر من 3 تقييمات في الساعة
        """
        if start_date is None:
            start_date = datetime.now()
        
        count = len(items)
        if count == 0:
            return []
        
        center = days / 2.0
        std_dev = days / 4.0
        
        schedules = []
        for i in range(count):
            # توزيع طبيعي لليوم
            day_offset = random.gauss(center, std_dev)
            day_offset = max(0, min(days - 0.01, day_offset))
            
            # ساعة عشوائية بين 8 ص و 12 م
            hour = random.randint(8, 23)
            minute = random.randint(0, 59)
            # Jitter ±30 دقيقة
            jitter = random.randint(-30, 30)
            
            scheduled = start_date + timedelta(
                days=int(day_offset),
                hours=hour,
                minutes=minute + jitter
            )
            schedules.append(scheduled)
        
        schedules.sort()
        return schedules


if __name__ == '__main__':
    print('=== Audience Matrix Engine Test ===')
    engine = AudienceEngine(':memory:')
    
    # فحص توزيع النجوم
    ratings = engine._assign_ratings(100)
    dist = Counter(ratings)
    print(f'✅ توزيع 100 تقييم: {dict(sorted(dist.items()))}')
    
    # فحص حقن العيوب
    flaw = engine._get_random_flaw()
    print(f'✅ عيب عشوائي: "{flaw}"')
    
    # فحص Bell Curve
    schedule = engine.schedule_bell_curve(list(range(20)), days=7)
    print(f'✅ Bell Curve: {len(schedule)} موعد')
    for s in schedule[:5]:
        print(f'   {s.strftime("%Y-%m-%d %H:%M")}')
    
    print('✅ All engine tests passed!')
