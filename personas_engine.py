# -*- coding: utf-8 -*-
"""
محرك الشخصيات العميقة — Deep Persona Engine
كل شخصية بـ 7 أبعاد: mood, expertise, writing_style, mention_product, use_emoji, has_typo, dialect
"""
import random
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ═══════════════════════════════════════════════════════════
#  تحميل الأسماء
# ═══════════════════════════════════════════════════════════

try:
    with open(BASE_DIR / 'names.json', 'r', encoding='utf-8') as f:
        NAMES = json.load(f)
except:
    NAMES = {'male': ['محمد'], 'female': ['نورة'], 'family_names': ['السعودي'], 'cities': [{'name': 'الرياض', 'weight': 1}]}

# import اللهجات
try:
    from dialects import get_dialect_for_city, get_dialect_data, get_dialect_examples, apply_typos
except ImportError:
    def get_dialect_for_city(c): return 'najdi'
    def get_dialect_data(d): return {'name': 'نجدية', 'expressions': ['حلو'], 'filler_words': ['يعني']}
    def get_dialect_examples(d, c=4): return '- حلو'
    def apply_typos(t, p=0.1): return t

# import الأنماط
try:
    from review_patterns import pick_pattern, pick_rating, get_pattern_description, get_low_rating_reason
except ImportError:
    def pick_pattern(u=None): return 'ultra_short'
    def pick_rating(): return 5
    def get_pattern_description(p): return 'كلمة أو كلمتين فقط (1-3 كلمة)'
    def get_low_rating_reason(r): return ''

# ═══════════════════════════════════════════════════════════
#  الشخصيات الأساسية (من app.py الأصلي — لا تتغير)
# ═══════════════════════════════════════════════════════════

