# -*- coding: utf-8 -*-
import sys, os, json, re, random, requests as http_req, time
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:  # توافق مع إصدارات urllib3 الأقدم
    from requests.packages.urllib3.util.retry import Retry
# ضمان ترميز UTF-8 للطباعة (يمنع تعطّل الإيموجي على كونسول Windows cp1256)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# CORS مقيّد على نطاقات متجرك — اضبط ALLOWED_ORIGINS في البيئة (مفصولة بفواصل).
# الافتراضي '*' للتطوير المحلي فقط؛ في الإنتاج ضع نطاقك الفعلي.
_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('ALLOWED_ORIGINS', '*').split(',') if o.strip()]
CORS(app, resources={r"/api/*": {"origins": _ALLOWED_ORIGINS}})
BASE_DIR = Path(__file__).parent


def _safe_int(value, default, lo, hi):
    """تحويل آمن لعدد صحيح من مدخل غير موثوق مع تقييده ضمن [lo, hi]."""
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default

# ═══════════════════════════════════════════════════════════
# Rate limiting — حماية endpoints الذكاء الاصطناعي من الإساءة/استنزاف رصيد OpenRouter.
# اختياري وآمن: إن لم تكن flask-limiter مثبّتة يصبح rate_limit ديكوريتر بلا أثر،
# فلا يكسر التطوير المحلي. في الإنتاج تُثبَّت تلقائياً من requirements.txt.
# تُضبط الحدود عبر متغيرات البيئة (RATE_LIMIT_DEFAULT / RATE_LIMIT_GENERATE).
# ═══════════════════════════════════════════════════════════
RATE_LIMIT_GENERATE = os.environ.get('RATE_LIMIT_GENERATE', '20 per minute')
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[os.environ.get('RATE_LIMIT_DEFAULT', '300 per hour')],
        storage_uri=os.environ.get('RATE_LIMIT_STORAGE', 'memory://'),
    )

    def rate_limit(rule):
        return _limiter.limit(rule)
    USE_RATE_LIMIT = True
    print('✅ flask-limiter loaded (rate limiting active: %s)' % RATE_LIMIT_GENERATE)
except Exception as _e:
    USE_RATE_LIMIT = False

    def rate_limit(rule):
        def _decorator(fn):
            return fn
        return _decorator
    print('⚠️ flask-limiter not active (%s) — endpoints unthrottled' % _e)

# المسار الثابت للبيانات المؤقتة — Railway يضبطه على /data (Persistent Volume).
# يبقى بين عمليات النشر. الكود والبيانات الثابتة (catalog/names/.env) تبقى في BASE_DIR.
DATA_DIR = Path(os.environ.get('DATA_DIR', str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# استيراد المحركات الجديدة (مع fallback آمن)
# ═══════════════════════════════════════════════════════════
try:
    from personas_engine import (generate_persona, generate_review_params, build_master_prompt,
                                  set_catalog as pe_set_catalog, ARCHETYPES as NEW_ARCHETYPES)
    USE_NEW_PERSONAS = True
    print('\u2705 personas_engine loaded')
except ImportError:
    USE_NEW_PERSONAS = False
    print('\u26a0\ufe0f personas_engine not found, using legacy')

try:
    from dialects import get_dialect_for_city, get_dialect_examples, apply_typos
    USE_DIALECTS = True
    print('\u2705 dialects loaded')
except ImportError:
    USE_DIALECTS = False
    print('\u26a0\ufe0f dialects not found')

try:
    from review_patterns import (get_ai_directive, get_pattern_description,
                                  REVIEW_PATTERNS, PATTERN_CATEGORIES)
    USE_PATTERNS = True
    print('\u2705 review_patterns V2 loaded (%d patterns, %d categories)' % (len(REVIEW_PATTERNS), len(PATTERN_CATEGORIES)))
except ImportError:
    USE_PATTERNS = False
    print('\u26a0\ufe0f review_patterns not found')

try:
    from anti_repeat import (archive_review as ar_archive_review, archive_batch as ar_archive_batch,
                             get_used_texts as ar_get_used_texts, get_archive_stats as ar_get_archive_stats,
                             clear_archive as ar_clear_archive, format_used_texts_block, is_duplicate,
                             register_text as ar_register_text)
    USE_ANTI_REPEAT = True
    print('\u2705 anti_repeat loaded')
except ImportError:
    USE_ANTI_REPEAT = False
    print('\u26a0\ufe0f anti_repeat not found')

try:
    from semantic_guard import guard_violations, strip_broken_tail
    USE_SEMANTIC_GUARD = True
    print('\u2705 semantic_guard loaded')
except ImportError:
    USE_SEMANTIC_GUARD = False
    print('\u26a0\ufe0f semantic_guard not found')

try:
    from trending import calculate_product_weight, get_trending_names, blend_selection
    USE_TRENDING = True
    print('\u2705 trending loaded')
except ImportError:
    USE_TRENDING = False
    print('\u26a0\ufe0f trending not found')

try:
    import demographic_matcher as _demo
    USE_DEMO_MATCH = True   # \u0645\u0637\u0627\u0628\u0642\u0629 \u062f\u064a\u0645\u0648\u063a\u0631\u0627\u0641\u064a\u0629 \u2014 \u0639\u0644\u0645 \u062a\u062d\u0643\u0651\u0645 (\u0637\u0631\u064a\u0642 \u0639\u0648\u062f\u0629 \u0641\u0648\u0631\u064a)
    print('\u2705 demographic_matcher loaded')
except ImportError:
    USE_DEMO_MATCH = False
    print('\u26a0\ufe0f demographic_matcher not found')

try:
    from thread_generator import generate_thread_data, parse_ai_reply, format_thread_for_display
    USE_THREADS = True
    print('\u2705 thread_generator loaded')
except ImportError:
    USE_THREADS = False
    print('\u26a0\ufe0f thread_generator not found')

try:
    from short_texts_bank import pick_short_text as stb_pick_short
    USE_SHORT_BANK = True
    print('\u2705 short_texts_bank loaded')
except ImportError:
    USE_SHORT_BANK = False
    print('\u26a0\ufe0f short_texts_bank not found')

try:
    from golden_reviews import get_stats as golden_stats  # مثال الذهبي لم يعد يُحقن في مسار المتجر
    USE_GOLDEN = True
    print('\u2705 golden_reviews loaded (%d reviews)' % golden_stats()['total'])
except ImportError:
    USE_GOLDEN = False
    print('\u26a0\ufe0f golden_reviews not found')

# \u062f\u0648\u0627\u0644 \u062a\u062a\u0628\u0639 \u0627\u0644\u062a\u0643\u0631\u0627\u0631 (\u0623\u0646\u0645\u0627\u0637 + \u0635\u0641\u0627\u062a) \u2014 \u062a\u064f\u0633\u062a\u062f\u0639\u0649 \u0628\u0639\u062f \u0643\u0644 \u062a\u0648\u0644\u064a\u062f AI \u0646\u0627\u062c\u062d
try:
    from anti_repeat import track_pattern as ar_track_pattern, track_adjective as ar_track_adjective
    USE_AR_TRACK = True
except ImportError:
    USE_AR_TRACK = False

# \u0645\u062d\u0631\u0643 \u0627\u0644\u0642\u0648\u0627\u0644\u0628 \u0627\u0644\u0636\u062e\u0645 \u2014 \u0634\u0628\u0643\u0629 \u0627\u0644\u0623\u0645\u0627\u0646 \u0627\u0644\u062d\u0642\u064a\u0642\u064a\u0629 \u0639\u0646\u062f \u062a\u0639\u0637\u0651\u0644 \u0627\u0644\u0640 AI
try:
    from review_generator import ReviewGenerator
    fallback_gen = ReviewGenerator()
    USE_REVIEW_GEN = True
    print('\u2705 review_generator loaded (fallback engine)')
except Exception as _e:
    fallback_gen = None
    USE_REVIEW_GEN = False
    print(f'\u26a0\ufe0f review_generator not available: {_e}')

try:
    from mahalli_intel import (get_our_products as intel_get_our_products,
                               get_competitors as intel_get_competitors,
                               get_our_rank as intel_get_our_rank,
                               get_priorities as intel_get_priorities,
                               generate_daily_plan as intel_daily_plan,
                               get_dashboard_summary as intel_dashboard,
                               refresh_all_data as intel_refresh)
    USE_INTEL = True
    print('\u2705 mahalli_intel loaded')
except ImportError:
    USE_INTEL = False
    print('\u26a0\ufe0f mahalli_intel not found')

with open(BASE_DIR / 'names.json', 'r', encoding='utf-8') as f:
    NAMES = json.load(f)

# ═══════════════════════════════════════════════════════════
# أرشيف — يستخدم anti_repeat إذا متوفر، وإلا يعمل كالسابق
# ═══════════════════════════════════════════════════════════
ARCHIVE_FILE = DATA_DIR / 'archive.json'

def _load_archive():
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'reviews':[], 'store_reviews':[], 'personas':[]}
    return {'reviews':[], 'store_reviews':[], 'personas':[]}

def _save_archive(archive):
    # FIFO: حد أقصى 200 تقييم
    if len(archive.get('reviews', [])) > 200:
        archive['reviews'] = archive['reviews'][-200:]
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive, f, ensure_ascii=False, indent=1)

def _get_used_texts(archive, limit=40):
    """آخر 40 نص مستخدم لإرسالها للـ AI"""
    if USE_ANTI_REPEAT:
        return ar_get_used_texts(limit)
    texts = [r.get('text','') for r in archive.get('reviews',[])]
    return texts[-limit:] if len(texts)>limit else texts

