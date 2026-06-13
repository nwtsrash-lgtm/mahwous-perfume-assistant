# -*- coding: utf-8 -*-
"""
مولّد المحادثات — Thread Generator
توليد تقييم رئيسي + ردود من عملاء آخرين لبناء Social Proof
الوحدة تبني البرومبتات والبيانات فقط — استدعاء الـ AI يصير في app.py
"""
import sys
import random
import json
from pathlib import Path

# ضمان ترميز UTF-8 للطباعة (يمنع تعطّل الإيموجي على كونسول Windows cp1256)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).parent

# ═══════════════════════════════════════════════════════════
#  استيراد من الوحدات الموجودة
# ═══════════════════════════════════════════════════════════

try:
    from personas_engine import generate_persona
    HAS_PERSONAS = True
except ImportError:
    HAS_PERSONAS = False

# ═══════════════════════════════════════════════════════════
#  أنواع المحادثات (Threads)
# ═══════════════════════════════════════════════════════════

THREAD_TYPES = {
    'question_answer': {
        'weight': 35,
        'desc': 'عميل يسأل وصاحب التقييم يجاوب',
        'min_replies': 2,
        'max_replies': 3,
    },
    'confirmation': {
        'weight': 30,
        'desc': 'عميل ثاني يؤكد كلام الأول',
        'min_replies': 1,
        'max_replies': 2,
    },
    'recommendation_chain': {
        'weight': 20,
        'desc': 'عميل يوصي بناءً على التقييم',
        'min_replies': 1,
        'max_replies': 2,
    },
    'experience_sharing': {
        'weight': 10,
        'desc': 'عميل يشارك تجربته المشابهة',
        'min_replies': 1,
        'max_replies': 2,
    },
    'thanks_chain': {
        'weight': 5,
        'desc': 'عميل يشكر صاحب التقييم على المعلومة',
        'min_replies': 1,
        'max_replies': 1,
    },
}

# ═══════════════════════════════════════════════════════════
#  مواضيع الأسئلة الشائعة (بلهجة سعودية)
# ═══════════════════════════════════════════════════════════

QUESTION_TOPICS = [
    {'topic': 'الثبات بالحر', 'context': 'يبي يعرف إذا العطر يثبت بالحرارة العالية'},
    {'topic': 'الفوحان بعد ساعتين', 'context': 'يبي يعرف إذا العطر يفوح بعد فترة'},
    {'topic': 'يصلح للدوام؟', 'context': 'يبي يعرف إذا مناسب لبيئة العمل'},
    {'topic': 'الحجم كبير ولا صغير؟', 'context': 'يبي يعرف حجم القارورة'},
    {'topic': 'يشبه عطر معين؟', 'context': 'يبي يعرف إذا يشبه عطر ثاني مشهور'},
    {'topic': 'يصلح هدية؟', 'context': 'يبي يعرف إذا يناسب كهدية'},
    {'topic': 'التوصيل كم أخذ؟', 'context': 'يبي يعرف مدة الشحن'},
    {'topic': 'يناسب الشتاء؟', 'context': 'يبي يعرف إذا يناسب الأجواء الباردة'},
    {'topic': 'يناسب الصيف؟', 'context': 'يبي يعرف إذا يناسب الأجواء الحارة'},
    {'topic': 'ريحته نسائية ولا مشتركة؟', 'context': 'يبي يعرف إذا يناسب الجنسين'},
    {'topic': 'كم بخة تكفي؟', 'context': 'يبي يعرف عدد البخات المناسبة'},
    {'topic': 'يناسب المناسبات؟', 'context': 'يبي يعرف إذا يناسب الأعراس والعزايم'},
    {'topic': 'التغليف حلو؟', 'context': 'يبي يعرف جودة التغليف'},
    {'topic': 'يتفاعل مع البشرة؟', 'context': 'يبي يعرف كيف يتغير على الجلد'},
    {'topic': 'فيه عرض عليه؟', 'context': 'يبي يعرف إذا فيه تخفيض'},
]