ARCHETYPES = [
    {'id': 'شاب_جامعي', 'g': 'male', 'label': 'شاب جامعي', 'emoji': '🎓', 'age': (18, 23), 'price': (0, 300), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'رجل_أعمال', 'g': 'male', 'label': 'رجل أعمال', 'emoji': '👔', 'age': (30, 50), 'price': (400, 2000), 'prefers': ['رجالي', 'مشترك'], 'count': (3, 6)},
    {'id': 'خبير_عطور', 'g': 'male', 'label': 'خبير عطور', 'emoji': '🧪', 'age': (25, 40), 'price': (200, 2000), 'prefers': ['رجالي', 'مشترك'], 'count': (3, 7)},
    {'id': 'أب_عائلة', 'g': 'male', 'label': 'أب عائلة', 'emoji': '👨‍👧', 'age': (35, 55), 'price': (100, 500), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'شاب_رياضي', 'g': 'male', 'label': 'شاب رياضي', 'emoji': '💪', 'age': (20, 30), 'price': (100, 400), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'كبير_سن', 'g': 'male', 'label': 'رجل كبير', 'emoji': '👴', 'age': (55, 75), 'price': (100, 600), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 3)},
    {'id': 'موظف', 'g': 'male', 'label': 'موظف', 'emoji': '🏢', 'age': (25, 45), 'price': (150, 500), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'بنت_عصرية', 'g': 'female', 'label': 'بنت عصرية', 'emoji': '💅', 'age': (20, 28), 'price': (100, 600), 'prefers': ['نسائي', 'مشترك'], 'count': (3, 6)},
    {'id': 'أم_سعودية', 'g': 'female', 'label': 'أم سعودية', 'emoji': '👩‍🦱', 'age': (38, 55), 'price': (100, 800), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 5)},
    {'id': 'عروس', 'g': 'female', 'label': 'عروس', 'emoji': '👰', 'age': (21, 30), 'price': (300, 2000), 'prefers': ['نسائي', 'مشترك'], 'count': (4, 8)},
    {'id': 'موظفة', 'g': 'female', 'label': 'موظفة', 'emoji': '👩‍💻', 'age': (24, 40), 'price': (150, 600), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 4)},
    {'id': 'خبيرة_تجميل', 'g': 'female', 'label': 'خبيرة تجميل', 'emoji': '💄', 'age': (25, 38), 'price': (200, 1000), 'prefers': ['نسائي', 'مشترك'], 'count': (3, 6)},
    {'id': 'طالبة', 'g': 'female', 'label': 'طالبة جامعية', 'emoji': '📚', 'age': (18, 23), 'price': (0, 250), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 3)},
    {'id': 'جدة', 'g': 'female', 'label': 'سيدة كبيرة', 'emoji': '👵', 'age': (55, 75), 'price': (100, 500), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 3)},
    {'id': 'مقارن', 'g': 'male', 'label': 'مقارن أسعار', 'emoji': '📊', 'age': (25, 40), 'price': (100, 600), 'prefers': ['رجالي', 'مشترك'], 'count': (3, 5)},
    {'id': 'هدايا_رجل', 'g': 'male', 'label': 'يشتري هدايا', 'emoji': '🎁', 'age': (25, 45), 'price': (200, 1000), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 4)},
    {'id': 'هدايا_أنثى', 'g': 'female', 'label': 'تشتري هدايا', 'emoji': '🎀', 'age': (22, 45), 'price': (200, 800), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'محب_تسوق', 'g': 'male', 'label': 'محب تسوق', 'emoji': '🛍️', 'age': (22, 35), 'price': (100, 800), 'prefers': ['رجالي', 'مشترك'], 'count': (3, 6)},
    {'id': 'محبة_تسوق', 'g': 'female', 'label': 'محبة تسوق', 'emoji': '👛', 'age': (22, 35), 'price': (100, 800), 'prefers': ['نسائي', 'مشترك'], 'count': (3, 6)},
    # ── شخصيات إضافية (توسعة) ──
    {'id': 'مبتعث', 'g': 'male', 'label': 'شاب مبتعث', 'emoji': '✈️', 'age': (22, 30), 'price': (150, 900), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'عسكري', 'g': 'male', 'label': 'منسوب عسكري', 'emoji': '🎖️', 'age': (24, 45), 'price': (150, 600), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'معلم', 'g': 'male', 'label': 'معلم', 'emoji': '🧑‍🏫', 'age': (28, 50), 'price': (150, 500), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'مهندس', 'g': 'male', 'label': 'مهندس', 'emoji': '👷', 'age': (26, 45), 'price': (200, 800), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'طبيب', 'g': 'male', 'label': 'طبيب', 'emoji': '🩺', 'age': (30, 52), 'price': (300, 1500), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'متذوق_نيش', 'g': 'male', 'label': 'متذوق نيش', 'emoji': '🌿', 'age': (25, 45), 'price': (400, 3000), 'prefers': ['رجالي', 'مشترك'], 'count': (3, 6)},
    {'id': 'عامل_مقتصد', 'g': 'male', 'label': 'يدوّر العملي', 'emoji': '🧰', 'age': (25, 50), 'price': (0, 180), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 3)},
    {'id': 'وجيه', 'g': 'male', 'label': 'وجيه ومحب عود', 'emoji': '🕌', 'age': (45, 70), 'price': (300, 2000), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 4)},
    {'id': 'بدوي', 'g': 'male', 'label': 'محب البخور والعود', 'emoji': '🐪', 'age': (30, 60), 'price': (100, 800), 'prefers': ['رجالي', 'مشترك'], 'count': (2, 3)},
    {'id': 'مؤثرة', 'g': 'female', 'label': 'مؤثرة عطور', 'emoji': '📸', 'age': (22, 35), 'price': (200, 1500), 'prefers': ['نسائي', 'مشترك'], 'count': (3, 6)},
    {'id': 'معلمة', 'g': 'female', 'label': 'معلمة', 'emoji': '👩‍🏫', 'age': (28, 50), 'price': (150, 500), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 4)},
    {'id': 'طبيبة', 'g': 'female', 'label': 'طبيبة', 'emoji': '👩‍⚕️', 'age': (30, 50), 'price': (300, 1200), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 4)},
    {'id': 'متذوقة_نيش', 'g': 'female', 'label': 'متذوقة نيش', 'emoji': '🌸', 'age': (25, 45), 'price': (400, 2500), 'prefers': ['نسائي', 'مشترك'], 'count': (3, 5)},
    {'id': 'ست_بيت', 'g': 'female', 'label': 'ست بيت', 'emoji': '🏠', 'age': (30, 55), 'price': (80, 400), 'prefers': ['نسائي', 'مشترك'], 'count': (2, 4)},
]

