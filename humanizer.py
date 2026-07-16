# -*- coding: utf-8 -*-
"""
humanizer.py — طبقة أنسنة النصوص (Audit Pass) مكيّفة للعربية.

مبنية على مهارة «Signs of AI writing» (ويكيبيديا / سكِل humanizer، ٣٣ نمطاً)،
لكنها **مترجَمة لواقع نصوص العطور العربية القصيرة** بدل النقل الحرفي للأنماط
الإنجليزية (شرطة —، «vibrant tapestry»، تجنّب copula...) التي لا معنى لها في
مراجعة سعودية من كلمتين.

ثلاث طبقات متكاملة:
  1) توجيه استباقي في البرومبت  →  anti_tell_line() + voice_calibration_block()
     (أفضل رافعة: يمنع بصمة الـAI من التولّد أصلاً، ويعلّم النموذج صوت
      المراجعات الحقيقية من real_reviews_bank + مراجعات المنافسين المكشوطة).
  2) كشف بصمة الـAI              →  detect() / humanizer_violations()
     (يرجع قائمة «علامات» على نمط semantic_guard.guard_violations — للتلمترة
      ولتوجيه إعادة التوليد، لا للحذف الصامت).
  3) تنظيف تحفّظي length-aware   →  clean() / humanize_output()
     (يزيل الزخرفة غير المحتوى فقط: إيموجي/ماركداون/شرطات/اقتباس مجعّد وإطار
      المساعد الآلي. لا يحذف كلمات محتوى ولا يُرجع نصاً فارغاً من نص غير فارغ.)

قانون-4 (فلسفة المشروع): لا تلفيق ولا إفساد. المبالغات الدعائية تُكشف ويُمنع
توليدها بالبرومبت — لا تُحذف قسراً من داخل جملة قصيرة (قد يُفرغها أو يكسر معناها).

فلسفة مهمة (تمييز الجودة): حماس اللهجة السعودية الأصيل («خرافي»، «يجنّن»،
«رهيب»، «يستاهل») ليس بصمة ذكاء اصطناعي — المراجعات الحقيقية مليئة به. البصمة
الحقيقية هي **العربية الإعلانية الفصحى** التي يكتبها البوت ولا يقولها زبون حقيقي
(«يخطف الأنفاس»، «منقطع النظير»، «تحفة فنية»، «يأسر القلوب»). لذلك قائمة العلامات
أدناه تستهدف السجلّ الإعلاني حصراً وتترك حماس العامية.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get('DATA_DIR', str(BASE_DIR)))

# عتبة الطول: النص «قصير» (مايكرو-مراجعة) لا يُطبَّق عليه إلا التنظيف الآمن جداً.
MICRO_MAX_WORDS = 6


# ═══════════════════════════════════════════════════════════
#  تعابير الزخرفة غير المحتوى (تُزال بأمان — ليست كلاماً)
# ═══════════════════════════════════════════════════════════
# نطاقات الإيموجي والرموز التعبيرية (نفس نطاق app.py._EMOJI_RE + توسعة)
_EMOJI_RE = re.compile(
    '[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    '\U00002190-\U000021FF\U00002B00-\U00002BFF️‍•]+')

# شرطات AI الشهيرة (—, –, --) — SKILL §14. تُحوَّل لفاصل بسيط.
_DASH_RE = re.compile(r'\s*(?:—|–|--)\s*')

# اقتباس مجعّد → مستقيم — SKILL §19
_CURLY_MAP = {'“': '"', '”': '"', '‘': "'", '’': "'", '«': '"', '»': '"'}

# زخرفة ماركداون: عريض/عناوين/تعداد — SKILL §15،§16،§17
_MD_BOLD_RE = re.compile(r'\*{1,3}([^*]+)\*{1,3}')     # **نص** → نص
_MD_HEADER_RE = re.compile(r'^\s{0,3}#{1,6}\s+', re.MULTILINE)  # ## عنوان →
_MD_BULLET_RE = re.compile(r'^\s{0,3}[-*+]\s+', re.MULTILINE)   # - بند →


# ═══════════════════════════════════════════════════════════
#  علامات بصمة الـAI العربية (كشف فقط — سجلّ إعلاني فصيح)
# ═══════════════════════════════════════════════════════════
# مبالغات دعائية بالفصحى الإعلانية — يكتبها البوت ولا يقولها زبون سعودي حقيقي.
# (لا تحوي «خرافي/يجنّن/رهيب/يستاهل» عمداً — تلك حماس عامية أصيل.)
AR_MARKETING_TELLS = [
    'يخطف الأنفاس', 'تخطف الأنفاس', 'يأخذ الألباب', 'يأسر القلوب', 'تأسر القلوب',
    'يسلب الألباب', 'تسلب الألباب', 'يخطف الأنظار', 'تخطف الأنظار',
    'منقطع النظير', 'لا مثيل له', 'لا مثيل لها', 'بلا منازع', 'يفوق الخيال',
    'يفوق الوصف', 'لا يوصف', 'لا يُوصف', 'تحفة فنية', 'تحفة حقيقية',
    'قمة الروعة', 'قمة الأناقة', 'قمة الفخامة', 'روعة لا توصف', 'جمال أخّاذ',
    'جمال أخاذ', 'أناقة راقية', 'فخامة لا مثيل', 'سحر لا يقاوم', 'سحر خاص',
    'عبق ساحر', 'نفحات ساحرة', 'إبداع منقطع', 'تجربة لا تُنسى', 'تجربة لا تنسى',
    'تجربة استثنائية', 'خيار مثالي', 'الخيار الأمثل', 'يستحق كل التقدير',
    'آسر', 'يبهر', 'مبهر', 'إبهار',
]

# آثار المحادثة الآلية — إطار مساعد لُصق كمحتوى (SKILL §20). يُزال بأمان.
AR_CHATBOT_ARTIFACTS = [
    'إليك تقييمي', 'إليك رأيي', 'إليك التقييم', 'إليكم تقييمي', 'إليك',
    'إليكم', 'يسعدني أن', 'يسعدني', 'بكل سرور', 'بكل تأكيد', 'بالطبع',
    'دعني أخبرك', 'دعوني أخبركم', 'دعنا', 'دعونا', 'آمل أن يكون مفيداً',
    'أتمنى أن يكون مفيداً', 'أتمنى أن ينال إعجابك', 'هل تريد المزيد',
    'إذا أردت المزيد', 'تفضل', 'بالتأكيد يمكنني',
]

# تلميحات استعراضية (Signposting) — SKILL §28
AR_SIGNPOSTING = [
    'دعونا نتحدث', 'دعونا نستعرض', 'في هذا التقييم', 'سأتحدث عن',
    'سنتحدث عن', 'في البداية أود', 'قبل أن نبدأ',
]

# خواتيم تحفيزية عامة بالفصحى (SKILL §25) — يكتبها البوت لإنهاء «مقال».
# (لا تشمل «يستاهل/أنصحكم فيه» العاميّة — تلك خاتمة زبون حقيقي.)
AR_GENERIC_CLOSERS = [
    'أنصح الجميع بتجربته', 'أنصح الجميع به', 'أنصح به بشدة', 'ننصح بشدة',
    'بشكل عام تجربة رائعة', 'في الختام', 'وفي النهاية أنصح',
    'تجربة تستحق التكرار', 'لن تندم على شرائه',
]

# قاعدة الثلاثة (SKILL §10 الأصلي: 3 صفات معطوفة). معايرة على 100 نص منافس
# حقيقي >6 كلمات: نسخة الثلاث كانت تُشعل زوراً على 14/100 (العطف الثلاثي
# عادي بالعامية السعودية: «ثابت وفواح وجميل»). رُفعت لأربع معطوفات متتالية
# (نمط بوت أوضح ونادر بشرياً) — نفس القياس: 1/100 فقط.
_RULE_OF_THREE_RE = re.compile(
    r'(\S+)\s+و(\S+)\s+و(\S+)\s+و(\S+)')

# تكرار كلمة محورية — مرصود ميدانياً في المولّد القالبي («المقدمه فريشه...
# المقدمه حاره...»، «ثباته...ثباته...») حيث يبدو النص كقوالب ملتصقة لا سرد
# إنسان واحد. نفس الخطر ممكن من الـAI الحي (تكرار سهو لكلمة كـ«يهبل»).
# معايرة على 100 نص منافس حقيقي >6 كلمات: عتبة التكرار مرتين كانت تُشعل
# زوراً على 18/100 (بشر يعيدون كلمة أساسية كـ«عطر»/«ريحته» بلا قصد سرد
# ملتصق) — رُفعت لثلاث مرات فأكثر مع اشتراط عدم كون كل الظهورات متجاورة
# محضاً (تشديد لهجة مقصود مثل «فخم فخم فخم» — لا يُحسب مهما تكرر). نفس
# القياس بعد الرفع: 4/100.
_REPEAT_STOPWORDS = set(
    'و من في على عن إلى الى لي له لها ما لا او أو بس كل أي اي يا مع هذا '
    'هذه هذي حتى بعد قبل ذا اللي التي الذي عليه فيه منه لكم لكن ثم قد لم '
    'لن إن ان لو إذا اذا عند مو كان صار'.split())


def _has_nonadjacent_repeat(text, min_repeats=3):
    """كلمة محتوى (≥3 أحرف) تتكرر ≥3 مرات مع فاصل كلمة على الأقل بين ظهورين.

    التكرار المتجاور المحض («فخم فخم فخم») لا يُحسب مهما بلغ عدده —
    تشديد لهجة مقصود ومعاير على بيانات منافسين حقيقية.
    """
    positions = {}
    for i, w in enumerate((text or '').split()):
        w = w.strip('.,!؟،')
        if len(w) < 3 or w in _REPEAT_STOPWORDS:
            continue
        positions.setdefault(w, []).append(i)
    for idxs in positions.values():
        if len(idxs) >= min_repeats and any(
                b - a >= 2 for a, b in zip(idxs, idxs[1:])):
            return True
    return False


def _compile_phrase_list(phrases):
    """يبني Regex يطابق أياً من العبارات ككلمة/عبارة مستقلة (مع أدوات عطف شائعة)."""
    parts = sorted((re.escape(p) for p in phrases), key=len, reverse=True)
    return re.compile(r'(?<![ء-ي])(?:و|ف|ثم\s+)?(?:' + '|'.join(parts) +
                      r')(?![ء-ي])')


_MARKETING_RE = _compile_phrase_list(AR_MARKETING_TELLS)
_CHATBOT_RE = _compile_phrase_list(AR_CHATBOT_ARTIFACTS)
_SIGNPOST_RE = _compile_phrase_list(AR_SIGNPOSTING)
_CLOSER_RE = _compile_phrase_list(AR_GENERIC_CLOSERS)


# ═══════════════════════════════════════════════════════════
#  أدوات أساسية
# ═══════════════════════════════════════════════════════════
def word_count(text):
    return len((text or '').split())


def strip_emoji(text):
    return _EMOJI_RE.sub(' ', text or '')


def strip_typographic(text):
    """يزيل الزخرفة الطباعية (SKILL §14،§15،§16،§17،§19) بلا مساس بالمحتوى العربي."""
    if not text:
        return ''
    t = text
    for c, r in _CURLY_MAP.items():
        t = t.replace(c, r)
    t = _DASH_RE.sub(' ، ', t)          # شرطة AI → فاصلة عربية
    t = _MD_BOLD_RE.sub(r'\1', t)       # **عريض** → عريض
    t = _MD_HEADER_RE.sub('', t)        # ## عنوان → عنوان
    t = _MD_BULLET_RE.sub('', t)        # - بند → بند
    t = t.replace('`', '')
    return t


# ═══════════════════════════════════════════════════════════
#  الكشف — يرجع قائمة علامات (نمط semantic_guard.guard_violations)
# ═══════════════════════════════════════════════════════════
def detect(text, kind='review'):
    """يرجع قائمة نصية بأنواع بصمة الـAI الموجودة (فارغة = نظيف).

    للتلمترة وتوجيه إعادة التوليد. لا يعدّل النص.
    """
    if not text:
        return []
    tells = []
    if _EMOJI_RE.search(text):
        tells.append('إيموجي/رموز')
    if _DASH_RE.search(text):
        tells.append('شرطة AI (—)')
    if any(c in text for c in _CURLY_MAP):
        tells.append('اقتباس مجعّد')
    if _MD_BOLD_RE.search(text) or _MD_HEADER_RE.search(text):
        tells.append('زخرفة ماركداون')
    mk = _MARKETING_RE.findall(text)
    if mk:
        tells.append('مبالغة دعائية فصحى')
    if _CHATBOT_RE.search(text):
        tells.append('آثار مساعد آلي')
    if _SIGNPOST_RE.search(text):
        tells.append('تلميح استعراضي')
    if _CLOSER_RE.search(text):
        tells.append('خاتمة تحفيزية عامة')
    # قاعدة الثلاثة تُحسب علامة في النص الأطول فقط
    if word_count(text) > MICRO_MAX_WORDS and _RULE_OF_THREE_RE.search(text):
        tells.append('قاعدة الثلاثة')
    # تكرار كلمة محورية: نفس المنطق — يشوّه المايكرو-مراجعة القصيرة لو طُبّق عليها
    if word_count(text) > MICRO_MAX_WORDS and _has_nonadjacent_repeat(text):
        tells.append('تكرار كلمة محورية')
    return tells


# اسم مرادف يوائم اصطلاح الحُرّاس الأخرى في المشروع
def humanizer_violations(text, max_words=None, kind='review'):
    """مرادف detect() بتوقيع موائم لـ guard_violations(text, max_words)."""
    return detect(text, kind=kind)


# علامات على مستوى المحتوى فقط (تنجو من _humanize الذي يزيل الترقيم/الرموز).
# تُستخدم لتوجيه إعادة التوليد: نص بنبرة إعلانية/آلية يُعاد لا يُبتر.
_CONTENT_TELLS = {'مبالغة دعائية فصحى', 'آثار مساعد آلي', 'تلميح استعراضي',
                  'خاتمة تحفيزية عامة', 'قاعدة الثلاثة', 'تكرار كلمة محورية'}


def content_tells(text, kind='review'):
    """يرجع علامات المحتوى فقط (بلا إيموجي/شرطة/ماركداون — يزيلها التنظيف أصلاً)."""
    return [t for t in detect(text, kind=kind) if t in _CONTENT_TELLS]


# ═══════════════════════════════════════════════════════════
#  التنظيف التحفّظي (Audit Pass) — length-aware, لا يفرغ نصاً
# ═══════════════════════════════════════════════════════════
def _strip_leading(text, pattern):
    """يزيل عبارة إطار من بداية النص فقط (مع نقطتين/فاصلة تابعة)، بأمان."""
    m = pattern.match(text.lstrip())
    if not m:
        return text
    rest = text.lstrip()[m.end():].lstrip(' :،,.-')
    return rest if rest.strip() else text  # لا نُفرغ النص


def _strip_trailing(text, pattern):
    """يزيل خاتمة عامة من نهاية النص فقط، بأمان (لا يُفرغ)."""
    # نبحث عن آخر مطابقة قريبة من النهاية
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    last = matches[-1]
    # نزيلها فقط لو كانت في الربع الأخير من النص (خاتمة فعلية لا محتوى)
    if last.start() < len(text) * 0.6:
        return text
    head = text[:last.start()].rstrip(' :،,.-و')
    return head if head.strip() else text


def strip_frame(text):
    """يزيل إطار المساعد الآلي (بداية) والتلميح الاستعراضي والخاتمة العامة (نهاية).

    محافظ: لا يمسّ إلا الأطراف، ولا يُرجع نصاً فارغاً أبداً.
    """
    if not text:
        return ''
    t = text
    t = _strip_leading(t, _CHATBOT_RE)
    t = _strip_leading(t, _SIGNPOST_RE)
    t = _strip_trailing(t, _CLOSER_RE)
    return t


def clean(text, kind='review'):
    """طبقة المراجعة النهائية (Audit Pass): تنظيف تحفّظي length-aware.

    آمن دائماً: يزيل الزخرفة غير المحتوى (إيموجي/ماركداون/شرطات/اقتباس مجعّد)
    وإطار المساعد الآلي. **لا يحذف** كلمات المحتوى ولا المبالغات (تُمنع بالبرومبت،
    وتبقى للكشف فقط). لا يُرجع نصاً فارغاً من نص غير فارغ (قانون-4).
    """
    if not text or not text.strip():
        return ''
    original = text
    t = strip_emoji(text)
    t = strip_typographic(t)
    # إطار المساعد يُزال في كل الأطوال (بداية «إليك تقييمي:» زخرفة لا محتوى)،
    # لكن بحذر: الدوال الداخلية لا تُفرغ النص.
    t = strip_frame(t)
    t = re.sub(r'[ \t]*\n[ \t]*', ' ', t)   # أسطر → مسافة (نص متدفّق)
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:                                # حماية مطلقة: لا نُفرغ نصاً غير فارغ
        return re.sub(r'\s+', ' ', original).strip()
    return t


def humanize_output(text, kind='review'):
    """المدخل الموحّد (Middleware seam): أي نص متجه للمستخدم يمرّ من هنا.

    مرادف clean() باسم يوضّح دوره كطبقة وسطى. استُخدم في app.py/streamlit_app.py
    كي يمرّ كل مخرج (تقييم/متجر/رد/سلسلة/حملة) بطبقة أنسنة واحدة.
    """
    return clean(text, kind=kind)


# ═══════════════════════════════════════════════════════════
#  معايرة الصوت — تعلّم أسلوب المراجعات الحقيقية (SKILL: Voice Calibration)
#  المصدر: real_reviews_bank (منسّق) + مراجعات المنافسين المكشوطة (خط mahalli)
# ═══════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def _load_scraped_voices():
    """يحمّل نصوص مراجعات المنافسين الحقيقية (مخرَج خط كشط mahalli).

    مصدر «صوت» حقيقي لمعايرة الأسلوب. يتحمّل غياب الملف أو تلفه بصمت.
    """
    for fname in ('competitor_reviews_full.json', 'competitor_reviews.json'):
        for base in (DATA_DIR, BASE_DIR):
            p = base / fname
            if not p.exists():
                continue
            try:
                data = json.load(open(p, encoding='utf-8'))
            except Exception:
                continue
            revs = data.get('reviews') if isinstance(data, dict) else data
            if not isinstance(revs, list):
                continue
            out = []
            for r in revs:
                txt = (r.get('text') if isinstance(r, dict) else r) or ''
                txt = txt.strip()
                # نتجنّب المبالغات الدعائية في عيّنة «الصوت» كي لا نعلّم البوت بصمته
                if 2 <= word_count(txt) <= 14 and not _MARKETING_RE.search(txt):
                    out.append(txt)
            if out:
                return tuple(out)
    return tuple()


def _norm_gender(gender):
    """يطبّع أي تمثيل للجنس إلى 'male'/'female' كما يتوقّعه real_reviews_bank."""
    g = (gender or '').strip().lower()
    if g in ('female', 'f', 'أنثى', 'انثى', 'نسائي', 'امرأة', 'woman', 'w'):
        return 'female'
    return 'male'


def _bank_voices(kind, gender):
    """عيّنات صوت من real_reviews_bank حسب النوع (تقييم/متجر) والجنس."""
    try:
        import real_reviews_bank as bank
    except Exception:
        return []
    try:
        if kind == 'store':
            return list(getattr(bank, 'STORE_REVIEWS_BANK', []))
        picks = bank.pick_review_exemplars(gender=_norm_gender(gender), count=8)
        return list(picks or [])
    except Exception:
        return []


def _pick_spread(items, n, seed_text=''):
    """يختار n عناصر موزّعة (بلا عشوائية غير حتمية — يعتمد طول seed_text)."""
    items = [i for i in dict.fromkeys(items) if i and i.strip()]
    if not items:
        return []
    if len(items) <= n:
        return items
    step = max(1, len(items) // n)
    start = (len(seed_text) * 7) % len(items)
    out = []
    i = start
    while len(out) < n and len(out) < len(items):
        cand = items[i % len(items)]
        if cand not in out:
            out.append(cand)
        i += step or 1
    return out


def voice_calibration_block(kind='review', gender=None, n=6, seed_text=''):
    """كتلة معايرة الصوت للبرومبت: «اكتب بروح هذه المراجعات الحقيقية».

    تدمج بنك المراجعات المنسّق + مراجعات المنافسين المكشوطة (mahalli)، وتُرفق
    سطر «ابتعد عن نبرة الإعلانات». ترجع '' بأمان إن لا مصادر (تدرّج ناعم).

    seed_text: أي نص (اسم المنتج/الشخصية) لتنويع العيّنة المختارة حتمياً.
    """
    voices = _bank_voices(kind, gender)
    if kind != 'store':
        voices = list(voices) + list(_load_scraped_voices())
    picks = _pick_spread(voices, n, seed_text=seed_text)
    if not picks:
        return ''
    lines = '\n'.join(f'- {t}' for t in picks)
    return (
        '## اكتب بروح هذه المراجعات الحقيقية (للأسلوب والصوت فقط — لا تنسخها حرفياً):\n'
        f'{lines}\n'
        f'{anti_tell_line(kind=kind)}'
    )


def anti_tell_line(kind='review'):
    """سطر توجيه مضغوط يصلح حتى للمراجعات القصيرة جداً (يمنع بصمة الـAI استباقياً)."""
    return (
        '## اكتب كإنسان لا كإعلان:\n'
        '- بلا مبالغات دعائية فصيحة (يخطف الأنفاس، منقطع النظير، تحفة فنية، '
        'يأسر القلوب، لا يوصف) — حماس اللهجة العادي مسموح\n'
        '- بلا عبارات مساعد آلي (إليك، يسعدني، بالطبع، دعني)\n'
        '- بلا خاتمة تحفيزية عامة ولا رصّ ثلاث صفات معطوفة'
    )


# ═══════════════════════════════════════════════════════════
#  إحصاء (للتلمترة/guardian)
# ═══════════════════════════════════════════════════════════
def stats():
    return {
        'marketing_tells': len(AR_MARKETING_TELLS),
        'chatbot_artifacts': len(AR_CHATBOT_ARTIFACTS),
        'signposting': len(AR_SIGNPOSTING),
        'generic_closers': len(AR_GENERIC_CLOSERS),
        'scraped_voices': len(_load_scraped_voices()),
        'micro_max_words': MICRO_MAX_WORDS,
    }


if __name__ == '__main__':
    print('humanizer stats:', json.dumps(stats(), ensure_ascii=False, indent=2))
    samples = [
        'إليك تقييمي: هذا العطر تحفة فنية تخطف الأنفاس! 🌟🔥 أنصح الجميع بتجربته.',
        'ثباته خرافي ويجنّن',                       # حماس عامية أصيل — يجب ألا يُلمس محتواه
        'عطر **رائع** — فخامة لا مثيل لها',
        'جميل وراحه حلوه',
    ]
    for s in samples:
        print('\nقبل :', s)
        print('علامات:', detect(s))
        print('بعد :', clean(s))