# ═══════════════════════════════════════════════════════════
#  عبارات طبيعية للردود (تُحقن في البرومبتات كأمثلة)
# ═══════════════════════════════════════════════════════════

REPLY_EXEMPLARS = {
    'question': [
        'هو يثبت بالحر؟',
        'كم بخة تحطون؟',
        'يصلح للدوام ولا ثقيل؟',
        'التوصيل كم يوم أخذ معك؟',
        'حجمه كبير؟',
        'يشبه عطر معين؟',
        'يصلح هدية للوالد؟',
        'ريحته نسائية ولا مشتركة؟',
    ],
    'answer': [
        'إي والله يثبت، أنا جربته بالصيف ما تغير',
        'بخّتين على الرقبة تكفيك طول اليوم',
        'للدوام ممتاز، خفيف وما يزعج أحد',
        'يومين بس والله، سريعين ماشاء الله',
        'الحجم كويس، ١٠٠ مل يكفيك شهرين',
        'لا مو شبيه، هذا له ستايل خاص فيه',
        'أكيد يصلح، أنا جبته هدية وفرحوا فيه',
    ],
    'confirmation': [
        'نفس الشي عندي، ريحته تجنن',
        'أنا بعد جربته وكلامك صح ١٠٠٪',
        'والله صدقت، أنا أخذته وما ندمت',
        'نفس تجربتي بالضبط 👍',
        'أؤكد كلامك، عطر ما يتفوت',
        'صح كلامك، أنا الثالث مره أطلبه',
    ],
    'recommendation': [
        'بسبب تقييمك طلبته ووصلني اليوم 🔥',
        'حماسك خلاني أطلبه، يا رب يكون زي ما قلت',
        'طلبته على كلامك وفعلاً ما خاب ظني',
        'أنت السبب إني طلبته 😂👍',
        'شاكر لك، طلبته وجاني اليوم',
    ],
    'experience': [
        'أنا عندي وأستخدمه للمناسبات، فخم',
        'جربته من فترة وللحين معي، يستاهل',
        'أنا أستخدمه للدوام وريحته تدوم لين الليل',
        'عندي منه ومن غيره بس هذا المفضل',
    ],
    'thanks': [
        'يعطيك العافية على المعلومة 🙏',
        'شكراً على التقييم، ساعدتني أقرر',
        'الله يجزاك خير، كنت محتار وقررت أطلبه',
        'مشكور، تقييمك فاد',
    ],
}

# ═══════════════════════════════════════════════════════════
#  بناء شخصية بديلة (إذا ما كان personas_engine متاح)
# ═══════════════════════════════════════════════════════════

_FALLBACK_NAMES_M = ['أبو محمد', 'خالد', 'عبدالله', 'فهد', 'سعود', 'تركي', 'ناصر', 'بندر']
_FALLBACK_NAMES_F = ['أم نوره', 'نوف', 'سارة', 'ريم', 'لطيفة', 'منيرة', 'دلال', 'هيا']
_FALLBACK_CITIES = ['الرياض', 'جدة', 'الدمام', 'مكة', 'المدينة', 'أبها', 'الطائف', 'بريدة']


def _fallback_persona():
    """شخصية بسيطة بديلة بدون personas_engine"""
    gender = random.choice(['male', 'female'])
    if gender == 'male':
        name = random.choice(_FALLBACK_NAMES_M)
    else:
        name = random.choice(_FALLBACK_NAMES_F)

    return {
        'name': name,
        'age': random.randint(20, 55),
        'city': random.choice(_FALLBACK_CITIES),
        'gender': gender,
        'label': 'عميل',
        'emoji': '👤',
        'archId': 'عميل_عام',
        'mood': random.choice(['متحمس', 'هادئ', 'عملي']),
        'expertise': random.choice(['مبتدئ', 'متوسط']),
        'writing_style': random.choice(['مختصر', 'عادي']),
        'dialect': 'najdi',
        'dialect_name': 'نجدية',
        'mention_product': False,
        'use_emoji': random.random() < 0.15,
        'has_typo': False,
    }