# ═══════════════════════════════════════════════════════════
#  المزاج ومستوى الخبرة وأسلوب الكتابة
# ═══════════════════════════════════════════════════════════

MOODS = ['متحمس', 'هادئ', 'ناقد', 'عملي', 'عاطفي']
MOOD_WEIGHTS = [30, 25, 10, 25, 10]

EXPERTISE_LEVELS = ['مبتدئ', 'متوسط', 'خبير']
EXPERTISE_WEIGHTS = [40, 45, 15]

WRITING_STYLES = ['مختصر', 'عادي', 'مفصّل']
WRITING_STYLE_WEIGHTS = [35, 45, 20]

# ═══════════════════════════════════════════════════════════
#  تعيين الخبرة المناسبة حسب نوع الشخصية
# ═══════════════════════════════════════════════════════════

ARCHETYPE_EXPERTISE_BIAS = {
    'خبير_عطور': {'مبتدئ': 0, 'متوسط': 20, 'خبير': 80},
    'خبيرة_تجميل': {'مبتدئ': 0, 'متوسط': 30, 'خبير': 70},
    'شاب_جامعي': {'مبتدئ': 60, 'متوسط': 35, 'خبير': 5},
    'طالبة': {'مبتدئ': 65, 'متوسط': 30, 'خبير': 5},
    'كبير_سن': {'مبتدئ': 50, 'متوسط': 40, 'خبير': 10},
    'جدة': {'مبتدئ': 55, 'متوسط': 40, 'خبير': 5},
    'رجل_أعمال': {'مبتدئ': 10, 'متوسط': 50, 'خبير': 40},
}


# ═══════════════════════════════════════════════════════════
#  المدن والعناوين (من app.py الأصلي)
# ═══════════════════════════════════════════════════════════

CITY_DATA = {
    'الرياض': {'postal_range': (11411, 13999), 'districts': [
        ('العليا', 'شارع العليا العام'), ('النخيل', 'شارع الأمير محمد بن سعد'), ('الملقا', 'طريق أنس بن مالك'),
        ('الياسمين', 'شارع عبدالرحمن الداخل'), ('حطين', 'شارع التخصصي'), ('الورود', 'شارع الورود'),
        ('السليمانية', 'شارع الأمير سلطان'), ('الربوة', 'طريق الإمام الشافعي'), ('المروج', 'طريق الملك فهد'),
        ('الصحافة', 'طريق أبو بكر الصديق'), ('النرجس', 'شارع محمد بن عبدالوهاب')]},
    'جدة': {'postal_range': (21411, 23999), 'districts': [
        ('الحمراء', 'شارع فلسطين'), ('الروضة', 'شارع الأمير سلطان'), ('الشاطئ', 'طريق الكورنيش'),
        ('البوادي', 'شارع الأمير ماجد'), ('الفيصلية', 'شارع الأمير فهد'), ('النعيم', 'شارع حراء'),
        ('المحمدية', 'شارع التحلية'), ('السامر', 'طريق المدينة')]},
    'الدمام': {'postal_range': (31411, 34999), 'districts': [
        ('الشاطئ', 'طريق الكورنيش'), ('الفيصلية', 'شارع الملك فيصل'), ('الريان', 'شارع الريان'),
        ('الجلوية', 'شارع الظهران'), ('المريكبات', 'شارع الملك خالد'), ('الأمانة', 'طريق الخليج')]},
    'مكة المكرمة': {'postal_range': (21955, 24999), 'districts': [
        ('العزيزية', 'طريق الملك عبدالعزيز'), ('الشوقية', 'شارع الشوقية'), ('النسيم', 'شارع النسيم'),
        ('الزاهر', 'شارع الزاهر'), ('الرصيفة', 'شارع إبراهيم الخليل')]},
    'المدينة المنورة': {'postal_range': (41411, 42999), 'districts': [
        ('العزيزية', 'طريق الملك عبدالله'), ('قربان', 'شارع قربان'), ('الحرة الشرقية', 'شارع سلطانة'),
        ('الدفاع', 'شارع أبو بكر الصديق'), ('المناخة', 'شارع المناخة')]},
    'الخبر': {'postal_range': (31411, 34999), 'districts': [
        ('الحزام الذهبي', 'شارع الأمير تركي'), ('اليرموك', 'شارع اليرموك'), ('العليا', 'شارع الأمير فيصل'),
        ('الثقبة', 'شارع الملك سعود'), ('الروابي', 'شارع الروابي')]},
    'أبها': {'postal_range': (61411, 62999), 'districts': [
        ('المنسك', 'شارع الملك فيصل'), ('الوردتين', 'شارع الأمير سلطان'), ('المفتاحة', 'شارع الفن')]},
    'تبوك': {'postal_range': (71411, 71999), 'districts': [
        ('المروج', 'شارع الأمير فهد'), ('الفيصلية', 'طريق الملك فهد'), ('السليمانية', 'شارع السلام')]},
    'بريدة': {'postal_range': (51411, 52999), 'districts': [
        ('الصفراء', 'شارع الخبيب'), ('الفايزية', 'طريق الملك عبدالعزيز'), ('الإسكان', 'شارع الحرمين')]},
    'حائل': {'postal_range': (81411, 81999), 'districts': [
        ('المنتزه', 'شارع الملك فيصل'), ('العزيزية', 'طريق الأمير سلطان'), ('النقرة', 'شارع النقرة')]},
    'الأحساء': {'postal_range': (31911, 36999), 'districts': [
        ('المبرز', 'شارع الخليج'), ('الهفوف', 'شارع الملك عبدالعزيز')]},
    'نجران': {'postal_range': (66411, 66999), 'districts': [
        ('الفهد', 'شارع الملك فهد'), ('الفيصلية', 'شارع الأمير فيصل')]},
    'جازان': {'postal_range': (82411, 82999), 'districts': [
        ('الروضة', 'شارع الأمير سلطان'), ('الشاطئ', 'طريق الكورنيش')]},
    'خميس مشيط': {'postal_range': (61911, 62999), 'districts': [
        ('أم سرار', 'شارع الملك فهد'), ('الراقي', 'شارع الأمير سلطان')]},
}

