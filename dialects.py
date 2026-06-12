# -*- coding: utf-8 -*-
"""
محرك اللهجات السعودية — Saudi Dialect Engine
4 لهجات مع ربط المدن والتعابير وكلمات الحشو والأخطاء الإملائية
"""
import random

# ═══════════════════════════════════════════════════════════
#  اللهجات الأربعة الرئيسية
# ═══════════════════════════════════════════════════════════

DIALECTS = {
    'najdi': {  # نجدية — الرياض / القصيم / حائل
        'name': 'نجدية',
        'cities': ['الرياض', 'بريدة', 'حائل', 'عنيزة', 'الزلفي', 'شقراء', 'الدوادمي', 'المجمعة'],
        'expressions': [
            'مرة حلو', 'والله كفو', 'ذا الشي يجنن', 'ما عليه كلام',
            'وش ذا الجمال', 'يستاهل كل ريال', 'طيّب مرة',
            'ما توقعته كذا', 'الله يعطيهم العافية', 'ذا غييير',
            'لا يعلى عليه', 'شي ما يتوصف', 'كفو والله',
            'يا حليله', 'من جد روعة', 'بالذمة حلو',
            'ما شفت مثله', 'عاد ذا شي ثاني', 'خرافي مو طبيعي',
        ],
        'filler_words': ['يعني', 'والله', 'بصراحة', 'الصراحة', 'عاد', 'بس', 'طيب'],
        'greetings': ['الله يعطيهم العافية', 'ماشاء الله', 'الله يبارك'],
        'emphasis': ['مرة', 'مررة', 'كثير', 'وايد', 'حيل'],
    },
    'hijazi': {  # حجازية — جدة / مكة / المدينة / الطائف
        'name': 'حجازية',
        'cities': ['جدة', 'مكة المكرمة', 'المدينة المنورة', 'الطائف', 'ينبع', 'رابغ'],
        'expressions': [
            'كتير حلو', 'يا سلام', 'حبيته مرررة', 'قوي والله',
            'دحين صار المفضل', 'ما شفت زيه', 'حاجة تجنن',
            'عجبني كتير', 'لازق معاي', 'رهييب',
            'شي فاخر', 'والله حاجة ثانية', 'يا سلام عليه',
            'حبيته من أول ما شميته', 'بصراحة مرة حلو',
            'حاجة مختلفة عن الباقي', 'ما في زيه بجد',
        ],
        'filler_words': ['كده', 'دحين', 'يعني', 'أساساً', 'بجد', 'والله', 'بصراحة'],
        'greetings': ['يا سلام', 'ما شاء الله', 'الله يسعدهم'],
        'emphasis': ['مرة', 'مررة', 'كتير', 'أووي', 'حيل'],
    },
    'sharqi': {  # شرقية — الدمام / الخبر / الأحساء / الجبيل
        'name': 'شرقية',
        'cities': ['الدمام', 'الخبر', 'الأحساء', 'الجبيل', 'الظهران', 'القطيف', 'حفر الباطن'],
        'expressions': [
            'فله', 'حلو واجد', 'يجنن', 'مرة حلو والله',
            'ما يبيله كلام', 'شي خيالي', 'واجد حلو',
            'عجيب مو طبيعي', 'خوش عطر', 'حده حلو',
            'شكله غالي بس يستاهل', 'ما عليه زود',
            'والله إنه حلو', 'يا خي شي ثاني',
            'هالشي مو طبيعي', 'فله والله',
        ],
        'filler_words': ['يعني', 'هالشي', 'والله', 'بعد', 'شكله', 'أوكي'],
        'greetings': ['ماشاء الله عليه', 'يا سلام', 'تستاهل'],
        'emphasis': ['واجد', 'مرة', 'حده', 'بزاف', 'كثير'],
    },
    'janoubi': {  # جنوبية — أبها / خميس مشيط / نجران / جازان
        'name': 'جنوبية',
        'cities': ['أبها', 'خميس مشيط', 'نجران', 'جازان', 'الباحة', 'بيشة'],
        'expressions': [
            'زين مرة', 'حلو كثير', 'ما قصروا', 'طيب',
            'والله حلو', 'كثير زين', 'يستاهل',
            'طيب مرة', 'والنعم', 'زين ما عليه كلام',
            'حلو والله ما يغلى عليه', 'ما قصّر المتجر',
        ],
        'filler_words': ['يعني', 'بس', 'والله', 'والنعم', 'ذا'],
        'greetings': ['والنعم والله', 'ما شاء الله', 'الله يطيبه'],
        'emphasis': ['كثير', 'مرة', 'زود', 'واجد'],
    },
}

# ═══════════════════════════════════════════════════════════
#  ربط المدن باللهجات (للتحديد التلقائي)
# ═══════════════════════════════════════════════════════════

_CITY_TO_DIALECT = {}
for dialect_key, dialect_data in DIALECTS.items():
    for city in dialect_data['cities']:
        _CITY_TO_DIALECT[city] = dialect_key

def get_dialect_for_city(city_name):
    """تحديد لهجة المدينة تلقائياً"""
    dialect = _CITY_TO_DIALECT.get(city_name)
    if dialect:
        return dialect
    # fallback: بحث جزئي
    for city, d in _CITY_TO_DIALECT.items():
        if city in city_name or city_name in city:
            return d
    return 'najdi'  # default