def _get_persona():
    """الحصول على شخصية من المحرك أو البديل"""
    if HAS_PERSONAS:
        return generate_persona()
    return _fallback_persona()


# ═══════════════════════════════════════════════════════════
#  بناء البرومبتات لكل نوع رد
# ═══════════════════════════════════════════════════════════

def _pick_exemplars(category, count=2):
    """اختيار أمثلة عشوائية من بنك الردود"""
    bank = REPLY_EXEMPLARS.get(category, [])
    if not bank:
        return ''
    chosen = random.sample(bank, min(count, len(bank)))
    return '\n'.join(f'- {ex}' for ex in chosen)


def _build_question_prompt(reply_persona, main_review_text, topic_data, product_name):
    """
    بناء برومبت لسؤال من عميل آخر.
    السؤال يكون قصير (3-8 كلمات) بلهجة سعودية عفوية.
    """
    topic = topic_data['topic']
    context = topic_data['context']
    exemplars = _pick_exemplars('question', 3)

    prompt = f"""أنت {reply_persona['name']}، {reply_persona['label']}، من {reply_persona['city']}.
قرأت تقييم عميل آخر عن منتج "{product_name}" وهذا نص التقييم:
"{main_review_text}"

المطلوب: اكتب سؤال واحد قصير (3-8 كلمات فقط) بلهجة سعودية عفوية.
الموضوع اللي تبي تسأل عنه: {topic}
({context})

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- سؤال واحد فقط، قصير وعفوي
- بلهجة سعودية طبيعية (مو فصحى)
- لا تذكر اسم المنتج
- لا تبدأ بـ "السلام عليكم" أو "مرحبا"
- لا تكتب أكثر من 8 كلمات
- لا تستخدم علامات تعجب كثيرة

أجب بـ JSON فقط:
{{"text": "السؤال هنا"}}"""

    return prompt


def _build_answer_prompt(main_review_text, topic_data, product_name, original_persona_name=None):
    """
    بناء برومبت لجواب من صاحب التقييم الأصلي.
    الجواب يكون واثق وقصير (5-12 كلمة).
    """
    topic = topic_data['topic']
    exemplars = _pick_exemplars('answer', 3)
    answerer = original_persona_name or 'صاحب التقييم'

    prompt = f"""أنت {answerer}، صاحب التقييم الأصلي عن منتج "{product_name}".
تقييمك كان:
"{main_review_text}"

عميل سألك عن: {topic}

المطلوب: اكتب رد قصير واثق (5-12 كلمة) بلهجة سعودية طبيعية.

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- رد واحد فقط، واثق وطبيعي
- بلهجة سعودية (مو فصحى)
- جاوب من تجربتك الشخصية
- لا تبدأ بـ "السلام عليكم" أو "مرحبا"
- بين 5 و 12 كلمة
- ممكن تبدأ بـ "إي والله" أو "أكيد" أو "هو" أو مباشرة

أجب بـ JSON فقط:
{{"text": "الجواب هنا"}}"""

    return prompt


def _build_confirmation_prompt(reply_persona, main_review_text, product_name):
    """
    بناء برومبت لتأكيد من عميل آخر.
    يقول إنه جرب نفس المنتج ويوافق (3-8 كلمات).
    """
    exemplars = _pick_exemplars('confirmation', 3)

    prompt = f"""أنت {reply_persona['name']}، {reply_persona['label']}، من {reply_persona['city']}.
قرأت تقييم عميل آخر عن منتج "{product_name}" وهذا نص التقييم:
"{main_review_text}"

المطلوب: اكتب رد قصير (3-8 كلمات) تؤكد فيه كلام صاحب التقييم.
أنت بعد جربت نفس المنتج وتوافقه.

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- رد واحد قصير، 3-8 كلمات فقط
- بلهجة سعودية طبيعية
- لا تذكر اسم المنتج بالضرورة
- لا تبدأ بـ "السلام عليكم"
- عبّر عن موافقتك بشكل عفوي
- ممكن تستخدم إيموجي واحد فقط (اختياري)

أجب بـ JSON فقط:
{{"text": "الرد هنا"}}"""

    return prompt


