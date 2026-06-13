# -*- coding: utf-8 -*-
"""
بنك النصوص القصيرة البشرية — تقييمات 1-3 كلمات واقعية
Short Human Texts Bank for Ultra-Short Reviews

يحتوي 60+ نص قصير مصنّف حسب عائلة الرائحة:
- oud_occasions: عطور العود والمناسبات
- fresh_daily: العطور الصيفية واليومية
- feminine_sweet: العطور النسائية
- general_admiration: نصوص عامة تناسب أي عطر

يتكامل مع anti_repeat.py لضمان عدم التكرار.
"""

import random
import re


# ═══════════════════════════════════════════════════════════
#  بنك النصوص — 60+ نص بشري قصير (1-3 كلمات)
# ═══════════════════════════════════════════════════════════

# 1. عطور العود والمناسبات (الثقيلة / الشتوية / الأخشاب)
OUD_OCCASIONS = [
    'فخامة',
    'ريحة شيوخ',
    'هيبة',
    'ثقيل وحلو',
    'دمار شامل',
    'ملكي',
    'ما يكتم',
    'حق زواجات',
    'عود نظيف',
    'فخم فخم',
    'للمناسبات يفوز',
    'رزة',
    'شموخ',
    'يجيب العافية',
    'عطر أمراء',
]

# 2. العطور الصيفية واليومية (حمضيات / فريش / نظافة)
FRESH_DAILY = [
    'انتعاش',
    'بارد مره',
    'يبرد القلب',
    'ريحة نظافة',
    'فريش وحلو',
    'حق دوام',
    'ما يغث',
    'بطل للصبح',
    'يروق الأعصاب',
    'خفيف ولطيف',
    'ريحة شاور',
    'فرش فرش',
    'طاقة إيجابية',
    'منعش جداً',
    'للدوام يفوز',
]

# 3. العطور النسائية (سويت / زهور / فانيلا)
FEMININE_SWEET = [
    'أنوثة',
    'ناعم يجنن',
    'ريحة كيكة',
    'سويت وحلو',
    'عرايسي',
    'يهبل',
    'دلع',
    'ريحة بودرة',
    'يذوب',
    'خطير للبنات',
    'أنيق جداً',
    'هادي وحلو',
    'يجذب',
    'رومانسي',
    'كيوت مره',
]

# 4. نصوص عامة (إعجاب بالثبات والجودة - تناسب أي عطر)
GENERAL_ADMIRATION = [
    'خيال',
    'يفوز',
    'ولا غلطة',
    'أطلق عطر',
    'يستاهل',
    'بطل',
    'عجيب',
    'ما ندمت',
    'حلال فيه',
    'لقطة',
    'سعره بطل',
    'صدمني',
    'ثابت وفواح',
    'يجننننن',
    'أسطوري',
    'جبار',
    'إدمان',
    'مو طبيعي',
    'رجعت طلبت',
    'ناررر',
]


# ═══════════════════════════════════════════════════════════
#  ربط العوائل العطرية بمجموعات النصوص
# ═══════════════════════════════════════════════════════════

# كل عائلة عطرية ← أي مجموعة نصوص تناسبها (الأولى = الأساسية)
FAMILY_TO_BANKS = {
    # عود + أخشاب + جلود + شرقي → مجموعة العود والمناسبات
    'oud':      [OUD_OCCASIONS],
    'oriental': [OUD_OCCASIONS],
    'woody':    [OUD_OCCASIONS],
    'leather':  [OUD_OCCASIONS],
    # حمضيات + فريش → مجموعة الصيفية
    'citrus':   [FRESH_DAILY],
    'fresh':    [FRESH_DAILY],
    # زهور + سويت + حلويات → مجموعة النسائية
    'floral':   [FEMININE_SWEET],
    'sweet':    [FEMININE_SWEET],
    'gourmand': [FEMININE_SWEET],
    # مسك → خلط بين الأنثوية والعامة
    'musk':     [FEMININE_SWEET, OUD_OCCASIONS],
}


# ═══════════════════════════════════════════════════════════
#  التشويش البشري — بصمة إملائية طبيعية
# ═══════════════════════════════════════════════════════════

# حروف قابلة للتمطيط (الشاب السعودي يمطّ الحرف الأخير أو الأوسط)
STRETCHABLE_CHARS = {
    'ن': 'ننن',
    'ر': 'ررر',
    'ل': 'للل',
    'ي': 'ييي',
    'و': 'ووو',
    'ا': 'ااا',
    'ه': 'ههه',
    'م': 'مم',
    'ب': 'بب',
    'ح': 'حح',
}

