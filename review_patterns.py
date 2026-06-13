# -*- coding: utf-8 -*-
"""
أنماط التقييمات — 12 نمط واقعي مع أوزان وتوزيع نجوم
Review Patterns Engine
"""
import random

# ═══════════════════════════════════════════════════════════
#  الأنماط الـ 12 — كل نمط بوزن ونطاق كلمات ووصف
# ═══════════════════════════════════════════════════════════

REVIEW_PATTERNS = {
    'ultra_short': {
        'weight': 25,
        'words': (1, 3),
        'desc': 'كلمة أو كلمتين فقط',
        'desc_en': 'Ultra-short review (1-3 words only)',
        'examples': [
            'ممتاز', 'حلو', 'روعة', 'كفو', 'طيب مرة',
            'جميل', 'رائع', 'خرافي', 'يجنن', 'فخم',
            'ممتاز ممتاز', 'حلو مرة', 'روعة والله',
        ],
    },
    'delivery': {
        'weight': 12,
        'words': (3, 8),
        'desc': 'عن سرعة التوصيل',
        'desc_en': 'About delivery speed and experience',
        'examples': [
            'وصلني بسرعة', 'الشحن سريع ماشاء الله', 'وصل خلال يومين',
            'التوصيل سريع ومرتب', 'وصلني أسرع مما توقعت',
        ],
    },
    'packaging': {
        'weight': 8,
        'words': (3, 10),
        'desc': 'عن التغليف والتعبئة',
        'desc_en': 'About packaging quality',
        'examples': [
            'التغليف نظيف ومرتب', 'وصل مغلف بشكل فخم', 'التغليف يصلح كهدية',
        ],
    },
    'scent_no_name': {
        'weight': 15,
        'words': (3, 12),
        'desc': 'عن الريحة بدون ذكر الاسم',
        'desc_en': 'About the scent without mentioning product name',
        'examples': [
            'ريحته فخمة', 'الريحة تجنن', 'ريحته مميزة والله',
            'ريحة حلوة وثابتة', 'ريحته رجالية فخمة',
        ],
    },
    'longevity': {
        'weight': 10,
        'words': (3, 10),
        'desc': 'عن الثبات والفوحان',
        'desc_en': 'About longevity and projection',
        'examples': [
            'يثبت طول اليوم', 'الثبات خرافي', 'ما يروح بسرعة',
            'ثباته ممتاز حتى بالحر', 'يدوم ساعات طويلة',
        ],
    },
    'gift': {
        'weight': 8,
        'words': (4, 12),
        'desc': 'اشتراه هدية لشخص',
        'desc_en': 'Bought as a gift for someone',
        'examples': [
            'جبته هدية وانبسطوا فيه', 'هديته خوي وعجبه',
            'أخذته هدية للوالد وفرح فيه',
        ],
    },
    'repeat_buy': {
        'weight': 8,
        'words': (4, 10),
        'desc': 'يكرر الشراء',
        'desc_en': 'Repeat purchase',
        'examples': [
            'ثاني مرة أطلب', 'مو أول مرة وبإذن الله مو الأخيرة',
            'خلّصت الأول وطلبت الثاني على طول',
        ],
    },
    'comparison': {
        'weight': 5,
        'words': (5, 15),
        'desc': 'مقارنة بمنتج أو متجر آخر',
        'desc_en': 'Comparison with another product or store',
        'examples': [
            'أحسن من اللي عندي', 'سعره أحلى من المحلات',
            'جربت غيره وهذا الأفضل',
        ],
    },
    'with_note': {
        'weight': 5,
        'words': (5, 12),
        'desc': 'إيجابي مع ملاحظة بسيطة',
        'desc_en': 'Positive with a small note/criticism',
        'examples': [
            'حلو بس خفيف شوي', 'كويس بس التوصيل تأخر',
            'ريحته حلوة بس الحجم صغير',
        ],
    },
    'emotional': {
        'weight': 3,
        'words': (5, 15),
        'desc': 'عاطفي أو ذكرى',
        'desc_en': 'Emotional or memory-based review',
        'examples': [
            'ذكرني بعطر أبوي الله يرحمه', 'كل ما أشمّه أتذكر أيام الجامعة',
            'صار العطر المفضل عندي ومرتبط بذكريات حلوة',
        ],
    },
    'store_mention': {
        'weight': 3,
        'words': (5, 12),
        'desc': 'يمدح المتجر مع المنتج',
        'desc_en': 'Praises both store and product',
        'examples': [
            'المتجر ممتاز والعطر أفضل', 'خدمة ممتازة والمنتج أصلي',
            'شكراً لمهووس عطر ممتاز وتوصيل سريع',
        ],
    },
    'expert_detail': {
        'weight': 2,
        'words': (10, 25),
        'desc': 'تقييم خبير بالنوتات',
        'desc_en': 'Expert review mentioning notes and composition',
        'examples': [
            'افتتاحيته حمضية منعشة وقلبه خشبي والقاعدة مسك أبيض',
            'تركيبته متوازنة بين العود والورد الطائفي مع قاعدة عنبرية',
        ],
    },
    'season': {
        'weight': 6,
        'words': (4, 12),
        'desc': 'مناسبته للموسم (شتوي/صيفي)',
        'desc_en': 'Seasonal suitability (winter/summer)',
        'examples': [
            'دافي وشتوي يجنن', 'مثالي للصيف خفيف ومنعش',
            'حطيته بالبرد وكان رهيب', 'للأجواء الحارة ممتاز ما يثقل',
        ],
    },
    'dupe_compare': {
        'weight': 5,
        'words': (5, 15),
        'desc': 'مقارنة بعطر مشهور أو بديل أرخص',
        'desc_en': 'Compared to a famous designer/niche or as a cheaper dupe',
        'examples': [
            'قريب من عطر غالي جربته بس بنص السعر', 'بديل ممتاز للعطر الأصلي',
            'يشبه ريحة عطر مشهور والثبات أحسن',
        ],
    },
    'skin_reaction': {
        'weight': 4,
        'words': (5, 14),
        'desc': 'تفاعله مع البشرة/الكيمياء',
        'desc_en': 'How it reacts with skin chemistry',
        'examples': [
            'على بشرتي طلع أحلى من القماش', 'يتفاعل مع جلدي ويطلع دافي',
            'على جسمي ثباته أقوى من ما توقعت',
        ],
    },
    'second_opinion': {
        'weight': 4,
        'words': (5, 14),
        'desc': 'رأي شخص قريب (الزوجة/الربع/الأهل)',
        'desc_en': "Someone else's reaction (spouse/friends/family)",
        'examples': [
            'زوجتي قالت ريحته تجنن', 'الربع سألوني عنه أول ما جلست',
            'أهل البيت كلهم عجبهم',
        ],
    },
    'occasion_specific': {
        'weight': 4,
        'words': (5, 14),
        'desc': 'لمناسبة محددة (عيد/رمضان/عرس/جمعة)',
        'desc_en': 'For a specific occasion (Eid/Ramadan/wedding/Friday)',
        'examples': [
            'لبسته بالعيد وكان مميز', 'حطيته للتراويح برمضان وريحته تشرح',
            'استخدمته بعرس وكان الاختيار الصح',
        ],
    },
    'value_focus': {
        'weight': 5,
        'words': (4, 12),
        'desc': 'القيمة مقابل السعر',
        'desc_en': 'Value for money focus',
        'examples': [
            'قيمته أعلى من سعره بمراحل', 'بهالسعر صفقة ما تتعوض',
            'دفعت قليل وحصلت فخامة',
        ],
    },
}