def _build_recommendation_prompt(reply_persona, main_review_text, product_name):
    """
    بناء برومبت لتوصية بناءً على التقييم.
    عميل يقول إنه طلب المنتج بسبب التقييم (5-10 كلمات).
    """
    exemplars = _pick_exemplars('recommendation', 3)

    prompt = f"""أنت {reply_persona['name']}، {reply_persona['label']}، من {reply_persona['city']}.
قرأت تقييم عميل آخر عن منتج "{product_name}" وهذا نص التقييم:
"{main_review_text}"

المطلوب: اكتب رد قصير (5-10 كلمات) تقول فيه إنك طلبت المنتج بسبب هالتقييم.

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- رد واحد قصير، 5-10 كلمات فقط
- بلهجة سعودية طبيعية
- وضّح إن التقييم هو اللي خلاك تطلب
- لا تبدأ بـ "السلام عليكم"
- كن صادق وعفوي
- ممكن إيموجي واحد (اختياري)

أجب بـ JSON فقط:
{{"text": "الرد هنا"}}"""

    return prompt


def _build_experience_prompt(reply_persona, main_review_text, product_name):
    """
    بناء برومبت لمشاركة تجربة مشابهة.
    عميل يشارك تجربته الشخصية مع نفس المنتج (5-12 كلمة).
    """
    exemplars = _pick_exemplars('experience', 3)

    prompt = f"""أنت {reply_persona['name']}، {reply_persona['label']}، من {reply_persona['city']}.
قرأت تقييم عميل آخر عن منتج "{product_name}" وهذا نص التقييم:
"{main_review_text}"

المطلوب: اكتب رد قصير (5-12 كلمة) تشارك فيه تجربتك الشخصية مع نفس المنتج.
أنت بعد عندك المنتج وتبي تضيف شي من تجربتك.

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- رد واحد قصير، 5-12 كلمة فقط
- بلهجة سعودية طبيعية
- تكلم من تجربتك الشخصية
- لا تبدأ بـ "السلام عليكم"
- ممكن تضيف معلومة جديدة (مثلاً: الثبات، المناسبة، إلخ)

أجب بـ JSON فقط:
{{"text": "الرد هنا"}}"""

    return prompt


def _build_thanks_prompt(reply_persona, main_review_text, product_name):
    """
    بناء برومبت لشكر صاحب التقييم.
    عميل يشكره على المعلومة (3-8 كلمات).
    """
    exemplars = _pick_exemplars('thanks', 3)

    prompt = f"""أنت {reply_persona['name']}، {reply_persona['label']}، من {reply_persona['city']}.
قرأت تقييم مفيد عن منتج "{product_name}" وهذا نص التقييم:
"{main_review_text}"

المطلوب: اكتب رد شكر قصير (3-8 كلمات) لصاحب التقييم على المعلومة.

## أمثلة طبيعية (احتذِ الأسلوب لا الكلمات):
{exemplars}

## قواعد صارمة:
- رد شكر قصير، 3-8 كلمات فقط
- بلهجة سعودية طبيعية
- لا تبدأ بـ "السلام عليكم"
- كن صادق ومختصر
- ممكن إيموجي واحد (اختياري)

أجب بـ JSON فقط:
{{"text": "الرد هنا"}}"""

    return prompt


# ═══════════════════════════════════════════════════════════
#  الدالة الرئيسية: بناء بيانات المحادثة
# ═══════════════════════════════════════════════════════════

def pick_thread_type():
    """اختيار نوع محادثة عشوائي بناءً على الأوزان"""
    types = list(THREAD_TYPES.keys())
    weights = [THREAD_TYPES[t]['weight'] for t in types]
    return random.choices(types, weights=weights, k=1)[0]