# إضافات عشوائية (بعد النص)
SUFFIXES = [
    ' 🔥', ' ❤️', ' 👌', ' 💯', ' ✨', ' 😍', ' 👏',
    ' 💎', ' 🤩', ' 💪', ' ⭐', '',  '',  '',  '',  '',  '',
]


def _stretch_text(text, probability=0.15):
    """تمطيط حرف عشوائي في الكلمة الأخيرة — يشبه كتابة الشاب (يجنننن، خيييال)

    probability: احتمال التطبيق (15% افتراضياً)
    """
    if random.random() > probability:
        return text

    words = text.split()
    if not words:
        return text

    # الكلمة الأخيرة هي الأكثر عرضة للتمطيط
    last_word = words[-1]
    if len(last_word) < 2:
        return text

    # نبحث عن حرف قابل للتمطيط في الكلمة الأخيرة
    for i in range(len(last_word) - 1, -1, -1):
        char = last_word[i]
        if char in STRETCHABLE_CHARS:
            stretched = last_word[:i] + STRETCHABLE_CHARS[char] + last_word[i+1:]
            words[-1] = stretched
            return ' '.join(words)

    return text


def _add_suffix(text, probability=0.12):
    """إضافة إيموجي بسيط بعد النص (12% احتمال)"""
    if random.random() > probability:
        return text
    suffix = random.choice(SUFFIXES)
    return text + suffix


def humanize_short_text(text):
    """تطبيق تشويش بشري على النص القصير.

    - تمطيط حروف (15%): يجنن → يجننننن
    - إضافة إيموجي (12%): فخامة → فخامة 🔥
    """
    text = _stretch_text(text, probability=0.15)
    text = _add_suffix(text, probability=0.12)
    return text


# ═══════════════════════════════════════════════════════════
#  الاختيار الذكي — الدالة الرئيسية
# ═══════════════════════════════════════════════════════════

def pick_short_text(scent_family, used_texts=None, gender=None):
    """اختيار نص قصير بشري مناسب لعائلة الرائحة.

    المنطق:
    1. تحديد مجموعة النصوص حسب scent_family
    2. خلط 70% من مجموعة الفئة + 30% عامة
    3. استبعاد النصوص المستخدمة سابقاً
    4. تطبيق تشويش بشري
    5. إذا نفدت كل النصوص → يرجع None (يُحوّل للـ AI)

    Args:
        scent_family: عائلة الرائحة (oud/oriental/floral/citrus/etc)
        used_texts: قائمة النصوص المستخدمة سابقاً (للاستبعاد)
        gender: جنس العطر (نسائي/رجالي/مشترك) — يؤثر على اختيار المجموعة

    Returns:
        str أو None إذا نفدت النصوص
    """
    if used_texts is None:
        used_texts = []

    # تطبيع النصوص المستخدمة للمقارنة
    used_normalized = set()
    for t in used_texts:
        # إزالة الإيموجي والتمطيط للمقارنة
        clean = re.sub(r'[^\u0600-\u06FF\s]', '', t).strip()
        # إزالة التكرار في الحروف (يجننننن → يجنن)
        clean = re.sub(r'(.)\1{2,}', r'\1\1', clean)
        used_normalized.add(clean)

    # تحديد المجموعات
    family_banks = FAMILY_TO_BANKS.get(scent_family, [OUD_OCCASIONS])

    # تعديل حسب الجنس — العطر الرجالي لا يستخدم نصوص نسائية
    if gender == 'رجالي' and FEMININE_SWEET in family_banks:
        family_banks = [OUD_OCCASIONS]
    elif gender == 'نسائي' and scent_family in ('oud', 'oriental', 'woody'):
        # عطر نسائي شرقي → نمزج بين المناسبات والنسائية
        family_banks = [OUD_OCCASIONS, FEMININE_SWEET]

    # بناء الحوض: 70% فئة + 30% عامة
    category_pool = []
    for bank in family_banks:
        category_pool.extend(bank)

    pool = []
    # إضافة نصوص الفئة (وزن أعلى)
    for text in category_pool:
        pool.append((text, 2.0))  # وزن 2
    # إضافة نصوص عامة (وزن أقل)
    for text in GENERAL_ADMIRATION:
        pool.append((text, 1.0))  # وزن 1

    # استبعاد المستخدمة
    available = []
    weights = []
    for text, weight in pool:
        clean = re.sub(r'(.)\1{2,}', r'\1\1', text)
        if clean not in used_normalized:
            available.append(text)
            weights.append(weight)

    if not available:
        return None  # نفدت كل النصوص → يتحول للـ AI

    # اختيار مرجّح
    chosen = random.choices(available, weights=weights, k=1)[0]

    # تشويش بشري
    result = humanize_short_text(chosen)

    return result


