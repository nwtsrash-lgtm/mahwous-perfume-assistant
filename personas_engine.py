# -*- coding: utf-8 -*-
"""
محرك الشخصيات العميقة — Deep Persona Engine V2
كل شخصية بـ 7 أبعاد: mood, expertise, writing_style, mention_product, use_emoji, has_typo, dialect
V2: ai_directive injection + product data + review banks + enhanced directives
"""
import random
import json
import string
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
    from review_patterns import (pick_pattern, pick_rating, get_pattern_description,
                                  get_low_rating_reason, get_ai_directive, REVIEW_PATTERNS)
    _HAS_PATTERNS_V2 = True
except ImportError:
    def pick_pattern(u=None): return 'ultra_short'
    def pick_rating(): return 5
    def get_pattern_description(p): return 'كلمة أو كلمتين فقط (1-3 كلمة)'
    def get_low_rating_reason(r): return ''
    def get_ai_directive(p): return ''
    REVIEW_PATTERNS = {}
    _HAS_PATTERNS_V2 = False

# import بنوك التقييمات كمرجع للأسلوب
try:
    from real_reviews_bank import pick_review_exemplars as bank_pick_exemplars
    _HAS_REVIEW_BANK = True
except ImportError:
    _HAS_REVIEW_BANK = False
    def bank_pick_exemplars(gender='male', pattern=None, count=3, used_texts=None): return []

try:
    from short_texts_bank import pick_short_text
    _HAS_SHORT_BANK = True
except ImportError:
    _HAS_SHORT_BANK = False

# ═══════════════════════════════════════════════════════════
#  تحميل بيانات المنتجات المُثرية (مكونات + عائلة عطرية)
# ═══════════════════════════════════════════════════════════

_CATALOG_INDEX = {}  # name → {scent_family, ingredients, category}


def _index_catalog(products):
    """بناء فهرس المنتجات (name → بيانات مُثرية) من قائمة منتجات."""
    _CATALOG_INDEX.clear()
    for _prod in products:
        _CATALOG_INDEX[_prod.get('name', '')] = {
            'scent_family': _prod.get('scent_family', ''),
            'ingredients': _prod.get('ingredients', ''),
            'category': _prod.get('category', ''),
            'brand': _prod.get('brand', ''),
        }
    return len(_CATALOG_INDEX)


def set_catalog(products):
    """حقن الكتالوج من مصدر خارجي (مثل app.py) لتفادي قراءة الملف مرتين."""
    return _index_catalog(products)


# تحميل افتراضي من الملف — يُستبدل لاحقاً عبر set_catalog() إن استدعاه app.py
try:
    _catalog_path = BASE_DIR / 'catalog.json'
    if _catalog_path.exists():
        with open(_catalog_path, 'r', encoding='utf-8') as _cf:
            _index_catalog(json.load(_cf))
except Exception:
    pass

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

MOODS = ['متحمس', 'هادئ', 'ناقد', 'عملي', 'عاطفي', 'فضولي', 'واثق', 'متردد']
MOOD_WEIGHTS = [26, 22, 9, 22, 8, 5, 5, 3]

EXPERTISE_LEVELS = ['مبتدئ', 'متوسط', 'خبير']
EXPERTISE_WEIGHTS = [40, 45, 15]

WRITING_STYLES = ['مختصر', 'عادي', 'مفصّل', 'عفوي متقطع']
WRITING_STYLE_WEIGHTS = [33, 42, 18, 7]

# ═══════════════════════════════════════════════════════════
#  ما يهم كل شخصية في العطر (يوجّه محتوى التقييم ليكون واقعياً)
# ═══════════════════════════════════════════════════════════