def build_thread_prompt(main_review_text, thread_type, persona, product_name, topic_data=None):
    """
    بناء البرومبت المناسب حسب نوع المحادثة والشخصية.

    Args:
        main_review_text: نص التقييم الرئيسي
        thread_type: نوع المحادثة (question_answer, confirmation, إلخ)
        persona: بيانات شخصية صاحب الرد
        product_name: اسم المنتج
        topic_data: موضوع السؤال (مطلوب لـ question_answer)

    Returns:
        str: البرومبت الجاهز للإرسال للـ AI
    """
    if thread_type == 'question_answer':
        if topic_data is None:
            topic_data = random.choice(QUESTION_TOPICS)
        return _build_question_prompt(persona, main_review_text, topic_data, product_name)
    elif thread_type == 'confirmation':
        return _build_confirmation_prompt(persona, main_review_text, product_name)
    elif thread_type == 'recommendation_chain':
        return _build_recommendation_prompt(persona, main_review_text, product_name)
    elif thread_type == 'experience_sharing':
        return _build_experience_prompt(persona, main_review_text, product_name)
    elif thread_type == 'thanks_chain':
        return _build_thanks_prompt(persona, main_review_text, product_name)
    else:
        # fallback to confirmation
        return _build_confirmation_prompt(persona, main_review_text, product_name)


def generate_thread_data(product_name, main_review_text, reply_count=None,
                         original_persona_name=None):
    """
    توليد بيانات المحادثة (البرومبتات فقط، بدون استدعاء AI).

    Args:
        product_name: اسم المنتج
        main_review_text: نص التقييم الرئيسي
        reply_count: عدد الردود (إذا None يتم اختياره تلقائياً)
        original_persona_name: اسم صاحب التقييم الأصلي (للأجوبة)

    Returns:
        dict: {
            'thread_type': نوع المحادثة,
            'thread_desc': وصف النوع,
            'topic': موضوع السؤال (لـ question_answer فقط),
            'replies': [
                {
                    'persona': بيانات الشخصية,
                    'prompt': البرومبت الجاهز,
                    'type': نوع المحادثة,
                    'role': 'questioner' | 'answerer' | 'confirmer' | 'recommender' | ...,
                    'is_answer': هل هو جواب من صاحب التقييم الأصلي,
                },
                ...
            ],
        }
    """
    thread_type = pick_thread_type()
    type_info = THREAD_TYPES[thread_type]

    # تحديد عدد الردود
    if reply_count is None:
        reply_count = random.randint(type_info['min_replies'], type_info['max_replies'])
    reply_count = max(1, min(reply_count, 4))  # حد أقصى 4 ردود

    # اختيار موضوع السؤال (لـ question_answer)
    topic_data = None
    if thread_type == 'question_answer':
        topic_data = random.choice(QUESTION_TOPICS)
        # question_answer يحتاج زوج على الأقل (سؤال + جواب)
        reply_count = max(2, reply_count)

    replies = []

    for i in range(reply_count):
        # شخصية مختلفة لكل رد
        reply_persona = _get_persona()

        if thread_type == 'question_answer':
            if i == 0:
                # الرد الأول: سؤال من عميل آخر
                prompt = _build_question_prompt(
                    reply_persona, main_review_text, topic_data, product_name
                )
                role = 'questioner'
                is_answer = False
            else:
                # الردود التالية: جواب من صاحب التقييم الأصلي
                prompt = _build_answer_prompt(
                    main_review_text, topic_data, product_name,
                    original_persona_name
                )
                role = 'answerer'
                is_answer = True
        elif thread_type == 'confirmation':
            prompt = _build_confirmation_prompt(
                reply_persona, main_review_text, product_name
            )
            role = 'confirmer'
            is_answer = False
        elif thread_type == 'recommendation_chain':
            prompt = _build_recommendation_prompt(
                reply_persona, main_review_text, product_name
            )
            role = 'recommender'
            is_answer = False
        elif thread_type == 'experience_sharing':
            prompt = _build_experience_prompt(
                reply_persona, main_review_text, product_name
            )
            role = 'sharer'
            is_answer = False
        elif thread_type == 'thanks_chain':
            prompt = _build_thanks_prompt(
                reply_persona, main_review_text, product_name
            )
            role = 'thanker'
            is_answer = False
        else:
            prompt = _build_confirmation_prompt(
                reply_persona, main_review_text, product_name
            )
            role = 'confirmer'
            is_answer = False

        replies.append({
            'persona': reply_persona,
            'prompt': prompt,
            'type': thread_type,
            'role': role,
            'is_answer': is_answer,
        })

    return {
        'thread_type': thread_type,
        'thread_desc': type_info['desc'],
        'topic': topic_data,
        'replies': replies,
    }