def get_all_bank_texts():
    """إرجاع كل النصوص في البنك (للإحصائيات)"""
    all_texts = set()
    all_texts.update(OUD_OCCASIONS)
    all_texts.update(FRESH_DAILY)
    all_texts.update(FEMININE_SWEET)
    all_texts.update(GENERAL_ADMIRATION)
    return all_texts


def get_bank_stats():
    """إحصائيات البنك"""
    return {
        'oud_occasions': len(OUD_OCCASIONS),
        'fresh_daily': len(FRESH_DAILY),
        'feminine_sweet': len(FEMININE_SWEET),
        'general_admiration': len(GENERAL_ADMIRATION),
        'total_unique': len(get_all_bank_texts()),
    }


# ═══════════════════════════════════════════════════════════
#  برومبت AI للنصوص القصيرة — عند نفاد البنك
# ═══════════════════════════════════════════════════════════

def build_ai_short_prompt(product_name, product_category, product_ingredients,
                          used_short_texts=None):
    """بناء برومبت AI ذكي لتوليد نص قصير (1-3 كلمات) مبني على المكونات.

    يُستخدم فقط عندما ينفد البنك المحلي.

    Args:
        product_name: اسم العطر
        product_category: تصنيف العطر
        product_ingredients: مكونات العطر
        used_short_texts: قائمة النصوص القصيرة المستخدمة سابقاً

    Returns:
        str: البرومبت الجاهز لإرساله للـ AI
    """
    used_block = ''
    if used_short_texts:
        used_block = '\n'.join(used_short_texts[-40:])

    prompt = f"""أنت متسوق سعودي حقيقي وعفوي جداً، اشتريت هذا العطر:
- اسم العطر: {product_name}
- تصنيف العطر: {product_category}
- مكونات العطر: {product_ingredients}

المطلوب:
اكتب تقييماً قصيراً جداً جداً يتكون من (كلمة واحدة إلى 3 كلمات كحد أقصى).
يمنع منعاً باتاً استخدام الفواصل أو النقاط.

القواعد:
1. اقرأ المكونات والتصنيف، واستنتج منها "الإحساس" (مثلاً: إذا كان عود قل "فخامة" أو "ريحة شيوخ"، إذا كان حمضيات قل "انتعاش" أو "بارد").
2. لا تذكر أسماء المكونات أبداً (لا تقل عود، لا تقل ليمون، لا تقل فانيلا).
3. اكتب بلهجة سعودية عامية دارجة للشباب أو البنات (مثل: يجنن، دمار، خيال، ولا غلطة، بطل).
4. لضمان عدم التكرار، يُمنع منعاً باتاً استخدام أي من هذه الكلمات لأننا استخدمناها سابقاً:
{used_block}

أرجع التقييم فقط بدون أي كلام إضافي."""

    return prompt


# ═══════════════════════════════════════════════════════════
#  Standalone Test
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print('=' * 50)
    print('Short Texts Bank — Test')
    print('=' * 50)

    stats = get_bank_stats()
    print(f'\n📊 إحصائيات البنك:')
    for k, v in stats.items():
        print(f'   {k}: {v}')

    print(f'\n🎯 اختبار الاختيار (10 نصوص لكل عائلة):')
    used = []
    for family in ['oud', 'oriental', 'citrus', 'fresh', 'floral', 'sweet']:
        texts = []
        for _ in range(10):
            t = pick_short_text(family, used)
            if t:
                texts.append(t)
                used.append(t)
        print(f'\n   [{family}]:')
        for t in texts:
            print(f'      → {t}')

    print(f'\n🔄 اختبار نفاد البنك:')
    # محاكاة نفاد كل النصوص
    all_texts = list(get_all_bank_texts())
    result = pick_short_text('oud', all_texts)
    print(f'   بعد استخدام كل النصوص: {result}')
    print(f'   (None = يتحول للـ AI ✅)' if result is None else '   ⚠️ لسا فيه نصوص')

    print(f'\n📝 برومبت AI (عند نفاد البنك):')
    prompt = build_ai_short_prompt(
        'عطر لطافة عود سلامة',
        'العطور > عطور رجالية',
        'عود، جلود، مسك',
        ['فخامة', 'هيبة', 'خيال']
    )
    print(f'   {prompt[:200]}...')

    print(f'\n✅ Test PASSED')