PERSONA_FOCUS = {
    'شاب_جامعي': 'يهمه الكومبلمنتات والسعر المناسب وإنه يلفت الانتباه',
    'رجل_أعمال': 'يهمه الهيبة والحضور والثبات طول يوم العمل والرقي',
    'خبير_عطور': 'يحلل النوتات (المقدمة/القلب/القاعدة) والثبات والفوحان والتطور',
    'أب_عائلة': 'يهمه إنه محترم ويعجب العائلة ويصلح هدية',
    'شاب_رياضي': 'يهمه الانتعاش والخفة والثبات بعد النادي',
    'كبير_سن': 'يهمه العود الأصيل والطيب وراحة النفس، كلامه قليل ومباشر',
    'موظف': 'يهمه الثبات طول الدوام والسعر المعقول وعدم الإزعاج',
    'بنت_عصرية': 'يهمها الترند والريحة الجذابة والكومبلمنتات والإحساس بالثقة',
    'أم_سعودية': 'يهمها المناسبات والعزايم وإنه يلبق ويدوم وما يصدّع',
    'عروس': 'يهمها الرومانسية وليلة العمر والثبات طول الحفلة والذكرى',
    'موظفة': 'يهمها الأناقة المهنية والثبات والريحة المحترمة بدون مبالغة',
    'خبيرة_تجميل': 'تقارن بالنيش والديزاينر وتتكلم عن البدائل والثبات والفوحان',
    'طالبة': 'يهمها السعر المناسب والريحة الكيوت الخفيفة المناسبة للجامعة',
    'جدة': 'يهمها البخور والعود وطيب البيت، كلامها قليل وفيه دعاء',
    'مقارن': 'يقارن الأسعار والجودة مع متاجر ثانية ويركز على القيمة',
    'هدايا_رجل': 'يهمه إنه يصلح هدية وردة فعل الشخص والتغليف',
    'هدايا_أنثى': 'يهمها إنه هدية مميزة وتغليف حلو وفرحة المُهدى له',
    'محب_تسوق': 'يجرب كثير ويقارن ويتكلم عن تجربة الشراء كاملة',
    'محبة_تسوق': 'تجرب كثير وتحب الاكتشافات وتقارن مع طلباتها السابقة',
    'مبتعث': 'يقارن بالعطور برّا والأسعار العالمية ويحب الفخامة بسعر أقل',
    'عسكري': 'يهمه الثبات في الحر والميدان والقوة وعدم الحاجة لإعادة الرش',
    'معلم': 'يهمه الريحة المحترمة الهادية المناسبة للمدرسة والسعر المعقول',
    'مهندس': 'عملي ودقيق، يتكلم بالأرقام (ساعات الثبات) والقيمة مقابل السعر',
    'طبيب': 'يهمه النظافة والاعتدال وعدم الإزعاج والريحة الراقية المحترمة',
    'متذوق_نيش': 'يحلل النوتات بعمق ويقارن بعطور النيش الأصلية ويتكلم عن المواد الخام والتطور',
    'عامل_مقتصد': 'يهمه السعر الرخيص والثبات وإنه يكفي مدة، كلامه بسيط ومباشر',
    'وجيه': 'يحب العود الفاخر والحضور والهيبة في المجالس، أسلوبه وقور',
    'بدوي': 'يحب البخور والعود والدخون والطيب الأصيل، تعبيره فطري صادق',
    'مؤثرة': 'تتكلم بأسلوب سوشيال، تذكر تجربتها وتوصي متابعاتها وتقارن',
    'معلمة': 'يهمها الريحة الهادية المناسبة للمدرسة والثبات والسعر',
    'طبيبة': 'يهمها الأناقة والنظافة والاعتدال وعدم الإزعاج في العيادة',
    'متذوقة_نيش': 'تحلل النوتات وتقارن بالنيش النسائي وتتكلم عن الفخامة والتطور',
    'ست_بيت': 'يهمها طيب البيت والمناسبات العائلية والسعر المناسب والثبات',
}

# ═══════════════════════════════════════════════════════════
#  بنك تقييمات عملاء حقيقية (نمط واقعي) — يُحقن كأمثلة تعليمية
#  لتعليم الـ AI أسلوب العملاء الفعلي: عفوية، نواقص، بدايات متنوعة
#  V2: يدمج البنك الخارجي (312+ تقييم) إن توفّر
# ═══════════════════════════════════════════════════════════

REAL_REVIEW_EXEMPLARS = [
    'صراحه ما توقعته بهالقوه، حطيته الصبح ولين رجعت من الدوام وريحته معي',
    'ريحته حلوه بس الثبات مدري ليه ضعيف عندي، ينفع للطلعات القصيره',
    'طلبته بعد ما شفته عند صاحبي، نفس الجوده والتوصيل كان يومين بس',
    'والله ما قصرتو، التغليف فخم والقاروره وصلت سليمه وريحته تجنن',
    'كنت متردد بسبب السعر بس بعد ما جربته عرفت ليش غالي، يستاهل',
    'عطر هادي ومحترم، يصلح للدوام ومايصدّع اللي حولك',
    'اخذته لزوجي وعجبه مره صار مايلبس غيره',
    'عجبني الفوحان بس ودي لو الحجم اكبر شوي',
    'الريحه نضيفه ومرتبه، شبيه عطر غالي جربته قبل بس بنص السعر',
    'ثاني مره اطلبه، اول واحد خلصته بسرعه من كثر ما استخدمته',
    'حطيته بالعيد والكل سألني وش عطرك، كومبلمنتات من كل جهه',
    'بصراحه عادي، مو سيئ بس ما حسيته يستاهل كل هالمدح',
    'وصل بسرعه ماشاء الله والريحه فخمه، بطلب منه كمان للهدايا',
    'ثقيل وفخم للمناسبات، مو يومي بس يستاهل تلبسه بالأعراس',
    'المقدمه حمضيات حلوه وبعد ساعه يطلع المسك والقاعده خشبيه، تطور جميل',
    'طلبته من ترشيح وحده وما خاب ظني، ريحه راقيه وتدوم',
    'حلو للسعر بس يبيله إعادة رش بعد ٤ ساعات، عادي بالنسبة لي',
    'ريحته دافيه وشتويه، حطيته بالبرد وكان مثالي',
    'جبته هديه لأبوي وفرح فيه، طيب وثابت وريحته تعبّق المجلس',
    'أول بخه قويه شوي بس تهدا وتصير ريحه نظيفه حلوه قريبه من الجسم',
]