# ═══════════════════════════════════════════════════════════
#  دوال مساعدة
# ═══════════════════════════════════════════════════════════

def get_thread_type_info(thread_type):
    """معلومات نوع محادثة معين"""
    return THREAD_TYPES.get(thread_type, THREAD_TYPES['confirmation'])


def get_all_thread_types():
    """قائمة بكل أنواع المحادثات مع أوزانها"""
    total_weight = sum(t['weight'] for t in THREAD_TYPES.values())
    result = []
    for name, info in THREAD_TYPES.items():
        pct = round(info['weight'] / total_weight * 100, 1)
        result.append({
            'name': name,
            'desc': info['desc'],
            'weight': info['weight'],
            'percentage': pct,
        })
    return result


def parse_ai_reply(raw_text):
    """
    تحليل رد الـ AI واستخراج النص.
    يتعامل مع JSON أو نص عادي.

    Args:
        raw_text: الرد الخام من الـ AI

    Returns:
        str: النص المستخرج
    """
    if not raw_text:
        return ''

    raw_text = raw_text.strip()

    # محاولة تحليل JSON
    # إزالة markdown code blocks إذا موجودة
    if raw_text.startswith('```'):
        lines = raw_text.split('\n')
        # إزالة أول وآخر سطر (```)
        lines = [l for l in lines if not l.strip().startswith('```')]
        raw_text = '\n'.join(lines).strip()

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and 'text' in data:
            return data['text'].strip()
        if isinstance(data, str):
            return data.strip()
    except (json.JSONDecodeError, TypeError):
        pass

    # إذا مو JSON، نرجع النص كما هو (بعد تنظيف)
    # إزالة علامات اقتباس إذا موجودة
    if raw_text.startswith('"') and raw_text.endswith('"'):
        raw_text = raw_text[1:-1]

    return raw_text.strip()