def _archive_review(review_text, product_name, persona_name):
    """حفظ تقييم في الأرشيف"""
    if USE_ANTI_REPEAT:
        ar_archive_review(review_text, product_name, persona_name)
        return
    arc = _load_archive()
    arc['reviews'].append({
        'text': review_text,
        'product': product_name,
        'persona': persona_name,
        'ts': int(time.time())
    })
    _save_archive(arc)

def _archive_batch(reviews, persona_name):
    """حفظ مجموعة تقييمات"""
    if USE_ANTI_REPEAT:
        ar_archive_batch(reviews, persona_name)
        return
    arc = _load_archive()
    for rv in reviews:
        arc['reviews'].append({
            'text': rv.get('text',''),
            'product': rv.get('product',''),
            'persona': persona_name,
            'ts': int(time.time())
        })
    _save_archive(arc)

print(f'\U0001f4e6 Archive: {len(_load_archive().get("reviews",[]))} reviews')

# ═══════════════════════════════════════════════════════════
# OpenRouter AI — نصوص فريدة لكل شخصية وعطر
# ═══════════════════════════════════════════════════════════
# حمّل .env يدوياً (os مستورد في الأعلى)
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    for line in _env_path.read_text(encoding='utf-8').strip().split('\n'):
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

# يقبل عدة أسماء شائعة للمتغيّر (Railway قد يستخدم OPENROUTER_API_KEY)
AI_KEY = (os.environ.get('AI_KEY')
          or os.environ.get('OPENROUTER_API_KEY')
          or os.environ.get('OPENROUTER_KEY')
          or os.environ.get('OPENROUTER_API')
          or '').strip()
AI_URL = 'https://openrouter.ai/api/v1/chat/completions'
AI_MODEL = 'google/gemini-2.5-flash'
AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '45'))   # مهلة أطول: نقبل البطء مقابل تقييم صحيح
AI_TEMPERATURE = 0.9     # درجة إبداع عالية لضمان تنوع النصوص


class AIUnavailable(Exception):
    """يُرفع عند تعذّر الاتصال بالـ AI أو نفاد الرصيد — التطبيق يتوقف ولا يكتب قوالب."""
    pass

# جلسة HTTP ثابتة مع إعادة محاولة تلقائية — تستقر تحت ضغط الواجهة المباشرة
_ai_session = http_req.Session()
_ai_retry = Retry(
    total=3, connect=3, read=2, backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(['POST']),
)
_ai_session.mount('https://', HTTPAdapter(max_retries=_ai_retry))
_ai_session.headers.update({
    'Authorization': f'Bearer {AI_KEY}',
    'Content-Type': 'application/json',
})


def extract_json(text):
    """استخراج كائن JSON بأمان من رد الـ AI حتى لو تضمّن نصاً إضافياً.

    يبحث عن أول '{' وآخر '}' عبر Regex لمنع تعطّل الكود إذا أرجع النموذج
    نصاً عادياً مع الـ JSON أو غلّفه بـ markdown.
    """
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception:
        return None