def pick_real_exemplars(count=3, gender='male'):
    """اختيار أمثلة تقييمات حقيقية لحقنها في البرومبت كمرجع أسلوب.

    V2: يستخدم البنك الخارجي (312+ تقييم) إن توفّر، ثم يكمل من المحلي.
    """
    exemplars = []
    # أولاً: جلب من البنك الخارجي الغني
    if _HAS_REVIEW_BANK:
        try:
            bank_samples = bank_pick_exemplars(gender=gender, count=min(count, 2))
            exemplars.extend(bank_samples)
        except Exception:
            pass
    # ثانياً: إكمال من البنك المحلي
    remaining = count - len(exemplars)
    if remaining > 0:
        k = min(remaining, len(REAL_REVIEW_EXEMPLARS))
        exemplars.extend(random.sample(REAL_REVIEW_EXEMPLARS, k))
    return exemplars[:count]


def _get_product_data(product_name):
    """جلب بيانات المنتج المُثرية (مكونات + عائلة عطرية) من الكتالوج."""
    data = _CATALOG_INDEX.get(product_name, {})
    if not data:
        return ''
    parts = []
    if data.get('scent_family'):
        family_map = {
            'oud': 'عائلة العود', 'oriental': 'عائلة شرقية',
            'woody': 'عائلة خشبية', 'floral': 'عائلة زهرية',
            'fresh': 'عائلة منعشة', 'musk': 'عائلة المسك',
            'citrus': 'عائلة حمضية', 'sweet': 'عائلة حلوة',
            'gourmand': 'عائلة حلويات', 'leather': 'عائلة جلدية',
        }
        parts.append(f'العائلة: {family_map.get(data["scent_family"], data["scent_family"])}')
    if data.get('ingredients'):
        parts.append(f'المكونات: {data["ingredients"]}')
    if data.get('brand'):
        parts.append(f'البراند: {data["brand"]}')
    return '\n'.join(f'- {p}' for p in parts)

# ═══════════════════════════════════════════════════════════
#  SEO — حصان طروادة (مقارنة بعطور عالمية غالية) + كلمات بحث طويلة
#  يُحقن في البرومبت ليتصدّر التقييم نتائج البحث عن "بدائل" العطور
# ═══════════════════════════════════════════════════════════

# عطور عالمية غالية للمقارنة "لصالح متجرنا" (نفس الفخامة بسعر أقل)
SEO_DUPE_TARGETS = {
    'male': [
        'توم فورد أومبري ليذر', 'كريد أفنتوس', 'ديور سوفاج إليكسير', 'بكرات روج 540',
        'شانيل بلو دو شانيل', 'توم فورد نوار', 'جان بول غوتييه لو مال', 'فرزاتشي إيروس',
        'أرماني أكوا دي جيو', 'هوجو بوس بوتلد', 'ديور هوم انتنس', 'إنيشيو عود فور غريتنس',
        'كيليان أنجلز شير', 'لويس فيتون أومبري نوماد', 'مون بلان ليجند',
    ],
    'female': [
        'بكرات روج 540', 'لانكوم لا في إيه بيل', 'ديور جادور', 'شانيل كوكو مادموزيل',
        'إيف سان لوران بلاك أوبيوم', 'جورجيو أرماني سي', 'كارولينا هيريرا غود غيرل',
        'غوتشي بلوم', 'نارسيسو رودريغيز', 'توم فورد لوست شيري', 'إيف سان لوران مون باريس',
        'بربري هير', 'فالنتينو دونا', 'شانيل تشانس',
    ],
}