def format_thread_for_display(main_review, replies_texts, thread_data):
    """
    تنسيق المحادثة للعرض.

    Args:
        main_review: نص التقييم الرئيسي
        replies_texts: قائمة نصوص الردود (بعد AI)
        thread_data: بيانات المحادثة من generate_thread_data

    Returns:
        str: المحادثة منسقة للعرض
    """
    lines = []
    lines.append(f'📝 التقييم الرئيسي:')
    lines.append(f'   {main_review}')
    lines.append('')

    for i, reply_info in enumerate(thread_data['replies']):
        if i < len(replies_texts):
            persona = reply_info['persona']
            role = reply_info['role']
            text = replies_texts[i]

            role_labels = {
                'questioner': '❓ سؤال',
                'answerer': '💬 جواب',
                'confirmer': '✅ تأكيد',
                'recommender': '🔥 توصية',
                'sharer': '📢 تجربة',
                'thanker': '🙏 شكر',
            }
            role_label = role_labels.get(role, '💬 رد')

            lines.append(f'   {role_label} من {persona["name"]} ({persona["city"]}):')
            lines.append(f'   {text}')
            lines.append('')

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
#  Standalone Test
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 60)
    print('🧵 Thread Generator — اختبار مولّد المحادثات')
    print('=' * 60)

    # 1) عرض أنواع المحادثات
    print('\n📋 أنواع المحادثات:')
    for info in get_all_thread_types():
        print(f'   {info["name"]}: {info["percentage"]}% — {info["desc"]}')

    # 2) عرض مواضيع الأسئلة
    print(f'\n❓ مواضيع الأسئلة: {len(QUESTION_TOPICS)}')
    for t in QUESTION_TOPICS[:5]:
        print(f'   - {t["topic"]}')
    print(f'   ... و {len(QUESTION_TOPICS) - 5} مواضيع أخرى')

    # 3) عرض أمثلة الردود
    print(f'\n💬 بنك أمثلة الردود:')
    for cat, examples in REPLY_EXEMPLARS.items():
        print(f'   {cat}: {len(examples)} مثال')

    # 4) توليد شخصية بديلة
    print(f'\n👤 شخصية بديلة:')
    fp = _fallback_persona()
    print(f'   {fp["name"]} — {fp["label"]} — {fp["city"]}')

    # 5) توليد محادثة كاملة
    print('\n' + '=' * 60)
    print('🧪 توليد محادثة تجريبية:')
    print('=' * 60)

    test_product = 'عطر المسك الأبيض — 100مل'
    test_review = 'والله عطر فخم، ريحته تجنن وثباته طول اليوم ماشاء الله'

    thread = generate_thread_data(
        product_name=test_product,
        main_review_text=test_review,
        original_persona_name='أبو سلطان',
    )

    print(f'\n   النوع: {thread["thread_type"]} — {thread["thread_desc"]}')
    if thread['topic']:
        print(f'   الموضوع: {thread["topic"]["topic"]}')
    print(f'   عدد الردود: {len(thread["replies"])}')

    for i, reply in enumerate(thread['replies']):
        print(f'\n   ── رد #{i + 1} ──')
        print(f'   الشخصية: {reply["persona"]["name"]} ({reply["persona"]["city"]})')
        print(f'   الدور: {reply["role"]}')
        print(f'   جواب من صاحب التقييم: {"نعم" if reply["is_answer"] else "لا"}')
        print(f'   طول البرومبت: {len(reply["prompt"])} حرف')
        # عرض أول 120 حرف من البرومبت
        preview = reply['prompt'][:120].replace('\n', ' ')
        print(f'   بداية البرومبت: {preview}...')

    # 6) اختبار parse_ai_reply
    print('\n' + '=' * 60)
    print('🔧 اختبار parse_ai_reply:')
    print('=' * 60)

    test_cases = [
        ('{"text": "هو يثبت بالحر؟"}', 'JSON عادي'),
        ('```json\n{"text": "والله يثبت"}\n```', 'JSON في كود بلوك'),
        ('"ريحته تجنن"', 'نص بعلامات اقتباس'),
        ('حلو مرة', 'نص عادي'),
        ('', 'نص فارغ'),
    ]

    for raw, desc in test_cases:
        result = parse_ai_reply(raw)
        status = '✅' if result or raw == '' else '❌'
        print(f'   {status} {desc}: "{raw[:40]}" → "{result}"')

    # 7) اختبار format_thread_for_display
    print('\n' + '=' * 60)
    print('📄 عرض محادثة منسقة (بنصوص وهمية):')
    print('=' * 60)

    fake_replies = ['هو يثبت بالحر؟', 'إي والله يثبت، جربته بالصيف']
    if len(thread['replies']) > len(fake_replies):
        fake_replies.extend(['أنا بعد جربته وكلامك صح'] * (len(thread['replies']) - len(fake_replies)))

    formatted = format_thread_for_display(test_review, fake_replies, thread)
    print(formatted)

    # 8) توليد 5 محادثات لرؤية التنوع
    print('=' * 60)
    print('📊 توزيع 20 محادثة عشوائية:')
    print('=' * 60)

    type_counts = {}
    for _ in range(20):
        t = generate_thread_data(test_product, test_review)
        tt = t['thread_type']
        type_counts[tt] = type_counts.get(tt, 0) + 1

    for tt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        bar = '█' * count
        print(f'   {tt}: {count} {bar}')

    print('\n✅ كل الاختبارات نجحت!')