# ═══════════════════════════════════════════════════════════
#  توزيع النجوم الواقعي
# ═══════════════════════════════════════════════════════════

RATING_DISTRIBUTION = {
    5: 60,  # 60%
    4: 25,  # 25%
    3: 10,  # 10% — يذكر سبب بسيط
    2: 4,   # 4%  — مشكلة واقعية
    1: 1,   # 1%  — نادر جداً
}

# أسباب التقييم المنخفض (3 وأقل)
LOW_RATING_REASONS = {
    3: [
        'الثبات ضعيف شوي', 'الحجم صغير على السعر', 'ما يشبه الوصف بالضبط',
        'الريحة حلوة بس ما تثبت', 'التغليف عادي مو فخم',
        'حلو بس مو بالمستوى اللي توقعته', 'كويس بس في أحسن منه',
        'ريحته حلوة بس خفيفة مرة', 'الفوحان ضعيف',
    ],
    2: [
        'ما عجبني الريحة أبداً', 'غير اللي شفته بالصور', 'سعره غالي على جودته',
        'الثبات صفر تقريباً', 'ريحته تتغير بعد ساعة', 'مو أصلي حسيت',
        'التوصيل تأخر كثير والعلبة مكسورة',
    ],
    1: [
        'أسوأ عطر جربته', 'ريحته مو حلوة أبداً', 'غلط بالطلب وما ردوا علي',
    ],
}