# جمل يبحث عنها الناس في جوجل — تُدمج حرفياً داخل التقييم (Long-Tail)
# ملاحظة: لا تُضف عبارات موسمية (شتوي/صيفي) هنا — الموسم يديره الذكاء الزمني
# لتفادي تناقض كلمة "شتوي" مع توجيه زمني صيفي.
LONG_TAIL_KEYWORDS = [
    'عطر فواح للدوام', 'عطر يثبت طول اليوم', 'عطر يلفت الانتباه',
    'عطر مناسب للمناسبات', 'عطر رسمي للعمل', 'عطر ثباته قوي',
    'بديل العطور الغالية', 'عطر هدية مميز', 'عطر مسائي فخم',
    'عطر فخم بسعر رخيص',
]

# الأنماط التي يكون فيها حقن "العطر العالمي الغالي" طبيعياً
_SEO_DUPE_PATTERNS = {'dupe_compare', 'comparison', 'value_focus'}


def build_seo_block(persona, pattern, max_words=12, dupe_prob=0.55, keyword_prob=0.35):
    """بناء كتلة توجيهات SEO (قد تكون فارغة).

    - حصان طروادة: في أنماط المقارنة يُحقن عطر عالمي غالٍ ليُقارَن لصالحنا.
    - كلمات طويلة: بنسبة احتمالية تُدمج عبارة بحث جوجل حرفياً (تتطلب طولاً كافياً).
    """
    lines = []
    gender = 'female' if persona.get('gender') == 'female' else 'male'

    if pattern in _SEO_DUPE_PATTERNS and random.random() < dupe_prob:
        target = random.choice(SEO_DUPE_TARGETS[gender])
        lines.append(
            f'- قارن العطر بـ "{target}" (عطر عالمي غالي) لكن لصالح عطرنا — '
            f'نفس الفخامة/الثبات بسعر أقل بكثير. اذكر اسم "{target}" حرفياً مرة واحدة بشكل طبيعي.'
        )

    # عبارات البحث الطويلة تحتاج مساحة — لا تُحقن في الأنماط القصيرة جداً
    if max_words >= 8 and random.random() < keyword_prob:
        kw = random.choice(LONG_TAIL_KEYWORDS)
        lines.append(f'- ادمج عبارة "{kw}" حرفياً داخل التقييم بشكل طبيعي وكأنها من كلامك.')

    if not lines:
        return ''
    return '## لمسة تسويقية (طبيعية وغير مبالغة):\n' + '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
#  الذكاء الزمني والموسمي — يربط التقييم بوقت السيرفر الحالي
#  (راتب / موسم / مناسبة وطنية / جمعة / رمضان إن توفّر hijri)
# ═══════════════════════════════════════════════════════════

import datetime as _dt

# محاولة كشف رمضان/العيد هجرياً إن توفّرت المكتبة (اختياري، بدون إلزام)
try:
    from hijri_converter import convert as _hijri_convert
    _HAS_HIJRI = True
except Exception:
    _HAS_HIJRI = False


def _temporal_signals(now):
    """قائمة الإشارات الزمنية الفعّالة الآن (الأقوى أولاً)."""
    signals = []
    m, d, wd = now.month, now.day, now.weekday()  # wd: الإثنين=0 ... الجمعة=4

    # مناسبة هجرية (رمضان/عيد) — أولوية قصوى إن توفّرت
    if _HAS_HIJRI:
        try:
            h = _hijri_convert.Gregorian(now.year, now.month, now.day).to_hijri()
            if h.month == 9:
                signals.append('إنك تستخدمه في رمضان (للتراويح/الجمعات/السحور) وريحته هادية تناسب الأجواء الروحانية')
            elif h.month == 10 and h.day <= 4:
                signals.append('إنك تعطرت فيه لصلاة العيد وصباح العيد')
            elif h.month == 12 and 8 <= h.day <= 13:
                signals.append('أجواء الحج وعشر ذي الحجة')
        except Exception:
            pass

    # مناسبات وطنية (ميلادية)
    if m == 9 and 20 <= d <= 25:
        signals.append('اليوم الوطني السعودي وأجواء الاحتفال الأخضر')
    elif m == 2 and 19 <= d <= 24:
        signals.append('يوم التأسيس وأجواء الفخر بالتراث')
    elif m == 8 and d >= 20:
        signals.append('قرب العودة للمدارس/الجامعات والاستعداد للدوام')

    # يوم الراتب (أواخر/أوائل الشهر)
    if d >= 26 or d <= 3:
        signals.append('إنك طلبته أول ما نزل الراتب وكنت منتظره')

    # صلاة الجمعة
    if wd == 4:
        signals.append('إنك تعطرت فيه لصلاة الجمعة')

    # الموسم المناخي السعودي
    if m in (6, 7, 8, 9):
        signals.append('أجواء الصيف الحار وإنه خفيف/منعش وثابت رغم الحر والعرق')
    elif m in (12, 1, 2):
        signals.append('أجواء الشتاء والبرد وإنه دافي وثقيل وثباته خيالي بالبرد')
    else:
        signals.append('أجواء الفصل المعتدل المتقلب — لا ثقيل يكتم ولا خفيف يطير')

    return signals