SAUDI_PREFIXES = ['050', '053', '054', '055', '056', '057', '058', '059']


def _pick_city():
    """اختيار مدينة بناءً على الأوزان"""
    cities = NAMES.get('cities', [{'name': 'الرياض', 'weight': 1}])
    return random.choices(cities, weights=[c.get('weight', 1) for c in cities], k=1)[0]['name']


def _make_name(gender):
    """توليد اسم كامل"""
    key = 'male' if gender == 'male' else 'female'
    first = random.choice(NAMES.get(key, ['مستخدم']))
    family = random.choice(NAMES.get('family_names', ['السعودي']))
    return f'{first} {family}'


def _make_phone():
    """توليد رقم جوال سعودي"""
    return random.choice(SAUDI_PREFIXES) + ''.join([str(random.randint(0, 9)) for _ in range(7)])


def _make_address(city_name):
    """توليد عنوان وطني سعودي"""
    cdata = CITY_DATA.get(city_name, {'postal_range': (11411, 13999), 'districts': [('المركز', 'شارع العام')]})
    dist, street = random.choice(cdata['districts'])
    building = str(random.randint(1000, 9999))
    postal = str(random.randint(*cdata['postal_range']))
    extra = str(random.randint(1000, 9999))
    return {
        'building': building, 'street': street, 'district': dist,
        'city': city_name, 'postal': postal, 'extra': extra,
        'full': f'{building} {street}، حي {dist}، {city_name} {postal} - {extra}'
    }


# ═══════════════════════════════════════════════════════════
#  توليد شخصية عميقة
# ═══════════════════════════════════════════════════════════