def get_dialect_data(dialect_key):
    """جلب بيانات لهجة معينة"""
    return DIALECTS.get(dialect_key, DIALECTS['najdi'])

def get_random_expression(dialect_key):
    """تعبير عشوائي من اللهجة"""
    data = get_dialect_data(dialect_key)
    return random.choice(data['expressions'])

def get_random_filler(dialect_key):
    """كلمة حشو عشوائية"""
    data = get_dialect_data(dialect_key)
    return random.choice(data['filler_words'])

def get_random_emphasis(dialect_key):
    """كلمة تأكيد عشوائية"""
    data = get_dialect_data(dialect_key)
    return random.choice(data['emphasis'])

def get_dialect_examples(dialect_key, count=4):
    """أمثلة من اللهجة (لإرسالها في prompt الـ AI)"""
    data = get_dialect_data(dialect_key)
    examples = random.sample(data['expressions'], min(count, len(data['expressions'])))
    return '\n'.join([f'- {e}' for e in examples])

def get_all_cities():
    """كل المدن مع لهجاتها"""
    result = []
    for dialect_key, data in DIALECTS.items():
        for city in data['cities']:
            result.append({'city': city, 'dialect': dialect_key, 'dialect_name': data['name']})
    return result

# ═══════════════════════════════════════════════════════════
#  الأخطاء الإملائية الطبيعية (10% من التقييمات)
# ═══════════════════════════════════════════════════════════

NATURAL_TYPOS = {
    'مرة': ['مررة', 'مره'],
    'وايد': ['واايد', 'وآيد'],
    'حلو': ['حلوو', 'حلووو'],
    'ممتاز': ['ممتااز', 'متاز'],
    'روعة': ['روووعة', 'روعه'],
    'الله': ['اللله', 'اله'],
    'ماشاء': ['ماشاءالله', 'ماشالله'],
    'إن شاء الله': ['انشاءالله', 'ان شاء الله', 'انشالله'],
    'يجنن': ['يجننن', 'يجنن!'],
    'رهيب': ['رهييب', 'رهيييب'],
    'خرافي': ['خرااافي', 'خرافيي'],
    'كثير': ['كثيير', 'كثييير'],
    'بصراحة': ['بصراحه', 'بصرااحة'],
    'تجنن': ['تجننن', 'تجنن!'],
    'والله': ['واللله', 'والله!'],
    'ريحته': ['ريحتة', 'ريحتو'],
    'يستاهل': ['يستااهل', 'يستاهل!'],
    'أنصح': ['انصح', 'أنصصح'],
    'طيب': ['طييب', 'طيبب'],
    'فخم': ['فخخم', 'فخمم'],
}

def apply_typos(text, probability=0.10):
    """تطبيق خطأ إملائي طبيعي واحد على النص.

    probability: احتمال محاولة الإضافة (الشخصيات تمرّر 1.0 لأن has_typo نفسه نسبته 10%).
    عند المحاولة نضمن خطأً فعلياً: كلمة من قاموس الأخطاء إن وُجدت، وإلا إطالة حرف
    في كلمة طويلة (خطأ شائع طبيعي) — حتى لا تكون الخاصية بلا أثر.
    """
    if random.random() > probability:
        return text

    words = text.split()
    if not words:
        return text

    # 1) كلمات لها أخطاء طبيعية معروفة في القاموس
    candidates = [i for i, w in enumerate(words) if w.strip('.,!؟') in NATURAL_TYPOS]
    if candidates:
        i = random.choice(candidates)
        clean = words[i].strip('.,!؟')
        words[i] = words[i].replace(clean, random.choice(NATURAL_TYPOS[clean]))
        return ' '.join(words)

    # 2) احتياطي: ضاعف حرفاً وسط كلمة طويلة (إطالة طبيعية شائعة)
    long_idx = [i for i, w in enumerate(words) if len(w.strip('.,!؟')) >= 4]
    if long_idx:
        i = random.choice(long_idx)
        w = words[i]
        pos = len(w) // 2
        words[i] = w[:pos] + w[pos] + w[pos:]
        return ' '.join(words)

    return text


# ═══════════════════════════════════════════════════════════
#  Standalone Test
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('✅ Dialects loaded')
    print(f'   اللهجات: {len(DIALECTS)}')
    for key, data in DIALECTS.items():
        print(f'   {data["name"]}: {len(data["cities"])} مدينة, {len(data["expressions"])} تعبير')
    
    print(f'\n   الرياض → {get_dialect_for_city("الرياض")}')
    print(f'   جدة → {get_dialect_for_city("جدة")}')
    print(f'   الدمام → {get_dialect_for_city("الدمام")}')
    print(f'   أبها → {get_dialect_for_city("أبها")}')
    
    print(f'\n   تعبير نجدي: {get_random_expression("najdi")}')
    print(f'   تعبير حجازي: {get_random_expression("hijazi")}')
    
    original = 'ممتاز مرة والله ريحته حلو'
    typo_version = apply_typos(original, probability=1.0)
    print(f'\n   أصلي: {original}')
    print(f'   بخطأ: {typo_version}')