def _ai_call(prompt, max_tokens=1200, temperature=AI_TEMPERATURE):
    """استدعاء AI عبر OpenRouter — جلسة ثابتة + Retry + مهلة 15ث"""
    try:
        r = _ai_session.post(AI_URL, json={
            'model': AI_MODEL,
            'messages': [{'role':'user','content':prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }, timeout=AI_TIMEOUT)
        data = r.json()
        if r.status_code != 200:
            err = data.get('error',{}).get('message','unknown')
            print(f'⚠️ AI HTTP {r.status_code}: {err}')
            return None
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f'❌ AI Error: {e}')
        return None

def _make_persona_for_arch(arch):
    """شخصية كاملة من archetype — عميقة (7 أبعاد) إن توفّر المحرك الجديد.

    تضمن أن البرومبت المتقدم يجد كل المفاتيح (dialect/mood/expertise...)
    حتى في مسارات regen/add-perfumes التي كانت تمرر شخصية ناقصة.
    """
    if USE_NEW_PERSONAS:
        return generate_persona(arch)
    age = random.randint(*arch['age'])
    city = _city()
    return {
        'name': _name(arch['g']), 'label': arch['label'], 'gender': arch['g'],
        'age': age, 'city': city, 'emoji': arch.get('emoji', ''), 'archId': arch['id'],
        'address': _national_address(city), 'phone': _phone(),
    }


def _build_cross_sell(current_name, perfumes):
    """توجيه Cross-Sell/Layering: يذكر منتجاً ثانياً من نفس المتجر داخل التقييم.

    يرفع قيمة السلة. يُستخدم منتج آخر من نفس سلة الشخصية (طبيعي أكثر).
    يرجع نصاً (قد يكون فارغاً).
    """
    others = [p['name'] for p in perfumes if p.get('name') and p['name'] != current_name]
    if not others or random.random() >= 0.30:
        return ''
    other = random.choice(others)
    if random.random() < 0.5:
        return ('## ترابط منتجات (Cross-Sell):\n'
                f'- اذكر بعفوية أنك طلبت أيضاً "{other}" من نفس المتجر بنفس الطلب وامدحه بإيجاز '
                '(كلمة أو كلمتين) — لا تجعله محور التقييم.')
    return ('## وصفة سرية (Layering):\n'
            f'- اقترح خلطة شخصية اكتشفتها: رشة من هذا العطر وفوقها رشة من "{other}" من نفس المتجر، '
            'وصف النتيجة باختصار كأنها سر مميز.')


def _make_master_prompt(persona, product_name, used_block, extra_block=''):
    """بناء البرومبت المتقدم إجبارياً. يرجع (prompt, params).

    review_patterns اختياري (له بدائل افتراضية داخل personas_engine)، لكن
    لا نتراجع للبرومبت القديم إلا إذا فشل تحميل personas_engine بالكامل.
    """
    if USE_NEW_PERSONAS:
        params = generate_review_params(persona)
        result = build_master_prompt(persona, product_name, params, used_block, extra_block)
        # build_master_prompt returns (prompt, params) tuple
        if isinstance(result, tuple):
            return result
        return result, params
    # حالة قصوى: personas_engine غير محمّل إطلاقاً — نسرد قصة بدل الوصف الجاف
    rating = 5 if random.random() < 0.6 else (4 if random.random() < 0.7 else 3)
    prompt = (
        f"اكتب تقييم عطر من 1 إلى 4 كلمات فقط بلهجة سعودية عامية.\n"
        f"المنتج: {product_name}\n"
        f"التقييم: {rating} نجوم\n"
        f"أمثلة: ممتاز / والله حلو / ريحته ثابتة / يستاهل كل ريال\n"
        f"لا تذكر اسم المنتج. بدون ترقيم.\n"
        f"{('لا تكرر: ' + used_block) if used_block else ''}\n"
        f'أرجع JSON فقط: {{"rating": {rating}, "text": "...", "is_verified_purchase": true}}'
    )
    return prompt, {'rating': rating, 'pattern': 'ultra_short'}


# ═══════════════════════════════════════════════════════════
# تنظيف النص — يضمن نصاً بشرياً بلا ترقيم أو رموز (طبقة ضمان نهائية)
# ═══════════════════════════════════════════════════════════

# علامات ترقيم عربية/لاتينية + رموز تُزال لجعل النص يتدفّق طبيعياً كرسالة سريعة
_PUNCT_RE = re.compile(r'[،,؛;:.…·•\-–—_\"“”\'‘’`«»()\[\]{}<>/\\|*#^~=+%&@!؟?]+')
# نطاقات الإيموجي والرموز التعبيرية
_EMOJI_RE = re.compile(
    '[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    '\U00002190-\U000021FF\U00002B00-\U00002BFF️‍•]+')


def _humanize(text):
    """يزيل كل علامات الترقيم والرموز والإيموجي ويترك تدفّقاً عربياً طبيعياً."""
    if not text:
        return ''
    t = text.replace('\n', ' ').replace('\r', ' ')
    t = _EMOJI_RE.sub(' ', t)
    t = _PUNCT_RE.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# ═══════════════════════════════════════════════════════════
# طبقة ضمان التفرّد — كل نص (تقييم/متجر/رد) فريد لا يتكرر
# ═══════════════════════════════════════════════════════════

def _is_dup(text):
    """هل النص مكرر؟ (يعمل فقط عند توفّر anti_repeat)."""
    return bool(USE_ANTI_REPEAT and text and is_duplicate(text))


def _register(text):
    """تسجيل نص مقبول في طبقة الجلسة لمنع تكراره لاحقاً."""
    if USE_ANTI_REPEAT and text:
        try:
            ar_register_text(text)
        except Exception:
            pass


def _ai_unique_json(prompt, max_tokens, attempts=4, temp_step=0.06):
    """يستدعي AI متعدّد المحاولات حتى يحصل على JSON بنص فريد.

    يصعّد الحرارة والتلميح في كل محاولة. يرجع آخر dict صالح (قد يكون مكرراً
    لو فشلت كل المحاولات — المستدعي يلجأ لشبكة أمان فريدة).
    """
    best = None
    for k in range(attempts):
        hint = '' if k == 0 else (
            f'\n\n⚠️ المحاولة {k+1}: النص السابق مكرر أو قريب جداً من تقييم موجود. '
            'غيّر البداية والكلمات والفكرة كلياً واكتب صياغة جديدة تماماً.')
        out = _ai_call(prompt + hint, max_tokens=max_tokens,
                       temperature=min(1.0, AI_TEMPERATURE + k * temp_step))
        rv = extract_json(out)
        if not rv or not rv.get('text'):
            continue
        best = rv
        if not _is_dup(rv['text']):
            return rv
    return best


def _ai_unique_text(prompt, max_tokens, attempts=4, parser=None, temp_step=0.06):
    """مثل _ai_unique_json لكن يرجع نصاً مفرداً (يدعم parser مخصص مثل parse_ai_reply)."""
    parser = parser or (lambda out: ((extract_json(out) or {}).get('text', '') if out else ''))
    best = ''
    for k in range(attempts):
        hint = '' if k == 0 else (
            f'\n\n⚠️ المحاولة {k+1}: الرد السابق مكرر — غيّر الصياغة والبداية والكلمات كلياً.')
        out = _ai_call(prompt + hint, max_tokens=max_tokens,
                       temperature=min(1.0, AI_TEMPERATURE + k * temp_step))
        text = (parser(out) or '').strip()
        if not text:
            continue
        best = text
        if not _is_dup(text):
            return text
    return best


def _ai_write_json(prompt, max_tokens, attempts=5):
    """يكتب عبر AI فقط (لا قوالب). يرجع dict أو يرفع AIUnavailable عند تعذّر الـ AI.

    إن عاد الـ AI بنص (حتى لو قريب من سابق) نقبله كأفضل جهد للتفرّد.
    None تعني انقطاع الربط أو نفاد الرصيد → نتوقف ولا نكتب.
    """
    rv = _ai_unique_json(prompt, max_tokens=max_tokens, attempts=attempts)
    if not rv or not rv.get('text'):
        # قانون 4: عند تعذّر الـ AI (انقطاع/نفاد رصيد) نتوقّف ولا نفبرك تقييمًا.
        # المستدعون ومعالجات except AIUnavailable يترجمونه إلى 503 عبر _ai_unavailable_response().
        raise AIUnavailable('AI returned no usable review — stopping (no fabricated fallback, Law 4)')
    return rv


def _used_texts_block(limit=30, persona_name=None):
    """كتلة آخر النصوص المستخدمة (لمنع التكرار) — موحّدة لكل المسارات."""
    if USE_ANTI_REPEAT:
        return format_used_texts_block(limit=limit, persona_name=persona_name)
    used = _get_used_texts(_load_archive(), limit=limit + 10)
    return '\n'.join(f'- {t}' for t in used[-limit:]) if used else ''


def _plan_review(persona, pf, perfumes, used_block):
    """مرحلة (التفكير): يبني البرومبت ويحدّد النمط والتوجيه الاستراتيجي — بلا استدعاء AI.

    يرجع (prompt, params) ليتمكّن المسار اللحظي من عرض «ماذا سيكتب ولماذا» قبل الكتابة.
    """
    cross = _build_cross_sell(pf['name'], perfumes)
    
    context_hints = []
    
    ptype = pf.get('product_type', 'عطر')
    if ptype == 'مكياج':
        context_hints.append("هذا المنتج عبارة عن مكياج/أدوات تجميل (ليس عطراً). تحدث عن اللون، التغطية، الثبات، أو الملمس، ولا تستخدم كلمات عطرية مثل 'فوحان' أو 'ريحة'.")
    elif ptype == 'معطر_شعر':
        context_hints.append("هذا المنتج عطر مخصص للشعر. تحدث عن تأثيره على الشعر (ما ينشفه، ريحته تفوح مع الحركة)، ولا تتعامل معه كعطر جسم عادي.")
    elif ptype == 'معطر_جسم':
        context_hints.append("هذا معطر جسم (Body Mist)، ركز على الانتعاش والترطيب وخفة الريحة بعد الشاور.")
    elif ptype == 'بخور':
        context_hints.append("هذا بخور/عود. استخدم مصطلحات مثل 'الكسرة'، 'الدخان'، 'التبخير'، 'يمسك في الثياب/المجلس'.")
    elif ptype == 'عناية_جسم':
        context_hints.append("هذا منتج عناية بالجسم. ركز على الترطيب والنعومة وسرعة الامتصاص.")

    # Gift matching
    is_gift_male = persona.get('id', persona.get('archId')) == 'هدايا_رجل'
    is_gift_female = persona.get('id', persona.get('archId')) == 'هدايا_أنثى'
    
    if is_gift_male and (pf.get('g') == 'نسائي' or ptype == 'مكياج'):
        context_hints.append("مهم جداً: أنت رجل واشتريت هذا المنتج كهدية (لزوجتك/أمك/أختك). تحدث عن إعجابها بالهدية وردة فعلها، ولا تتحدث كأنك تستخدمه شخصياً!")
    elif is_gift_female and pf.get('g') == 'رجالي':
        context_hints.append("مهم جداً: أنتِ امرأة واشتريتِ هذا المنتج كهدية (لزوجك/أخوكِ/أبوكِ). تحدثي عن فخامة الهدية وكيف عجبته، ولا تتحدثي كأنكِ تستخدمينه شخصياً!")

    # توجيه واعٍ بطبيعة العطر (مناسبته/ثقله) — يجعل التقييم يطابق الاستخدام الحقيقي
    if USE_DEMO_MATCH and not (is_gift_male or is_gift_female):
        _dir = _demo.review_directive(persona, pf)
        if _dir:
            context_hints.append(_dir)

    if context_hints:
        cross += "\n\n## تنبيهات سياقية (التزم بها بحذافيرها):\n- " + "\n- ".join(context_hints)

    return _make_master_prompt(persona, pf['name'], used_block, extra_block=cross)


def _write_review(persona, pf, prompt, params):
    """مرحلة (الكتابة): الـ AI فقط يكتب — لا قوالب احتياطية.

    يرفع AIUnavailable إذا تعذّر الـ AI (انقطاع/نفاد رصيد) فيتوقف التوليد.
    يسجّل النص في طبقة الجلسة لمنع أي تكرار لاحق.
    """
    # سقف توكنز مرتبط بطول النمط — يمنع الإطناب فيزيائياً (يكفي JSON + النص)
    mx = 20
    if USE_PATTERNS:
        mx = REVIEW_PATTERNS.get(params.get('pattern', ''), {}).get('words', (1, 20))[1]
    max_tokens = 80 + mx * 8
    rv = _ai_write_json(prompt, max_tokens=max_tokens, attempts=5)  # يرفع AIUnavailable عند الفشل
    # ══ الحارس الدلالي: نزيف/بتر/تجاوز طول → إعادة توليد بدل القصّ الصامت ══
    if USE_SEMANTIC_GUARD:
        for _k in range(2):
            _t = _humanize(rv.get('text', ''))
            _viol = guard_violations(_t, max_words=4)
            if not _viol:
                break
            _hint = (f'\n\n⚠️ رُفض النص السابق «{_t}» ({"، ".join(_viol)}). '
                     'اكتب تقييماً جديداً عن العطر نفسه فقط، جملة مكتملة المعنى، ٤ كلمات كحد أقصى.')
            _nxt = _ai_unique_json(prompt + _hint, max_tokens=max_tokens, attempts=2)
            if _nxt and _nxt.get('text'):
                rv['text'] = _nxt['text']
            else:
                break
    rv['price'] = pf['price']
    rv['brand'] = pf['brand']
    rv['pg'] = pf['g']
    rv['product'] = pf['name']
    rv['pattern'] = params.get('pattern', '')
    # أخطاء إملائية طبيعية (تزيد التفرّد ولا تنقصه)
    if USE_DIALECTS and persona.get('has_typo', False):
        rv['text'] = apply_typos(rv['text'], probability=1.0)
    # تنظيف نهائي: نص بشري متدفّق بلا ترقيم أو رموز (ضمان مطلق)
    rv['text'] = _humanize(rv.get('text', ''))
    # ══ قص أخير: 4 كلمات بحد أقصى + إنقاذ الذيل المبتور (لا شظايا) ══
    _words = rv['text'].split()
    if len(_words) > 4:
        _words = _words[:4]
    if USE_SEMANTIC_GUARD:
        _words = strip_broken_tail(_words)
    rv['text'] = ' '.join(_words)

    if USE_AR_TRACK:
        ar_track_pattern(params.get('pattern', 'default'))
    _register(rv.get('text', ''))
    return rv


def _ai_reviews(persona, perfumes):
    """توليد تقييمات AI فريدة لكل عطر — يفكّر ثم يكتب (دفعة واحدة)."""
    used_block = _used_texts_block(limit=30, persona_name=persona.get('name'))
    all_reviews = []
    for pf in perfumes:
        prompt, params = _plan_review(persona, pf, perfumes, used_block)
        all_reviews.append(_write_review(persona, pf, prompt, params))
    # حفظ في الأرشيف
    _archive_batch(all_reviews, persona.get('name', ''))
    return all_reviews

def _ai_single_review(persona, product):
    """توليد تقييم واحد بالـ AI فقط — يرفع AIUnavailable عند تعذّر الـ AI."""
    used_block = _used_texts_block(limit=15, persona_name=persona.get('name'))
    prompt, params = _make_master_prompt(persona, product['name'], used_block)
    rv = _write_review(persona, product, prompt, params)
    _archive_review(rv.get('text', ''), product['name'], persona.get('name', ''))
    return rv

# جوانب متجر متنوّعة — يُختار منها جانبان عشوائياً لكل تقييم لمنع التكرار
STORE_ASPECTS = [
    'سرعة التوصيل — وصل قبل الموعد', 'فخامة التغليف — فقاعات وكرتون مزدوج', 
    'أصالة العطور 100%', 'خدمة العملاء — ردوا علي بسرعة',
    'الأسعار — أرخص من المحلات', 'سهولة الطلب والدفع', 
    'العينات المجانية — جاني عينات مع الطلب', 'الكرت الشخصي مع الطلب', 
    'التغليف المحمي ضد الكسر', 'التقسيط — تابي وتمارا بدون فوائد',
    'تتبع الطلب — كل خطوة واضحة'
]
# أساليب بداية متنوّعة لتقييم المتجر (تمنع تكرار صيغة الافتتاح)
STORE_OPENERS = [
    'ابدأ بانطباعك المباشر عن تجربة الشراء',
    'ابدأ بذكر آخر طلب وصلك وكيف كان',
    'ابدأ بمقارنة بسيطة مع متاجر ثانية تعاملت معها',
    'ابدأ بردة فعلك أول ما فتحت الطلب',
    'ابدأ بنصيحة لغيرك يطلب من المتجر',
]


# نداءات عامّية مقصورة — تُحذف حتميًّا بعد «يا» فقط (لا نمط عام)،
# فتبقى «يا سلام/يا رب/يا ليت/يا هلا» سليمة لأنها أصيلة وليست نداءً لشخص.
_STORE_VOCATIVES = ['صاحبي', 'خوي', 'ربع', 'شيخ', 'جماعة', 'حلفي',
                    'رجال', 'حبيبتي', 'ناس', 'صاح', 'ولد']
_STORE_VOCATIVE_RE = re.compile(
    r'يا\s+(?:' + '|'.join(_STORE_VOCATIVES) + r')(?![ء-ي])')


def _strip_store_vocatives(text, persona_name):
    """حذف حتمي لنداء الاسم من مخرج المتجر: «يا <اسم معروف>» و«يا أبو/أم <كلمة>»
    و«يا <نداء عامّي من قائمة مقصورة>». محصور في names.json + اسم الشخصية + القائمة
    حتى لا يمسّ «يا سلام/يا رب/يا ليت/يا هلا»."""
    names = set(NAMES.get('male', []) + NAMES.get('female', []) + NAMES.get('family_names', []))
    parts = (persona_name or '').split()
    if parts:
        names.add(parts[0])
    for nm in names:
        text = re.sub(r'يا\s+' + re.escape(nm) + r'(?![ء-ي])', ' ', text)
    text = re.sub(r'يا\s+(?:أبو|أم)\s+\S+', ' ', text)
    text = _STORE_VOCATIVE_RE.sub(' ', text)  # نداءات عامّية مقصورة (يا صاحبي/يا ربع/يا رجال...)
    return re.sub(r'\s+', ' ', text).strip()


# ═══════════════════════════════════════════════════════════
# تنوّع تقييم المتجر: طول مُعايَن + سقف موضوعي عبر الجلسة
# ═══════════════════════════════════════════════════════════

# ── هدف طول مُعايَن لكل تقييم (يطابق توزيع العملاء الحقيقي) ──
# 35% قصير جدًا · 40% قصير · 25% متوسط — يُعيَّن عشوائيًّا قبل البرومبت ويُحقن نصًّا،
# فيكسر رتابة «القصة من 8-16 كلمة» التي كانت تُنتج تقييمات متشابهة الطول.
_LENGTH_BANDS = [
    (0.35, (2, 5),   'قصير جدًا — من كلمتين إلى خمس كلمات فقط، انطباع خاطف بلا قصة'),
    (0.40, (6, 10),  'قصير — من ست إلى عشر كلمات، جملة أو جملتين'),
    (0.25, (11, 18), 'متوسط — من إحدى عشرة إلى ثماني عشرة كلمة، قصة مصغّرة'),
]


def _sample_length_target():
    """يعيّن نطاق طول عشوائيًّا وفق التوزيع الحقيقي — يرجع (min, max, وصف نصّي)."""
    r = random.random()
    cum = 0.0
    for prob, (lo, hi), desc in _LENGTH_BANDS:
        cum += prob
        if r <= cum:
            return lo, hi, desc
    _, (lo, hi), desc = _LENGTH_BANDS[-1]
    return lo, hi, desc


# ── سقف موضوعي عبر الجلسة: لا موضوع يتجاوز 20% من تقييمات المتجر ──
# يقتل «هوس التغليف» حتى لو نجا من إزالة المثال الذهبي: كل تقييم يُصنَّف بموضوعه
# الغالب، والمواضيع المشبعة تُستبعد من اختيار الجوانب وتُرفض إن كتبها النموذج تلقائيًّا.
STORE_TOPICS = ('تغليف', 'سعر', 'سرعة', 'خدمة', 'عينات', 'تقسيط', 'أصالة')

# كل جانب متجر → موضوعه (لتوجيه اختيار الجوانب بعيدًا عن المشبع)
_ASPECT_TOPIC = {
    'سرعة التوصيل — وصل قبل الموعد': 'سرعة',
    'فخامة التغليف — فقاعات وكرتون مزدوج': 'تغليف',
    'أصالة العطور 100%': 'أصالة',
    'خدمة العملاء — ردوا علي بسرعة': 'خدمة',
    'الأسعار — أرخص من المحلات': 'سعر',
    'سهولة الطلب والدفع': 'خدمة',
    'العينات المجانية — جاني عينات مع الطلب': 'عينات',
    'الكرت الشخصي مع الطلب': 'عينات',
    'التغليف المحمي ضد الكسر': 'تغليف',
    'التقسيط — تابي وتمارا بدون فوائد': 'تقسيط',
    'تتبع الطلب — كل خطوة واضحة': 'سرعة',
}

# كلمات دالّة على كل موضوع — لتصنيف النص المولّد فعليًّا (لا الجوانب المطلوبة فقط)
_TOPIC_KEYWORDS = {
    'تغليف': ['تغليف', 'مغلف', 'مغلّف', 'غلاف', 'كرتون', 'علبة', 'فقاعات', 'يغلف', 'تغليفة'],
    'سعر':   ['سعر', 'أسعار', 'اسعار', 'رخيص', 'أرخص', 'ارخص', 'خصم', 'وفرت', 'وفر', 'توفير', 'ريال', 'الأرخص'],
    'سرعة':  ['توصيل', 'وصل', 'سريع', 'بسرعة', 'يوصل', 'شحن', 'تتبع', 'يومين', 'الموعد', 'وصلني', 'وصلت'],
    'خدمة':  ['خدمة', 'ردوا', 'ردو', 'تواصل', 'واتساب', 'اهتمام', 'يهتمون', 'نصحوني', 'استفسار', 'ردهم'],
    'عينات': ['عينة', 'عينات', 'كرت', 'بطاقة', 'هدية'],
    'تقسيط': ['تقسيط', 'تابي', 'تمارا', 'أقساط', 'اقساط', 'قسط'],
    'أصالة': ['أصلي', 'أصلية', 'اصلي', 'اصلية', 'أصالة', 'باركود', 'سيريال', 'موثوق', 'مضمون'],
}

# ── حظر استعارات الفخامة (كنز/صندوق/مجوهرات/ذهب...) ──
# «هوس التغليف» كان يجرّ النموذج لتشبيه الطلب بصندوق كنوز أو مجوهرات أو ذهب.
# هذه الكلمات لا ترد أصلاً في تقييم متجر عطور واقعي، فحظرها آمن ويضمن «صفر استعارة كنز».
_LUXURY_NOUNS = ['كنوز', 'كنز', 'صناديق', 'صندوق', 'مجوهرات', 'جوهرة', 'جواهر',
                 'ألماس', 'الماس', 'لؤلؤ', 'ذهب', 'ذهبية']
# أدوات التشبيه التي تسبق الاستعارة عادةً — تُحذف معها لتبقى الجملة سليمة
_SIMILE_PARTICLES = {'كأنه', 'كأني', 'كأنها', 'كأنك', 'كأن', 'كنه', 'كنها', 'مثل', 'زي',
                     'تحفة', 'فاتح', 'فاتحة', 'فتحت', 'شاري', 'شارية', 'حماية', 'كنز', 'صندوق'}
# سابقة اختيارية (ال/بال/كال/لل/ب/ك/ل/و/ف) + الكلمة + حدّ عربي على الطرفين
_LUXURY_RE = re.compile(
    r'(?<![ء-ي])(?:وال|بال|كال|فال|ال|لل|ب|ك|ل|و|ف)?(?:' + '|'.join(_LUXURY_NOUNS) + r')(?![ء-ي])')


def _has_luxury_metaphor(text):
    """هل النص فيه كلمة استعارة فخامة محظورة؟"""
    return bool(_LUXURY_RE.search(text))


def _scrub_luxury_metaphor(text):
    """ضمان حتمي: يزيل كل كلمة استعارة فخامة + أداة التشبيه التي تسبقها.
    شبكة أمان أخيرة إن نجت الاستعارة من إعادة التوليد — تضمن صفر «كنز/صندوق/مجوهرات»."""
    if not _LUXURY_RE.search(text):
        return text
    keep = []
    for w in text.split():
        if _LUXURY_RE.search(w):
            while keep and keep[-1] in _SIMILE_PARTICLES:
                keep.pop()
            continue
        keep.append(w)
    return re.sub(r'\s+', ' ', ' '.join(keep)).strip()


_STORE_TOPIC_COUNTS = {t: 0 for t in STORE_TOPICS}
_STORE_TOPIC_TOTAL = 0
_TOPIC_CAP = 0.20   # لا موضوع يتجاوز 20% من تقييمات المتجر في الجلسة
_TOPIC_FLOOR = 5    # لا تُفعَّل النسبة قبل تجميع 5 تقييمات (تفادي تقييد مبكر)


def _classify_store_topic(text):
    """الموضوع الغالب لنص تقييم المتجر (أكثر المواضيع تطابقًا للكلمات الدالّة).
    عند تعادل التطابق (نص يلمّح لموضوعين، مثل «طلبية وصلتني جاني عينات») يُرجَّح
    الموضوع الأقل استخدامًا في الجلسة — يوازن التوزيع ويخدم سقف 20%.
    يرجع None لو لم يُطابق أي موضوع — فالتقييمات العامّة لا تُحسب ضد أي سقف."""
    scored = []
    for topic in STORE_TOPICS:
        hits = sum(text.count(kw) for kw in _TOPIC_KEYWORDS[topic])
        if hits:
            # (أكثر تطابقًا أولًا، ثم الأقل استخدامًا، ثم ترتيب ثابت)
            scored.append((-hits, _STORE_TOPIC_COUNTS.get(topic, 0), STORE_TOPICS.index(topic), topic))
    if not scored:
        return None
    scored.sort()
    return scored[0][3]


def _store_blocked_topics():
    """المواضيع المشبعة (بلغ نصيبها ≥20%) — تُستبعد حتى ينخفض نصيبها بنمو المقام."""
    if _STORE_TOPIC_TOTAL < _TOPIC_FLOOR:
        return set()
    return {t for t in STORE_TOPICS
            if _STORE_TOPIC_COUNTS[t] / _STORE_TOPIC_TOTAL >= _TOPIC_CAP}


def _record_store_topic(text):
    """يسجّل موضوع تقييم المتجر النهائي في عدّاد الجلسة — يرجع الموضوع المصنَّف."""
    global _STORE_TOPIC_TOTAL
    topic = _classify_store_topic(text)
    _STORE_TOPIC_TOTAL += 1
    if topic:
        _STORE_TOPIC_COUNTS[topic] += 1
    return topic


def _reset_store_topics():
    """تصفير عدّاد المواضيع (للاختبار أو بدء جلسة نظيفة)."""
    global _STORE_TOPIC_TOTAL
    for t in STORE_TOPICS:
        _STORE_TOPIC_COUNTS[t] = 0
    _STORE_TOPIC_TOTAL = 0


def _store_prompt(persona, band, aspects, opener, used_block, avoid_line, ban_line):
    """يبني برومبت المتجر مُكيّفًا مع نطاق الطول — القصير جدًّا يُسقط القصّة والافتتاحية
    والجانب الثاني (لأنها تجرّ النموذج للإطالة)، والمتوسط وحده يسمح بالقصّة المصغّرة."""
    who = (f"أنت العميل نفسه ({persona['label']}، عمره {persona['age']}، "
           f"من {persona['city']}) تكتب بصيغة المتكلّم عن تجربتك.")
    common = (f"- بلهجة سعودية عفوية بدون ترقيم ولا أرقام\n"
              f"- لا تُخاطب أحدًا بالاسم ولا تستعمل نداءً («يا فلان» أو «يا صاحبي» أو «يا ربع»)، ولا تذكر اسمك\n"
              f"{ban_line}{avoid_line}\n"
              f"- لا تكرر هذه الصياغات:\n{used_block if used_block else '(لا يوجد سابق)'}\n"
              f'أرجع JSON فقط: {{"rating": 5, "text": "..."}}')
    if band == 'vshort':      # 2-5 كلمات
        return (f'اكتب انطباعًا خاطفًا جدًّا عن متجر "مهووس للعطور" — من كلمتين إلى خمس كلمات فقط.\n'
                f'{who}\n'
                f'جملة واحدة قصيرة جدًّا عن: {aspects[0]}. بلا قصة وبلا مقدمات وبلا تفاصيل إضافية.\n'
                f'{common}')
    if band == 'short':       # 6-10 كلمات
        return (f'اكتب تقييمًا قصيرًا (من ست إلى عشر كلمات) لمتجر "مهووس للعطور" بلهجة سعودية عامية.\n'
                f'{who}\n'
                f'ركّز على: {aspects[0]}. جملة أو جملتين فقط بلا إطالة.\n'
                f'{common}')
    # story (11-18 كلمات)
    return (f'اكتب تقييمًا (من إحدى عشرة إلى ثماني عشرة كلمة، لا أكثر) لمتجر "مهووس للعطور" بلهجة سعودية عامية.\n'
            f'{who}\n'
            f'ركّز على هذين الجانبين: {aspects[0]} و{aspects[1]}.\n'
            f'- {opener}\n'
            f'- احكِ تجربتك كأنك تحكي لصاحبك، واذكر تفصيلة واحدة محددة\n'
            f'{common}')


def _ai_store_review(persona):
    """تقييم متجر متنوّع: طول مُعايَن + جوانب موزونة بالموضوع + سقف 20% لكل موضوع + حظر استعارات الفخامة.

    لا يُحقن مثال ذهبي (كان يُسحب كله من story_type واحد فيوحّد المخرج ويطبع القالب الطويل)؛
    STORE_ASPECTS المتنوّعة + الشخصية + سقف الموضوع + طول مُعايَن هي ما يقود التنوّع.
    """
    # (1) هدف الطول — يُعيَّن قبل البرومبت (35% قصير جدًا · 40% قصير · 25% متوسط)
    lo, hi, length_desc = _sample_length_target()
    band = 'vshort' if hi <= 5 else ('short' if hi <= 10 else 'story')
    # (2) اختيار الجوانب بعيدًا عن المواضيع المشبعة (≥20%)
    blocked = _store_blocked_topics()
    pool = [a for a in STORE_ASPECTS if _ASPECT_TOPIC.get(a) not in blocked]
    if len(pool) < 2:
        pool = list(STORE_ASPECTS)
    aspects = random.sample(pool, k=2)
    opener = random.choice(STORE_OPENERS)
    used_block = _used_texts_block(limit=15, persona_name=persona.get('name'))
    avoid_line = (f"\n- ممنوع الحديث عن: {'، '.join(sorted(blocked))} (تكرّرت كثيرًا)" if blocked else '')
    ban_line = ("- تكلّم بواقعية: ممنوع تشبيه العطر أو الطلب أو التغليف بالكنز أو الصندوق "
                "أو المجوهرات أو الجوهرة أو الذهب أو الألماس أو التحفة")

    prompt = _store_prompt(persona, band, aspects, opener, used_block, avoid_line, ban_line)
    rv = _ai_write_json(prompt, max_tokens=200, attempts=5)  # يرفع AIUnavailable عند الفشل

    def _finalize(text):
        text = _humanize(text)  # بلا ترقيم أو رموز
        text = re.sub(r'\s+', ' ', re.sub(r'[0-9٠-٩]+', ' ', text)).strip()  # صفر أرقام (مسار المتجر)
        return _strip_store_vocatives(text, persona.get('name'))  # منع النداء حتميًّا

    text = _finalize(rv.get('text', ''))

    # (3) حارس موحّد: استعارة فخامة / موضوع مشبع / تجاوز الطول → إعادة توليد موجَّهة
    for _k in range(3):
        problems = []
        if _has_luxury_metaphor(text):
            problems.append('استعارة فخامة (كنز/صندوق/مجوهرات/ذهب) ممنوعة')
        blocked_now = _store_blocked_topics()
        if _STORE_TOPIC_TOTAL >= _TOPIC_FLOOR and _classify_store_topic(text) in blocked_now:
            fresh = [a for a in STORE_ASPECTS if _ASPECT_TOPIC.get(a) not in blocked_now]
            alt = random.choice(fresh or STORE_ASPECTS)
            problems.append(f"موضوع «{_classify_store_topic(text)}» تكرّر كثيرًا؛ اكتب عن {alt} بدلًا منه ولا تذكره")
        if len(text.split()) > hi + 2:
            problems.append(f"أطل من المطلوب؛ التزم بـ {length_desc}")
        if not problems:
            break
        hint = "\n\n⚠️ أعد الكتابة: " + " · ".join(problems)
        nxt = _ai_unique_json(prompt + hint, max_tokens=200, attempts=2)
        if not (nxt and nxt.get('text')):
            break
        text = _finalize(nxt['text'])

    # (4) ضمانات حتمية: صفر استعارة فخامة + احترام سقف نطاق الطول (كما يقصّ مسار المنتج)
    text = _scrub_luxury_metaphor(text)
    words = text.split()
    if len(words) > hi:
        words = words[:hi]
        if USE_SEMANTIC_GUARD:
            words = strip_broken_tail(words)
    text = ' '.join(words)
    rv['text'] = text

    # (5) تسجيل الموضوع النهائي في عدّاد الجلسة (بعد التثبيت)
    _record_store_topic(text)

    _register(text)
    if USE_ANTI_REPEAT:
        try:
            ar_archive_review(text, 'متجر مهووس', persona.get('name', ''))
        except Exception:
            pass
    return rv

# ملاحظة: لا توجد كتابة احتياطية بالقوالب — الـ AI وحده يكتب.
# عند تعذّر الـ AI (انقطاع/نفاد رصيد) يرفع _ai_write_json استثناء AIUnavailable
# فتتوقف الكتابة وتُرجع الواجهة رسالة خطأ بدل عرض نص قالب.
# (بنوك النصوص مثل real_reviews_bank/short_texts_bank تبقى مراجع أسلوبية تُحقن
#  في البرومبت ليتعلّم منها النموذج فقط — لا تُعرض كتقييمات.)

# ═══════════ الشخصيات ═══════════
ARCHETYPES = [
    {'id':'شاب_جامعي','g':'male','label':'شاب جامعي','emoji':'🎓','age':(18,23),
     'price':(0,300),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'رجل_أعمال','g':'male','label':'رجل أعمال','emoji':'👔','age':(30,50),
     'price':(400,2000),'prefers':['رجالي','مشترك'],'count':(3,6)},
    {'id':'خبير_عطور','g':'male','label':'خبير عطور','emoji':'🧪','age':(25,40),
     'price':(200,2000),'prefers':['رجالي','مشترك'],'count':(3,7)},
    {'id':'أب_عائلة','g':'male','label':'أب عائلة','emoji':'👨‍👧','age':(35,55),
     'price':(100,500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'شاب_رياضي','g':'male','label':'شاب رياضي','emoji':'💪','age':(20,30),
     'price':(100,400),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'كبير_سن','g':'male','label':'رجل كبير','emoji':'👴','age':(55,75),
     'price':(100,600),'prefers':['رجالي','مشترك'],'count':(2,3)},
    {'id':'موظف','g':'male','label':'موظف','emoji':'🏢','age':(25,45),
     'price':(150,500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'بنت_عصرية','g':'female','label':'بنت عصرية','emoji':'💅','age':(20,28),
     'price':(100,600),'prefers':['نسائي','مشترك'],'count':(3,6)},
    {'id':'أم_سعودية','g':'female','label':'أم سعودية','emoji':'👩‍🦱','age':(38,55),
     'price':(100,800),'prefers':['نسائي','مشترك'],'count':(2,5)},
    {'id':'عروس','g':'female','label':'عروس','emoji':'👰','age':(21,30),
     'price':(300,2000),'prefers':['نسائي','مشترك'],'count':(4,8)},
    {'id':'موظفة','g':'female','label':'موظفة','emoji':'👩‍💻','age':(24,40),
     'price':(150,600),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'خبيرة_تجميل','g':'female','label':'خبيرة تجميل','emoji':'💄','age':(25,38),
     'price':(200,1000),'prefers':['نسائي','مشترك'],'count':(3,6)},
    {'id':'طالبة','g':'female','label':'طالبة جامعية','emoji':'📚','age':(18,23),
     'price':(0,250),'prefers':['نسائي','مشترك'],'count':(2,3)},
    {'id':'جدة','g':'female','label':'سيدة كبيرة','emoji':'👵','age':(55,75),
     'price':(100,500),'prefers':['نسائي','مشترك'],'count':(2,3)},
    {'id':'مقارن','g':'male','label':'مقارن أسعار','emoji':'📊','age':(25,40),
     'price':(100,600),'prefers':['رجالي','مشترك'],'count':(3,5)},
    {'id':'هدايا_رجل','g':'male','label':'يشتري هدايا','emoji':'🎁','age':(25,45),
     'price':(200,1000),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'هدايا_أنثى','g':'female','label':'تشتري هدايا','emoji':'🎀','age':(22,45),
     'price':(200,800),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'محب_تسوق','g':'male','label':'محب تسوق','emoji':'🛍️','age':(22,35),
     'price':(100,800),'prefers':['رجالي','مشترك'],'count':(3,6)},
    {'id':'محبة_تسوق','g':'female','label':'محبة تسوق','emoji':'👛','age':(22,35),
     'price':(100,800),'prefers':['نسائي','مشترك'],'count':(3,6)},
    # ── شخصيات إضافية (توسعة) — يجب أن تطابق personas_engine.ARCHETYPES ──
    {'id':'مبتعث','g':'male','label':'شاب مبتعث','emoji':'✈️','age':(22,30),
     'price':(150,900),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'عسكري','g':'male','label':'منسوب عسكري','emoji':'🎖️','age':(24,45),
     'price':(150,600),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'معلم','g':'male','label':'معلم','emoji':'🧑‍🏫','age':(28,50),
     'price':(150,500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'مهندس','g':'male','label':'مهندس','emoji':'👷','age':(26,45),
     'price':(200,800),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'طبيب','g':'male','label':'طبيب','emoji':'🩺','age':(30,52),
     'price':(300,1500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'متذوق_نيش','g':'male','label':'متذوق نيش','emoji':'🌿','age':(25,45),
     'price':(400,3000),'prefers':['رجالي','مشترك'],'count':(3,6)},
    {'id':'عامل_مقتصد','g':'male','label':'يدوّر العملي','emoji':'🧰','age':(25,50),
     'price':(0,180),'prefers':['رجالي','مشترك'],'count':(2,3)},
    {'id':'وجيه','g':'male','label':'وجيه ومحب عود','emoji':'🕌','age':(45,70),
     'price':(300,2000),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'بدوي','g':'male','label':'محب البخور والعود','emoji':'🐪','age':(30,60),
     'price':(100,800),'prefers':['رجالي','مشترك'],'count':(2,3)},
    {'id':'مؤثرة','g':'female','label':'مؤثرة عطور','emoji':'📸','age':(22,35),
     'price':(200,1500),'prefers':['نسائي','مشترك'],'count':(3,6)},
    {'id':'معلمة','g':'female','label':'معلمة','emoji':'👩‍🏫','age':(28,50),
     'price':(150,500),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'طبيبة','g':'female','label':'طبيبة','emoji':'👩‍⚕️','age':(30,50),
     'price':(300,1200),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'متذوقة_نيش','g':'female','label':'متذوقة نيش','emoji':'🌸','age':(25,45),
     'price':(400,2500),'prefers':['نسائي','مشترك'],'count':(3,5)},
    {'id':'ست_بيت','g':'female','label':'ست بيت','emoji':'🏠','age':(30,55),
     'price':(80,400),'prefers':['نسائي','مشترك'],'count':(2,4)},
    # ── الطبقة 7 — يجب أن تطابق personas_engine.ARCHETYPES (مصيدة #1) ──
    {'id':'كسول','g':'male','label':'كسول ما يحب يكتب','emoji':'😑','age':(18,55),
     'price':(0,999),'prefers':['رجالي','مشترك'],'count':(1,1)},
    {'id':'كسولة','g':'female','label':'كسولة ما تحب تكتب','emoji':'😑','age':(18,55),
     'price':(0,999),'prefers':['نسائي','مشترك'],'count':(1,1)},
    {'id':'ناقد_صريح','g':'male','label':'ناقد يقول رأيه بصراحة','emoji':'🤨','age':(25,50),
     'price':(50,500),'prefers':['رجالي','مشترك'],'count':(1,3)},
    {'id':'ناقدة_صريحة','g':'female','label':'ناقدة تقول رأيها بصراحة','emoji':'🤨','age':(25,50),
     'price':(50,500),'prefers':['نسائي','مشترك'],'count':(1,3)},
    {'id':'متردد','g':'male','label':'متردد كان خايف واكتشف','emoji':'🤔','age':(20,40),
     'price':(30,300),'prefers':['رجالي','مشترك'],'count':(1,2)},
    {'id':'مترددة','g':'female','label':'مترددة كانت خايفة واكتشفت','emoji':'🤔','age':(20,40),
     'price':(30,300),'prefers':['نسائي','مشترك'],'count':(1,2)},
    {'id':'متذمر_لطيف','g':'male','label':'يشتكي من شي تافه ثم يمدح','emoji':'😂','age':(20,45),
     'price':(30,400),'prefers':['رجالي','مشترك'],'count':(1,2)},
    {'id':'متذمرة_لطيفة','g':'female','label':'تشتكي من شي تافه ثم تمدح','emoji':'😂','age':(20,45),
     'price':(30,400),'prefers':['نسائي','مشترك'],'count':(1,2)},
]

# ═══════════ الكتالوج الكامل من ملف المتجر ═══════════
with open(BASE_DIR / 'catalog.json', 'r', encoding='utf-8') as f:
    PRODUCTS = json.load(f)
# مصدر واحد للحقيقة: نُمرّر نفس القائمة لفهرس personas_engine بدل قراءة الملف مرتين
if USE_NEW_PERSONAS:
    try:
        pe_set_catalog(PRODUCTS)
    except Exception as _e:
        print(f'⚠️ set_catalog failed: {_e}')
print(f'📦 الكتالوج: {len(PRODUCTS)} منتج ({sum(1 for p in PRODUCTS if p["g"]=="رجالي")} رجالي | {sum(1 for p in PRODUCTS if p["g"]=="نسائي")} نسائي | {sum(1 for p in PRODUCTS if p["g"]=="مشترك")} مشترك)')

# ═══════════ براندات ترند — الأكثر مبيعاً في السعودية ═══════════
TRENDING_BRANDS = [
    'ديور','شانيل','توم فورد','لطافة','أرماني','بربري','كارولينا',
    'لانكوم','فرساتشي','جوتشي','جان بول','أمواج','نارسيسو',
    'بولغاري','كالفن','مونت بلانك','دولتشي','بوشرون','هوجو',
    'جيرلان','كريد','بيليونير','راشد','عساف','سوفاج','خمرة',
]

def _pick_products(arch):
    """اختيار عطور ذكية حسب الشخصية مع ترجيح الترند المتقدم"""
    pool = []
    is_gift_male = arch['id'] == 'هدايا_رجل'
    is_gift_female = arch['id'] == 'هدايا_أنثى'
    
    for p in PRODUCTS:
        if p['g'] not in arch['prefers']:
            continue
        
        ptype = p.get('product_type', 'عطر')
        # الذكور (غير الهدايا) لا يشترون مكياج أبداً
        if arch['g'] == 'male' and not is_gift_male and ptype in ['مكياج', 'معطر_شعر']:
            continue
            
        # الإناث (غير الهدايا) لا يشترين عطور رجالية أبداً
        if arch['g'] == 'female' and not is_gift_female and p['g'] == 'رجالي':
            continue
            
        if arch['price'][0] <= p['price'] <= arch['price'][1]:
            pool.append(p)
            
    if len(pool) < 3:
        pool = [p for p in PRODUCTS if p['g'] in arch['prefers']]
        # Re-apply strict type filters
        pool = [p for p in pool if not (arch['g'] == 'male' and not is_gift_male and p.get('product_type') in ['مكياج', 'معطر_شعر'])]
    if len(pool) < 3:
        pool = PRODUCTS[:]

    # فلتر المطابقة الديموغرافي: يهذّب المجمّع حسب (عمر/مناسبة/ثقل) الشخصية،
    # يرفض غير المنطقي (شيخ+حلويات، رياضي+عود ثقيل) ويعيد الترشيح. لا يُفرِّغ
    # المجمّع أبداً، ولا يمسّ حقن كربتك/الترند داخل blend_selection.
    if USE_DEMO_MATCH:
        pool = _demo.filter_pool(arch, pool)

    count = random.randint(*arch['count'])

    # خلطة "محلي" الذكية التلقائية: كربتك (أولوية قصوى) + أفضل 100 ترند + تمويه
    # مختلفة في كل سلة. تحترم pool المُفلتر (جنس/سعر/نوع) فلا تكسر التماسك.
    if USE_TRENDING:
        return blend_selection(PRODUCTS, pool, count, arch['prefers'])

    # شبكة أمان (بلا محرك الترند): ترجيح بسيط للبراندات الترند
    trend_lower = [b.lower() for b in TRENDING_BRANDS]
    weights = []
    for p in pool:
        brand = p.get('brand', '').lower()
        name = p.get('name', '').lower()
        is_trend = any(tb in brand or tb in name for tb in trend_lower)
        weights.append(3.0 if is_trend else 1.0)
    count = min(count, len(pool))
    selected, pool_copy, w_copy = [], list(pool), list(weights)
    for _ in range(count):
        if not pool_copy:
            break
        idx = random.choices(range(len(pool_copy)), weights=w_copy, k=1)[0]
        selected.append(pool_copy.pop(idx))
        w_copy.pop(idx)
    return selected

# ═══════════ الأسماء والمدن والعناوين ═══════════
def _name(g):
    key='male' if g=='male' else 'female'
    return random.choice(NAMES.get(key,['مستخدم']))+' '+random.choice(NAMES.get('family_names',['السعودي']))

def _city():
    cities=NAMES.get('cities',[{'name':'الرياض','weight':1}])
    return random.choices(cities,weights=[c.get('weight',1) for c in cities],k=1)[0]['name']

# ═══════════ عنوان وطني سعودي ═══════════
# مصدر واحد للحقيقة: personas_engine. يُستورد منه مباشرة لتفادي تكرار/تباعد القائمتين.
# الـ fallback المحلي يُستخدم فقط إذا تعذّر استيراد المحرك الجديد.
if USE_NEW_PERSONAS:
    from personas_engine import CITY_DATA, _make_address as _national_address
else:
    CITY_DATA = {
        'الرياض': {'districts': [('العليا', 'شارع العليا العام', '122'), ('النخيل', 'شارع الأمير محمد بن سعد', '123'),
            ('الملقا', 'طريق أنس بن مالك', '135'), ('الصحافة', 'طريق أبو بكر الصديق', '133')]},
        'جدة': {'districts': [('الحمراء', 'شارع فلسطين', '233'), ('الروضة', 'شارع الأمير سلطان', '234'),
            ('الشاطئ', 'طريق الكورنيش', '236')]},
        'الدمام': {'districts': [('الشاطئ', 'طريق الكورنيش', '324'), ('الفيصلية', 'شارع الملك فيصل', '322')]},
    }

    def _national_address(city_name):
        cdata = CITY_DATA.get(city_name, {'districts': [('المركز', 'الشارع العام', '114')]})
        dist, street, postal_prefix = random.choice(cdata['districts'])
        building = str(random.randint(2000, 9999))
        postal = f'{postal_prefix}{random.randint(0, 99):02d}'
        extra = str(random.randint(2000, 9999))
        return {
            'building': building, 'street': street, 'district': dist,
            'city': city_name, 'postal': postal, 'extra': extra,
            'short_code': ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(4)) + f'{random.randint(0,9999):04d}',
            'full': f'{building} {street}، حي {dist}، {city_name} {postal} - {extra}'
        }

# ═══════════ رقم جوال سعودي ═══════════
SAUDI_PREFIXES = ['050','053','054','055','056','057','058','059']
def _phone():
    return random.choice(SAUDI_PREFIXES) + ''.join([str(random.randint(0,9)) for _ in range(7)])

# ═══════════ توليد شخصية كاملة ═══════════
def _gen_one():
    """توليد شخصية كاملة — يستخدم المحرك الجديد إذا متوفر"""
    if USE_NEW_PERSONAS:
        # المحرك الجديد: شخصية عميقة بـ 7 أبعاد
        persona = generate_persona()
        arch = next((a for a in ARCHETYPES if a['id'] == persona['archId']), random.choice(ARCHETYPES))
    else:
        # المحرك القديم
        arch = random.choice(ARCHETYPES)
        age = random.randint(*arch['age'])
        city = _city()
        addr = _national_address(city)
        persona = {
            'name': _name(arch['g']), 'city': city, 'gender': arch['g'], 'age': age,
            'label': arch['label'], 'emoji': arch['emoji'], 'archId': arch['id'],
            'address': addr, 'phone': _phone()
        }

    perfumes = _pick_products(arch)
    reviews = _ai_reviews(persona, perfumes)
    store = _ai_store_review(persona)

    return {
        'persona': persona,
        'perfumes': perfumes,
        'reviews': reviews,
        'store': store
    }

@app.route('/')
def index(): return render_template('index.html')

@app.route('/health')
def health():
    """Railway health check — حالة المحركات والبيانات"""
    return jsonify({
        'status': 'ok',
        'engines': {
            'personas': USE_NEW_PERSONAS,
            'dialects': USE_DIALECTS,
            'patterns': USE_PATTERNS,
            'anti_repeat': USE_ANTI_REPEAT,
            'trending': USE_TRENDING,
            'intel': USE_INTEL,
            'rate_limit': USE_RATE_LIMIT,
        },
        'products': len(PRODUCTS),
        'archive': len(_load_archive().get('reviews', [])),
        'data_dir': str(DATA_DIR),
    })

def _ai_unavailable_response():
    """رد موحّد عند تعذّر الـ AI — التطبيق توقّف ولم يكتب أي قالب."""
    return jsonify({
        'error': 'ai_unavailable',
        'message': 'تعذّر الاتصال بالذكاء الاصطناعي أو نفد الرصيد — لم تتم كتابة أي تقييم.',
    }), 503

@app.route('/api/generate', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def generate():
    try:
        return jsonify(_gen_one())
    except AIUnavailable:
        return _ai_unavailable_response()

@app.route('/api/batch', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def batch():
    n = _safe_int((request.get_json(silent=True) or {}).get('count', 5), 5, 1, 20)
    try:
        results = [_gen_one() for _ in range(n)]
    except AIUnavailable:
        return _ai_unavailable_response()
    return jsonify({'results': results, 'count': n})

@app.route('/api/regen-review', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def regen_review():
    d = request.get_json(silent=True) or {}
    arch = next((a for a in ARCHETYPES if a['id']==d.get('archId','')), random.choice(ARCHETYPES))
    product = {'name':d.get('product',''),'price':d.get('price',0),'brand':d.get('brand',''),'g':d.get('pg','مشترك')}
    persona = _make_persona_for_arch(arch)
    try:
        rv = _ai_single_review(persona, product)
    except AIUnavailable:
        return _ai_unavailable_response()
    return jsonify(rv)

@app.route('/api/add-perfumes', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def add_perfumes():
    d = request.get_json(silent=True) or {}
    arch = next((a for a in ARCHETYPES if a['id']==d.get('archId','')), random.choice(ARCHETYPES))
    exclude = set(d.get('existing', []))
    pool = [p for p in PRODUCTS if p['g'] in arch['prefers'] and p['name'] not in exclude
            and arch['price'][0]<=p['price']<=arch['price'][1]]
    if not pool:
        pool = [p for p in PRODUCTS if p['g'] in arch['prefers'] and p['name'] not in exclude]
    if not pool:
        return jsonify({'perfumes':[],'reviews':[]})
    count = random.randint(1, min(3, len(pool)))
    perfumes = random.sample(pool, count)
    persona = _make_persona_for_arch(arch)
    try:
        reviews = _ai_reviews(persona, perfumes)
    except AIUnavailable:
        return _ai_unavailable_response()
    return jsonify({'perfumes': perfumes, 'reviews': reviews})

@app.route('/api/new-phone', methods=['POST'])
def new_phone():
    return jsonify({'phone': _phone()})


@app.route('/api/git-push', methods=['POST'])
def git_push():
    """رفع التعديلات إلى Railway عبر git push"""
    import subprocess
    try:
        cwd = os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
        subprocess.run(['git', 'add', '.'], cwd=cwd, check=True, capture_output=True, timeout=30)
        subprocess.run(['git', 'commit', '-m', 'auto update'], cwd=cwd, capture_output=True, timeout=30)
        result = subprocess.run(['git', 'push'], cwd=cwd, check=True, capture_output=True, timeout=60)
        return jsonify({'ok': True, 'msg': 'تم الرفع بنجاح'})
    except subprocess.CalledProcessError as e:
        return jsonify({'ok': False, 'error': e.stderr.decode('utf-8', errors='replace')[:200]}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500

@app.route('/api/archive', methods=['GET'])
def archive_stats():
    arc = _load_archive()
    return jsonify({
        'total_reviews': len(arc.get('reviews',[])),
        'last_10': [{'text':r['text'],'product':r.get('product',''),'persona':r.get('persona','')}
                    for r in arc.get('reviews',[])[-10:]]
    })

@app.route('/api/archive/stats', methods=['GET'])
def archive_stats_detail():
    """إحصائيات الأرشيف التفصيلية (العدد الحالي + الحد الأقصى)"""
    if USE_ANTI_REPEAT:
        try:
            return jsonify(ar_get_archive_stats())
        except Exception as e:
            print(f'⚠️ archive stats error: {e}')
    arc = _load_archive()
    return jsonify({'total': len(arc.get('reviews', [])), 'max': 200})

@app.route('/api/archive/clear', methods=['POST'])
def archive_clear():
    if USE_ANTI_REPEAT:
        ar_clear_archive()
    else:
        _save_archive({'reviews':[], 'store_reviews':[], 'personas':[]})
    return jsonify({'status':'ok','message':'تم مسح الأرشيف'})

# ═══════════════════════════════════════════════════════════
# API استخبارات محلي (Algolia Intelligence)
# ═══════════════════════════════════════════════════════════

@app.route('/api/intel/our-products', methods=['GET'])
def api_intel_products():
    """جلب منتجاتنا من Algolia"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    products = intel_get_our_products()
    return jsonify({'products': products, 'count': len(products)})

@app.route('/api/intel/competitors/<path:product_name>', methods=['GET'])
def api_intel_competitors(product_name):
    """جلب المنافسين لمنتج"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    competitors = intel_get_competitors(product_name)
    return jsonify({'competitors': competitors, 'count': len(competitors)})

@app.route('/api/intel/our-rank/<path:query>', methods=['GET'])
def api_intel_rank(query):
    """ترتيبنا لكلمة بحث"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    rank, product = intel_get_our_rank(query)
    return jsonify({'rank': rank, 'product': product, 'query': query})

@app.route('/api/intel/priorities', methods=['GET'])
def api_intel_priorities():
    """قائمة الأولويات"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    priorities = intel_get_priorities()
    return jsonify({'priorities': priorities})

@app.route('/api/intel/daily-plan', methods=['GET'])
def api_intel_daily():
    """خطة اليوم"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    plan = intel_daily_plan()
    return jsonify(plan)

@app.route('/api/intel/dashboard', methods=['GET'])
def api_intel_dashboard():
    """ملخص لوحة التحكم"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    summary = intel_dashboard()
    return jsonify(summary)

@app.route('/api/intel/refresh', methods=['POST'])
def api_intel_refresh():
    """تحديث البيانات من Algolia"""
    if not USE_INTEL:
        return jsonify({'error': 'mahalli_intel not available'}), 503
    result = intel_refresh()
    return jsonify(result)

# ═══════════════════════════════════════════════════════════
# SSE — مؤشر مباشر لعمل الـ API (Server-Sent Events)
# ═══════════════════════════════════════════════════════════

from flask import Response, stream_with_context

@app.route('/api/generate-stream', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def api_generate_stream():
    """توليد لحظي حقيقي: يختار العطور → يفكّر → يكتب أمام المستخدم خطوة بخطوة (SSE).

    خلافاً للنسخة القديمة (تولّد كل شيء ثم تعيد تمثيل الخطوات)، هنا كل حدث
    يُبثّ فور حدوثه فعلاً: استدعاء AI لكل عطر يتم داخل الحلقة ويُعرض ناتجه مباشرة.
    """
    def _sse(evt):
        return f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    def generate():
        try:
            # ── 1) اختيار الشخصية ──
            yield _sse({'step': 'persona', 'msg': 'يختار الشخصية المناسبة...', 'icon': '👤'})
            if USE_NEW_PERSONAS:
                persona = generate_persona()
                arch = next((a for a in ARCHETYPES if a['id'] == persona['archId']),
                            random.choice(ARCHETYPES))
            else:
                arch = random.choice(ARCHETYPES)
                city = _city()
                persona = {
                    'name': _name(arch['g']), 'city': city, 'gender': arch['g'],
                    'age': random.randint(*arch['age']), 'label': arch['label'],
                    'emoji': arch['emoji'], 'archId': arch['id'],
                    'address': _national_address(city), 'phone': _phone(),
                }
            yield _sse({'step': 'persona_done', 'icon': '✅',
                        'msg': f"الشخصية: {persona['name']} — {persona['label']} — {persona['city']}",
                        'persona': persona})

            # ── 2) اختيار العطور (منظّم: موزون بالترند وتفضيلات الشخصية ونطاق سعرها) ──
            yield _sse({'step': 'products', 'icon': '📦',
                        'msg': 'يختار عطوراً تناسب الشخصية (ترجيح ذكي لا عشوائي)...'})
            perfumes = _pick_products(arch)
            yield _sse({'step': 'products_done', 'icon': '✅',
                        'msg': f'اختار {len(perfumes)} عطور',
                        'perfumes': [{'name': p['name'], 'price': p['price'],
                                      'brand': p.get('brand', '')} for p in perfumes]})

            # ── 3) لكل عطر: يفكّر (نمط + توجيه استراتيجي) ثم يكتب لحظياً ──
            used_block = _used_texts_block(limit=30)
            reviews = []
            for i, pf in enumerate(perfumes, 1):
                # (أ) التفكير — يُبنى البرومبت ويُحدَّد النمط قبل الكتابة
                prompt, params = _plan_review(persona, pf, perfumes, used_block)
                pattern = params.get('pattern', '')
                directive = get_ai_directive(pattern) if USE_PATTERNS else ''
                desc = get_pattern_description(pattern) if USE_PATTERNS else ''
                yield _sse({'step': 'thinking', 'index': i, 'icon': '🧠',
                            'product': pf['name'],
                            'msg': f"يفكّر في «{pf['name']}» — النمط: {desc or pattern}",
                            'pattern': pattern, 'directive': directive[:160]})

                # (ب) الكتابة — استدعاء AI فعلي الآن وعرض الناتج مباشرة
                rv = _write_review(persona, pf, prompt, params)
                reviews.append(rv)
                yield _sse({'step': 'review', 'index': i, 'icon': '✍️',
                            'product': pf['name'],
                            'msg': f"كتب تقييم «{pf['name']}»",
                            'text': rv.get('text', ''), 'rating': rv.get('rating', 5),
                            'pattern': rv.get('pattern', pattern)})

            # حفظ الدفعة في الأرشيف (مرة واحدة بعد اكتمالها)
            _archive_batch(reviews, persona.get('name', ''))

            # ── 4) تقييم المتجر (متغيّر وغير مكرر) ──
            yield _sse({'step': 'store', 'icon': '🏪', 'msg': 'يكتب تقييماً عاماً للمتجر...'})
            store = _ai_store_review(persona)
            yield _sse({'step': 'store_done', 'icon': '✅', 'msg': 'كتب تقييم المتجر',
                        'text': store.get('text', ''), 'rating': store.get('rating', 5)})

            # ── 5) اكتمل — البيانات الكاملة للواجهة ──
            data = {'persona': persona, 'perfumes': perfumes,
                    'reviews': reviews, 'store': store}
            yield _sse({'step': 'done', 'icon': '🎉', 'msg': 'اكتمل التوليد!', 'data': data})

        except AIUnavailable:
            # تعذّر الـ AI (انقطاع/نفاد رصيد) — نتوقف ولا نكتب قوالب
            yield _sse({'step': 'error', 'icon': '🛑', 'fatal': True,
                        'msg': 'تعذّر الاتصال بالذكاء الاصطناعي أو نفد الرصيد — توقّفت الكتابة.'})
        except Exception as e:
            yield _sse({'step': 'error', 'msg': str(e), 'icon': '❌'})

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ═══════════════════════════════════════════════════════════
# Thread Generation — توليد محادثات (تقييم + ردود)
# ═══════════════════════════════════════════════════════════

@app.route('/api/generate-thread', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def api_generate_thread():
    """توليد محادثة: تقييم رئيسي + ردود من عملاء آخرين (الـ AI فقط)"""
    if not USE_THREADS:
        return jsonify({'error': 'thread_generator not available'}), 503

    body = request.get_json(silent=True) or {}
    product_name = body.get('product_name', '')
    main_review = body.get('main_review', '')

    if not product_name or not main_review:
        return jsonify({'error': 'product_name and main_review required'}), 400

    reply_count = _safe_int(body.get('reply_count', 2), 2, 1, 4)

    # بناء بيانات المحادثة (برومبتات فقط)
    thread_data = generate_thread_data(product_name, main_review, reply_count)

    # استدعاء الـ AI لكل رد — فريد لا يتكرر. عند تعذّر الـ AI نتوقف ولا نكتب قوالب.
    thread_replies = []
    for reply_info in thread_data['replies']:
        text = _ai_unique_text(reply_info['prompt'], max_tokens=150,
                               attempts=4, parser=parse_ai_reply)
        if not text:
            return _ai_unavailable_response()
        text = _humanize(text)  # بلا ترقيم أو رموز
        if not text:
            return _ai_unavailable_response()
        _register(text)
        thread_replies.append({
            'name': reply_info['persona'].get('name', 'عميل'),
            'city': reply_info['persona'].get('city', ''),
            'text': text,
            'type': reply_info['type'],
            'is_answer': reply_info.get('is_answer', False),
        })

    return jsonify({
        'thread_type': thread_data['thread_type'],
        'main_review': main_review,
        'product_name': product_name,
        'replies': thread_replies,
    })


if __name__ == '__main__':
    arc = _load_archive()
    print('='*50)
    print('Perfume Assistant V2 — AI Mode (Railway)')
    print(f'   DATA_DIR: {DATA_DIR}')
    print(f'   Products: {len(PRODUCTS)}')
    print(f'   Archive: {len(arc.get("reviews",[]))} reviews (max 200 FIFO)')
    print(f'   Engines: P={USE_NEW_PERSONAS} D={USE_DIALECTS} R={USE_PATTERNS}')
    print(f'            A={USE_ANTI_REPEAT} T={USE_TRENDING} I={USE_INTEL}')
    print(f'            Threads={USE_THREADS}')
    if USE_PATTERNS:
        print(f'   Patterns: {len(REVIEW_PATTERNS)} in {len(PATTERN_CATEGORIES)} categories')
    print(f'   AI: {AI_MODEL}')
    print(f'   AI_KEY: {"***" + AI_KEY[-6:] if AI_KEY else "MISSING!"}')
    print('='*50)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