def generate_persona(archetype=None):
    """توليد شخصية كاملة بـ 7 أبعاد عميقة"""
    if archetype is None:
        archetype = random.choice(ARCHETYPES)
    
    age = random.randint(*archetype['age'])
    city = _pick_city()
    gender = archetype['g']
    name = _make_name(gender)
    
    # تحديد اللهجة من المدينة
    dialect = get_dialect_for_city(city)
    dialect_data = get_dialect_data(dialect)
    
    # المزاج
    mood = random.choices(MOODS, weights=MOOD_WEIGHTS, k=1)[0]
    
    # مستوى الخبرة (مع تحيز حسب الشخصية)
    bias = ARCHETYPE_EXPERTISE_BIAS.get(archetype['id'])
    if bias:
        exp_levels = list(bias.keys())
        exp_weights = list(bias.values())
        expertise = random.choices(exp_levels, weights=exp_weights, k=1)[0]
    else:
        expertise = random.choices(EXPERTISE_LEVELS, weights=EXPERTISE_WEIGHTS, k=1)[0]
    
    # أسلوب الكتابة
    writing_style = random.choices(WRITING_STYLES, weights=WRITING_STYLE_WEIGHTS, k=1)[0]
    
    # ذكر المنتج (40% فقط)
    mention_product = random.random() < 0.40
    
    # إيموجي (15% فقط)
    use_emoji = random.random() < 0.15
    
    # أخطاء إملائية (10%)
    has_typo = random.random() < 0.10
    
    return {
        # بيانات أساسية
        'name': name,
        'age': age,
        'city': city,
        'gender': gender,
        'label': archetype['label'],
        'emoji': archetype['emoji'],
        'archId': archetype['id'],
        'address': _make_address(city),
        'phone': _make_phone(),
        
        # الأبعاد الـ 7 الجديدة
        'mood': mood,
        'expertise': expertise,
        'writing_style': writing_style,
        'mention_product': mention_product,
        'use_emoji': use_emoji,
        'has_typo': has_typo,
        'dialect': dialect,
        'dialect_name': dialect_data['name'],
    }


def generate_review_params(persona):
    """توليد معايير التقييم (نمط + نجوم + وصف) للشخصية"""
    pattern = pick_pattern()
    rating = pick_rating()
    
    # المبتدئ ما يختار أنماط خبير
    if persona['expertise'] == 'مبتدئ' and pattern == 'expert_detail':
        pattern = 'ultra_short'
    
    # الخبير ما يختار ultra_short كثير
    if persona['expertise'] == 'خبير' and pattern == 'ultra_short':
        if random.random() < 0.7:
            pattern = random.choice(['scent_no_name', 'longevity', 'comparison', 'expert_detail'])
    
    pattern_desc = get_pattern_description(pattern)
    low_reason = get_low_rating_reason(rating) if rating <= 3 else ''
    
    return {
        'pattern': pattern,
        'pattern_desc': pattern_desc,
        'rating': rating,
        'low_reason': low_reason,
    }


# ═══════════════════════════════════════════════════════════
#  MASTER PROMPT — البرومبت المتقدم
# ═══════════════════════════════════════════════════════════

MASTER_PROMPT = """أنت {persona_name}، {persona_label}، عمرك {age}، من {city}.
## هويتك:
- لهجتك: {dialect_name}
- مزاجك: {mood}
- مستوى خبرتك: {expertise}
- أسلوبك: {writing_style}
## أمثلة طبيعية من لهجتك:
{dialect_examples}
## المطلوب:
اكتب تقييم واحد فقط كأنك فعلاً اشتريت هذا المنتج.
المنتج: {product_name}
النمط المطلوب: {pattern_description}
## قواعد صارمة:
- الطول: {min_words}-{max_words} كلمة فقط
- {opening_rule}
- {mention_rule}
- {emoji_rule}
- {typo_rule}
- التقييم: {rating} نجوم {rating_note}
## ممنوع منعاً باتاً:
- لا تكتب بفصحى أو لغة رسمية
- لا تبدأ بـ "لقد" أو "إن" أو "يعد" أو "هذا المنتج"
- لا تبدأ التقييم باسم المنتج إطلاقاً — ابدأ بإحساسك أو رأيك أو موقفك
- لا تضع نقاط bullet أو قوائم مرقمة
- لا تكرر هذه الصياغات السابقة:
{used_texts_block}
أرجع JSON فقط: {{"rating": {rating}, "text": "..."}}"""


# تنويع البدايات — كل تقييم يبدأ بأسلوب إنساني مختلف
OPENING_STYLES = [
    'ابدأ بانطباعك المباشر بدون مقدمة (مثل: صراحة.. / والله.. / بصراحة..)',
    'ابدأ بوصف الإحساس أو الموقف اللي عشته مع العطر',
    'ابدأ من نص القصة مباشرة كأنك تكمل كلام مع صاحبك',
    'ابدأ بذكر المناسبة أو الوقت اللي استخدمته فيه',
    'ابدأ برأيك في الريحة أو الثبات على طول',
    'ابدأ بتعجب أو ردة فعل عفوية',
    'ابدأ بمقارنة بسيطة أو توقع كان عندك قبل التجربة',
    'ابدأ بسبب شرائك أو وش خلاك تطلبه',
]