def build_temporal_block(prob=0.4, now=None):
    """توجيه زمني واحد طبيعي (قد يكون فارغاً) مرتبط بوقت السيرفر."""
    if random.random() >= prob:
        return ''
    now = now or _dt.datetime.now()
    signals = _temporal_signals(now)
    if not signals:
        return ''
    # ترجيح الإشارات الأولى (المناسبات/الراتب) قليلاً على الموسم
    weights = [max(1, len(signals) - i) for i in range(len(signals))]
    hint = random.choices(signals, weights=weights, k=1)[0]
    return f'## ربط زمني (اذكره بعفوية إن ناسب، لا تُقحمه):\n- اربط تجربتك بـ: {hint}.'

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
    # ── توسعة ──
    'متذوق_نيش': {'مبتدئ': 0, 'متوسط': 15, 'خبير': 85},
    'متذوقة_نيش': {'مبتدئ': 0, 'متوسط': 20, 'خبير': 80},
    'مؤثرة': {'مبتدئ': 5, 'متوسط': 45, 'خبير': 50},
    'طبيب': {'مبتدئ': 15, 'متوسط': 55, 'خبير': 30},
    'طبيبة': {'مبتدئ': 15, 'متوسط': 55, 'خبير': 30},
    'مهندس': {'مبتدئ': 20, 'متوسط': 55, 'خبير': 25},
    'مبتعث': {'مبتدئ': 25, 'متوسط': 55, 'خبير': 20},
    'وجيه': {'مبتدئ': 20, 'متوسط': 45, 'خبير': 35},
    'بدوي': {'مبتدئ': 30, 'متوسط': 45, 'خبير': 25},
    'عامل_مقتصد': {'مبتدئ': 70, 'متوسط': 28, 'خبير': 2},
    'ست_بيت': {'مبتدئ': 55, 'متوسط': 40, 'خبير': 5},
    'معلم': {'مبتدئ': 35, 'متوسط': 55, 'خبير': 10},
    'معلمة': {'مبتدئ': 35, 'متوسط': 55, 'خبير': 10},
    'عسكري': {'مبتدئ': 45, 'متوسط': 48, 'خبير': 7},
}


# ═══════════════════════════════════════════════════════════
#  المدن والعناوين (من app.py الأصلي)
# ═══════════════════════════════════════════════════════════