def pick_pattern(used_patterns=None):
    """اختيار نمط عشوائي بناءً على الأوزان مع تجنب التكرار"""
    patterns = list(REVIEW_PATTERNS.keys())
    weights = [REVIEW_PATTERNS[p]['weight'] for p in patterns]
    
    # تقليل وزن الأنماط المستخدمة مؤخراً
    if used_patterns:
        for i, p in enumerate(patterns):
            count = used_patterns.get(p, 0)
            if count > 0:
                weights[i] = max(1, weights[i] // (count + 1))
    
    chosen = random.choices(patterns, weights=weights, k=1)[0]
    return chosen


def get_pattern_info(pattern_name):
    """معلومات نمط معين"""
    return REVIEW_PATTERNS.get(pattern_name, REVIEW_PATTERNS['ultra_short'])


def pick_rating():
    """اختيار تقييم نجوم بناءً على التوزيع الواقعي"""
    ratings = list(RATING_DISTRIBUTION.keys())
    weights = list(RATING_DISTRIBUTION.values())
    return random.choices(ratings, weights=weights, k=1)[0]


def get_low_rating_reason(rating):
    """سبب التقييم المنخفض"""
    if rating > 3:
        return ''
    reasons = LOW_RATING_REASONS.get(rating, LOW_RATING_REASONS[3])
    return random.choice(reasons)


def get_pattern_description(pattern_name):
    """وصف النمط لإرساله في prompt الـ AI"""
    info = get_pattern_info(pattern_name)
    desc = info['desc']
    words = info['words']
    return f'{desc} ({words[0]}-{words[1]} كلمة)'


def get_all_patterns_summary():
    """ملخص كل الأنماط"""
    summary = []
    total_weight = sum(p['weight'] for p in REVIEW_PATTERNS.values())
    for name, info in REVIEW_PATTERNS.items():
        pct = round(info['weight'] / total_weight * 100, 1)
        summary.append({
            'name': name,
            'desc': info['desc'],
            'weight': info['weight'],
            'percentage': pct,
            'words': info['words'],
        })
    return summary


# ═══════════════════════════════════════════════════════════
#  Standalone Test
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('✅ Review Patterns loaded')
    print(f'   الأنماط: {len(REVIEW_PATTERNS)}')
    
    total = sum(p['weight'] for p in REVIEW_PATTERNS.values())
    for name, info in REVIEW_PATTERNS.items():
        pct = round(info['weight'] / total * 100, 1)
        print(f'   {name}: {pct}% ({info["words"][0]}-{info["words"][1]} كلمة) — {info["desc"]}')
    
    print(f'\n   توزيع النجوم:')
    for stars, pct in RATING_DISTRIBUTION.items():
        print(f'   {"★" * stars}{"☆" * (5-stars)}: {pct}%')
    
    print(f'\n   نمط عشوائي: {pick_pattern()}')
    print(f'   تقييم عشوائي: {pick_rating()} نجوم')