# طرق متنوعة لذكر اسم المنتج (لا تكون أول الكلام أبداً)
MENTION_STYLES = [
    'اذكر اسم المنتج مرة وحدة في منتصف الكلام بشكل عابر — لا تبدأ فيه أبداً',
    'مرر اسم المنتج داخل الجملة بطبيعية وخلِّ بدايتك إحساس أو رأي مو الاسم',
    'اذكر اسمه قرب النهاية كأنك تتذكره، وابدأ التقييم بانطباعك',
    'اذكر اسم المنتج بشكل عفوي وسط الجملة مو في أولها',
]


def build_master_prompt(persona, product_name, review_params, used_texts_block=''):
    """بناء البرومبت المتقدم"""
    from review_patterns import REVIEW_PATTERNS
    
    pattern_info = REVIEW_PATTERNS.get(review_params['pattern'], REVIEW_PATTERNS['ultra_short'])
    min_words, max_words = pattern_info['words']
    
    # قواعد خاصة — تنويع ذكر الاسم وموضعه (لا يكون أول الكلام)
    mention_rule = 'لا تذكر اسم المنتج' if not persona['mention_product'] else random.choice(MENTION_STYLES)
    # نمط "عن الريحة بدون ذكر الاسم" يفرض عدم ذكر الاسم بغض النظر عن تفضيل الشخصية
    if review_params['pattern'] == 'scent_no_name':
        mention_rule = 'لا تذكر اسم المنتج إطلاقاً — صف الريحة فقط'

    # تنويع البداية في كل تقييم
    opening_rule = random.choice(OPENING_STYLES)
    emoji_rule = 'بدون إيموجي نهائياً' if not persona['use_emoji'] else 'إيموجي واحد فقط'
    typo_rule = 'أضف خطأ إملائي طبيعي واحد' if persona['has_typo'] else 'بدون أخطاء إملائية'
    rating_note = '— اذكر سبب بسيط للنقص' if review_params['rating'] <= 3 else ''
    
    dialect_examples = get_dialect_examples(persona['dialect'], count=4)
    
    prompt = MASTER_PROMPT.format(
        persona_name=persona['name'],
        persona_label=persona['label'],
        age=persona['age'],
        city=persona['city'],
        dialect_name=persona['dialect_name'],
        mood=persona['mood'],
        expertise=persona['expertise'],
        writing_style=persona['writing_style'],
        dialect_examples=dialect_examples,
        product_name=product_name,
        pattern_description=review_params['pattern_desc'],
        min_words=min_words,
        max_words=max_words,
        opening_rule=opening_rule,
        mention_rule=mention_rule,
        emoji_rule=emoji_rule,
        typo_rule=typo_rule,
        rating=review_params['rating'],
        rating_note=rating_note,
        used_texts_block=used_texts_block if used_texts_block else '(لا يوجد سابق)',
    )
    
    return prompt


# ═══════════════════════════════════════════════════════════
#  Standalone Test
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 50)
    print('Personas Engine Test')
    print('=' * 50)
    
    for i in range(3):
        p = generate_persona()
        params = generate_review_params(p)
        print(f'\n--- Persona {i+1} ---')
        print(f'  Name: {p["name"]}')
        print(f'  City: {p["city"]} | Dialect: {p["dialect_name"]}')
        print(f'  Label: {p["label"]} | Age: {p["age"]}')
        print(f'  Mood: {p["mood"]} | Expertise: {p["expertise"]}')
        print(f'  Style: {p["writing_style"]}')
        print(f'  Mention: {p["mention_product"]} | Emoji: {p["use_emoji"]} | Typo: {p["has_typo"]}')
        print(f'  Pattern: {params["pattern"]} | Rating: {params["rating"]}')
    
    print(f'\n  Archetypes: {len(ARCHETYPES)}')
    print(f'  Cities in CITY_DATA: {len(CITY_DATA)}')
    print(f'  Test PASSED')