# بيانات العنوان الوطني السعودي — لكل حي اسمه الفعلي وشارعه وبادئة رمزه البريدي (٣ خانات).
# الرمز البريدي = البادئة + خانتين، فيتطابق مع المدينة والحي (لا رمز عشوائي خارج النطاق).
# ملاحظة: أسماء المدن هنا تطابق names.json حرفياً (مثل «جيزان») حتى لا يسقط أي عنوان للنمط الافتراضي.
CITY_DATA = {
    'الرياض': {'districts': [
        ('العليا', 'شارع العليا العام', '122'), ('النخيل', 'شارع الأمير محمد بن سعد', '123'),
        ('الملقا', 'طريق أنس بن مالك', '135'), ('الياسمين', 'شارع عبدالرحمن الداخل', '133'),
        ('حطين', 'شارع التخصصي', '135'), ('الورود', 'شارع الورود', '122'),
        ('السليمانية', 'شارع الأمير سلطان', '122'), ('الربوة', 'طريق الإمام الشافعي', '128'),
        ('المروج', 'طريق الملك فهد', '122'), ('الصحافة', 'طريق أبو بكر الصديق', '133'),
        ('النرجس', 'شارع محمد بن عبدالوهاب', '132')]},
    'جدة': {'districts': [
        ('الحمراء', 'شارع فلسطين', '233'), ('الروضة', 'شارع الأمير سلطان', '234'),
        ('الشاطئ', 'طريق الكورنيش', '236'), ('البوادي', 'شارع الأمير ماجد', '235'),
        ('الفيصلية', 'شارع الأمير فهد', '234'), ('النعيم', 'شارع حراء', '235'),
        ('المحمدية', 'شارع التحلية', '236'), ('السامر', 'طريق المدينة', '233')]},
    'الدمام': {'districts': [
        ('الشاطئ', 'طريق الكورنيش', '324'), ('الفيصلية', 'شارع الملك فيصل', '322'),
        ('الريان', 'شارع الريان', '324'), ('الجلوية', 'شارع الظهران', '324'),
        ('المريكبات', 'شارع الملك خالد', '324'), ('الأمانة', 'طريق الخليج', '324')]},
    'مكة المكرمة': {'districts': [
        ('العزيزية', 'طريق الملك عبدالعزيز', '242'), ('الشوقية', 'شارع الشوقية', '242'),
        ('النسيم', 'شارع النسيم', '242'), ('الزاهر', 'شارع الزاهر', '243'),
        ('الرصيفة', 'شارع إبراهيم الخليل', '242')]},
    'المدينة المنورة': {'districts': [
        ('العزيزية', 'طريق الملك عبدالله', '423'), ('قربان', 'شارع قربان', '423'),
        ('الحرة الشرقية', 'شارع سلطانة', '423'), ('الدفاع', 'شارع أبو بكر الصديق', '423'),
        ('المناخة', 'شارع المناخة', '421')]},
    'الخبر': {'districts': [
        ('الحزام الذهبي', 'شارع الأمير تركي', '344'), ('اليرموك', 'شارع اليرموك', '344'),
        ('العليا', 'شارع الأمير فيصل', '344'), ('الثقبة', 'شارع الملك سعود', '346'),
        ('الروابي', 'شارع الروابي', '343')]},
    'الطائف': {'districts': [
        ('الفيصلية', 'شارع الملك فيصل', '268'), ('الشهداء الشمالية', 'شارع الستين', '268'),
        ('شهار', 'طريق الرياض', '268'), ('الحوية', 'طريق الحوية', '269')]},
    'القطيف': {'districts': [
        ('القلعة', 'شارع الملك فيصل', '324'), ('الشويكة', 'شارع القدس', '324'),
        ('الناصرة', 'طريق الكورنيش', '324')]},
    'ينبع': {'districts': [
        ('الناصرية', 'شارع الملك عبدالعزيز', '464'), ('شرم ينبع', 'طريق الكورنيش', '464'),
        ('الصناعية', 'طريق الملك فهد', '465')]},
    'أبها': {'districts': [
        ('المنسك', 'شارع الملك فيصل', '625'), ('الوردتين', 'شارع الأمير سلطان', '625'),
        ('المفتاحة', 'شارع الفن', '625')]},
    'خميس مشيط': {'districts': [
        ('أم سرار', 'شارع الملك فهد', '619'), ('الراقي', 'شارع الأمير سلطان', '629')]},
    'تبوك': {'districts': [
        ('المروج', 'شارع الأمير فهد', '471'), ('الفيصلية', 'طريق الملك فهد', '471'),
        ('السلام', 'شارع السلام', '471')]},
    'بريدة': {'districts': [
        ('الصفراء', 'شارع الخبيب', '523'), ('الفايزية', 'طريق الملك عبدالعزيز', '522'),
        ('الإسكان', 'شارع الحرمين', '523')]},
    'حائل': {'districts': [
        ('المنتزه', 'شارع الملك فيصل', '551'), ('العزيزية', 'طريق الأمير سلطان', '551'),
        ('النقرة', 'شارع النقرة', '551')]},
    'الأحساء': {'districts': [
        ('المبرز', 'شارع الخليج', '364'), ('الهفوف', 'شارع الملك عبدالعزيز', '369')]},
    'نجران': {'districts': [
        ('الفهد', 'شارع الملك فهد', '664'), ('الفيصلية', 'شارع الأمير فيصل', '664')]},
    'جيزان': {'districts': [
        ('الروضة', 'شارع الأمير سلطان', '825'), ('الشاطئ', 'طريق الكورنيش', '825'),
        ('المطار', 'طريق الملك فهد', '827')]},
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


def _short_code():
    """الرمز الوطني المختصر: ٤ أحرف لاتينية كبيرة + ٤ أرقام (مثل RAHA2929)."""
    letters = ''.join(random.choice(string.ascii_uppercase) for _ in range(4))
    digits = ''.join(str(random.randint(0, 9)) for _ in range(4))
    return letters + digits


def _make_address(city_name):
    """توليد عنوان وطني سعودي صحيح ومتسق.

    - الرمز البريدي يطابق المدينة والحي (بادئة الحي + خانتين)، لا رقم عشوائي خارج النطاق.
    - رقم المبنى والرقم الإضافي بصيغة ٤ خانات كما في العنوان الوطني الفعلي.
    - يضيف الرمز المختصر (short_code) المعتمد في الشحن السعودي.
    """
    cdata = CITY_DATA.get(city_name)
    if not cdata:  # مدينة خارج القائمة — بادئة رياض الافتراضية بدل رمز عشوائي
        cdata = {'districts': [('المركز', 'الشارع العام', '114')]}
    dist, street, postal_prefix = random.choice(cdata['districts'])
    building = str(random.randint(2000, 9999))
    postal = f'{postal_prefix}{random.randint(0, 99):02d}'
    extra = str(random.randint(2000, 9999))
    return {
        'building': building, 'street': street, 'district': dist,
        'city': city_name, 'postal': postal, 'extra': extra,
        'short_code': _short_code(),
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
#  MASTER PROMPT V2 — البرومبت المتقدم مع التوجيه الاستراتيجي
#  التغييرات عن V1:
#  1. حقن ai_directive (التوجيه الاستراتيجي للنمط)
#  2. حقن بيانات المنتج (مكونات + عائلة عطرية)
#  3. حقن نماذج من البنوك كأمثلة أسلوبية
#  4. الـ AI يتلقى "مهمة" لا مجرد وصف نمط
# ═══════════════════════════════════════════════════════════

MASTER_PROMPT = """أنت {persona_name}، {persona_label}، عمرك {age}، من {city}.
## هويتك:
- لهجتك: {dialect_name}
- مزاجك: {mood}
- مستوى خبرتك: {expertise}
- أسلوبك: {writing_style}
- اللي يهمك في العطر: {persona_focus}
## أمثلة طبيعية من لهجتك:
{dialect_examples}
## هكذا يكتب عملاء حقيقيون (احتذِ الأسلوب لا الكلمات — عفوية، نواقص بسيطة، بدايات متنوعة):
{real_examples}
## بيانات المنتج (استخدمها لتوجيه إحساسك، لا تسرد المكونات):
المنتج: {product_name}
{product_data}
## مهمتك الاستراتيجية:
{ai_directive}
## النمط: {pattern_description}
{directives_block}
## قواعد صارمة:
- الطول: {min_words}-{max_words} كلمة فقط — كل كلمة زيادة تُضعف التقييم
- {opening_rule}
- {mention_rule}
- {typo_rule}
- التقييم: {rating} نجوم {rating_note}
- اكتب بتدفّق طبيعي بدون أي علامات ترقيم نهائياً: بلا فواصل «،» وبلا نقاط «.» وبلا «؛ : ؟ !» وبلا إيموجي أو رموز — كأنك تكتب رسالة سريعة لصاحبك
- النبرة إيجابية أو محايدة تماماً — حتى لو ذكرت ملاحظة بسيطة اجعلها لطيفة لا تنفّر القارئ من الشراء
## ممنوع منعاً باتاً:
- ممنوع أي علامة ترقيم أو رمز أو إيموجي إطلاقاً (لا «،» لا «.» لا «!» لا «؟» لا «…»)
- ممنوع أي كلمة سلبية تنفّر من المنتج أو المتجر (لا «سيء» لا «ما عجبني» لا «رديء» لا «ندمت»)
- لا تكتب بفصحى أو لغة رسمية — لهجة سعودية عفوية صادقة
- لا تبدأ بـ "لقد" أو "إن" أو "يعد" أو "هذا المنتج"
- لا تبدأ التقييم باسم المنتج إطلاقاً — ابدأ بإحساسك أو رأيك أو موقفك
- لا تسرد المكونات العطرية بالاسم — عبّر عن إحساسك بها (مثلاً: بدل "يحتوي ليمون" قُل "انتعاش")
- لا تضع نقاط bullet أو قوائم مرقمة
- لا تكرر هذه الصياغات السابقة (اكتب شيئاً مختلفاً تماماً):
{used_texts_block}
## صيغة الإخراج:
يجب أن يكون الرد عبارة عن كائن JSON واحد فقط، لا تكتب أي حرف أو مقدمة أو شرح خارج أقواس الـ JSON.
- text: نص التقييم (بلا أي ترقيم أو رموز)
- rating: عدد النجوم ({rating})
- is_verified_purchase: true دائماً
أرجع JSON فقط بهذا الشكل: {{"rating": {rating}, "text": "...", "is_verified_purchase": true}}"""


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


def build_master_prompt(persona, product_name, review_params, used_texts_block='', extra_block=''):
    """بناء البرومبت المتقدم V2.

    التطويرات عن V1:
    - ai_directive: التوجيه الاستراتيجي من النمط (المهمة النفسية/التسويقية)
    - product_data: مكونات + عائلة عطرية من الكتالوج المُثرى
    - review bank exemplars: نماذج من البنك الخارجي (312+ تقييم)
    - extra_block: توجيهات إضافية يبنيها المستدعي (مثل Cross-Sell)
    """
    # --- جلب بيانات النمط ---
    pattern_info = REVIEW_PATTERNS.get(review_params['pattern'],
                                       REVIEW_PATTERNS.get('ultra_short', {'words': (1, 3)}))
    min_words, max_words = pattern_info.get('words', (1, 3))

    # --- التوجيه الاستراتيجي من النمط (المفتاح الجديد!) ---
    ai_directive = get_ai_directive(review_params['pattern'])
    if not ai_directive:
        ai_directive = f'اكتب تقييماً عفوياً وصادقاً عن تجربتك مع هذا العطر ({review_params.get("pattern_desc", "")})'

    # --- بيانات المنتج المُثرية ---
    product_data = _get_product_data(product_name)
    if not product_data:
        product_data = '(لا تتوفر بيانات إضافية — اكتب عن إحساسك العام)'

    # --- قواعد خاصة — تنويع ذكر الاسم وموضعه ---
    mention_rule = 'لا تذكر اسم المنتج' if not persona['mention_product'] else random.choice(MENTION_STYLES)
    if review_params['pattern'] == 'scent_no_name':
        mention_rule = 'لا تذكر اسم المنتج إطلاقاً — صف الريحة فقط'

    # --- تنويع البداية ---
    opening_rule = random.choice(OPENING_STYLES)

    # --- وضع القِصَر الصارم للأنماط القصيرة جداً (≤3 كلمات) ---
    # بدون ذكر الاسم (يوفّر كلمات) + تعليمة طول قاطعة لمنع الإطناب
    if max_words <= 3:
        mention_rule = 'لا تذكر اسم المنتج إطلاقاً'
        opening_rule = ('اكتب كلمة أو كلمتين فقط (٣ كلمات كحد أقصى مطلق) تعبّر عن انطباعك — '
                        'مثل: ممتاز / يجنن / فخم وثابت / خيال والله. ممنوع جملة كاملة أو شرح.')
    emoji_rule = 'بدون إيموجي نهائياً' if not persona['use_emoji'] else 'إيموجي واحد فقط'
    typo_rule = 'أضف خطأ إملائي طبيعي واحد' if persona['has_typo'] else 'بدون أخطاء إملائية'
    rating_note = '— اذكر ملاحظة بسيطة لطيفة بصيغة إيجابية لا تنفّر' if review_params['rating'] <= 3 else ''

    dialect_examples = get_dialect_examples(persona['dialect'], count=4)

    # --- تركيز الشخصية ---
    persona_focus = PERSONA_FOCUS.get(persona.get('archId', ''), 'يهمك تكتب رأيك الصادق بعفوية')

    # --- أمثلة عملاء حقيقية (V2: من البنك الخارجي + المحلي) ---
    # للأنماط القصيرة جداً: نحقن أمثلة قصيرة (2-4 كلمات) ليتعلّم النموذج القِصَر
    # بدل الأمثلة الطويلة التي تدفعه للإطناب.
    gender = persona.get('gender', 'male')
    if max_words <= 5 and _HAS_SHORT_BANK:
        fam = _CATALOG_INDEX.get(product_name, {}).get('scent_family', '')
        shorts = []
        for _ in range(8):
            t = pick_short_text(fam, gender=gender)
            if t and t not in shorts:
                shorts.append(t)
            if len(shorts) >= 4:
                break
        real_examples = '\n'.join(f'- {ex}' for ex in shorts) if shorts \
            else '\n'.join(f'- {ex}' for ex in pick_real_exemplars(3, gender=gender))
    else:
        real_examples = '\n'.join(f'- {ex}' for ex in pick_real_exemplars(3, gender=gender))

    # --- كتلة التوجيهات الموحّدة ---
    # الأنماط القصيرة (≤6 كلمات) لا تتحمّل توجيهات إضافية تطيلها (SEO/زمني)
    seo_block = build_seo_block(persona, review_params['pattern'], max_words=max_words)
    temporal_block = build_temporal_block() if max_words >= 6 else ''
    
    # extra_block يحتوي على التنبيهات السياقية الهامة جداً (مكياج/هدايا) فلا يجوز حذفه!
    directives_block = '\n'.join(b for b in (seo_block, temporal_block, extra_block) if b)

    prompt = MASTER_PROMPT.format(
        persona_name=persona['name'],
        persona_label=persona['label'],
        age=persona['age'],
        city=persona['city'],
        dialect_name=persona['dialect_name'],
        mood=persona['mood'],
        expertise=persona['expertise'],
        writing_style=persona['writing_style'],
        persona_focus=persona_focus,
        dialect_examples=dialect_examples,
        real_examples=real_examples,
        product_name=product_name,
        product_data=product_data,
        ai_directive=ai_directive,
        pattern_description=review_params['pattern_desc'],
        directives_block=directives_block,
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
