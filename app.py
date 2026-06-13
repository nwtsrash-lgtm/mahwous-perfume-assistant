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
    from trending import calculate_product_weight, get_trending_names
    USE_TRENDING = True
    print('\u2705 trending loaded')
except ImportError:
    USE_TRENDING = False
    print('\u26a0\ufe0f trending not found')

try:
    from thread_generator import generate_thread_data, parse_ai_reply, format_thread_for_display
    USE_THREADS = True
    print('\u2705 thread_generator loaded')
except ImportError:
    USE_THREADS = False
    print('\u26a0\ufe0f thread_generator not found')

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

AI_KEY = os.environ.get('AI_KEY', '')
AI_URL = 'https://openrouter.ai/api/v1/chat/completions'
AI_MODEL = 'google/gemini-2.5-flash'
AI_TIMEOUT = 15          # مهلة قصيرة لتوليد مباشر وسريع للواجهة
AI_TEMPERATURE = 0.9     # درجة إبداع عالية لضمان تنوع النصوص

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
        prompt = build_master_prompt(persona, product_name, params, used_block, extra_block)
        return prompt, params
    # حالة قصوى: personas_engine غير محمّل إطلاقاً
    rating = 5 if random.random() < 0.6 else (4 if random.random() < 0.7 else 3)
    g = 'رجل' if persona.get('gender') == 'male' else 'امرأة'
    prompt = (
        f"اكتب تقييم واحد كعميل سعودي حقيقي بلهجة سعودية عامية.\n"
        f"العميل: {persona.get('label','')}، {g}، {persona.get('age','')} سنة، من {persona.get('city','')}\n"
        f"العطر: {product_name}\n"
        f"اكتب 3-20 كلمة. التقييم {rating} نجوم.\n"
        f"{('لا تكرر: ' + used_block) if used_block else ''}\n"
        f'أرجع JSON فقط: {{"rating": {rating}, "text": "...", "is_verified_purchase": true}}'
    )
    return prompt, {'rating': rating, 'pattern': 'scent_no_name'}


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


def _unique_fallback(product, persona=None, attempts=8):
    """شبكة أمان فريدة: يكرّر محرك القوالب الضخم حتى ينتج نصاً غير مكرر."""
    last = None
    for _ in range(attempts):
        rv = _fallback_single(product, persona)
        last = rv
        if not _is_dup(rv.get('text', '')):
            return rv
    return last  # احتمال نادر جداً — يُقبل بعد استنفاد المحاولات


def _used_texts_block(limit=30):
    """كتلة آخر النصوص المستخدمة (لمنع التكرار) — موحّدة لكل المسارات."""
    if USE_ANTI_REPEAT:
        return format_used_texts_block(limit=limit)
    used = _get_used_texts(_load_archive(), limit=limit + 10)
    return '\n'.join(f'- {t}' for t in used[-limit:]) if used else ''


def _plan_review(persona, pf, perfumes, used_block):
    """مرحلة (التفكير): يبني البرومبت ويحدّد النمط والتوجيه الاستراتيجي — بلا استدعاء AI.

    يرجع (prompt, params) ليتمكّن المسار اللحظي من عرض «ماذا سيكتب ولماذا» قبل الكتابة.
    """
    cross = _build_cross_sell(pf['name'], perfumes)
    return _make_master_prompt(persona, pf['name'], used_block, extra_block=cross)


def _write_review(persona, pf, prompt, params):
    """مرحلة (الكتابة): يستدعي AI لكتابة تقييم فريد مع شبكة أمان فريدة.

    يضمن أن النص الناتج غير مكرر (محاولات AI متصاعدة ثم قوالب فريدة)،
    ثم يسجّله في طبقة الجلسة. يرجع review_dict كامل الحقول.
    """
    rv = _ai_unique_json(prompt, max_tokens=400, attempts=4)

    if rv and rv.get('text') and not _is_dup(rv['text']):
        rv['price'] = pf['price']
        rv['brand'] = pf['brand']
        rv['pg'] = pf['g']
        rv['product'] = pf['name']
        rv['pattern'] = params.get('pattern', '')
        # أخطاء إملائية (تزيد التفرّد ولا تنقصه)
        if USE_DIALECTS and persona.get('has_typo', False):
            rv['text'] = apply_typos(rv['text'], probability=1.0)
    else:
        # كل محاولات AI كانت مكررة أو فشلت → قالب فريد مضمون
        rv = _unique_fallback(pf, persona)
        rv['pattern'] = params.get('pattern', '')

    # تتبع النمط + تسجيل النص لمنع أي تكرار لاحق
    if USE_AR_TRACK:
        ar_track_pattern(params.get('pattern', 'default'))
    _register(rv.get('text', ''))
    return rv


def _ai_reviews(persona, perfumes):
    """توليد تقييمات AI فريدة لكل عطر — يفكّر ثم يكتب (دفعة واحدة)."""
    used_block = _used_texts_block(limit=30)
    all_reviews = []
    for pf in perfumes:
        prompt, params = _plan_review(persona, pf, perfumes, used_block)
        all_reviews.append(_write_review(persona, pf, prompt, params))
    # حفظ في الأرشيف
    _archive_batch(all_reviews, persona.get('name', ''))
    return all_reviews

def _ai_single_review(persona, product):
    """توليد تقييم واحد بالـ AI — يفكّر ثم يكتب (نفس مسار التوليد الدفعي)."""
    used_block = _used_texts_block(limit=15)
    prompt, params = _make_master_prompt(persona, product['name'], used_block)
    rv = _write_review(persona, product, prompt, params)
    _archive_review(rv.get('text', ''), product['name'], persona.get('name', ''))
    return rv

# جوانب متجر متنوّعة — يُختار منها جانبان عشوائياً لكل تقييم لمنع التكرار
STORE_ASPECTS = [
    'سرعة التوصيل', 'فخامة التغليف', 'أصالة العطور 100%', 'خدمة العملاء وسرعة الرد',
    'الأسعار المنافسة', 'سهولة الطلب والدفع', 'العينات المجانية مع الطلب',
    'الكرت الشخصي مع الطلب', 'التغليف المحمي ضد الكسر', 'التقسيط بتابي/تمارا',
]
# أساليب بداية متنوّعة لتقييم المتجر (تمنع تكرار صيغة الافتتاح)
STORE_OPENERS = [
    'ابدأ بانطباعك المباشر عن تجربة الشراء',
    'ابدأ بذكر آخر طلب وصلك وكيف كان',
    'ابدأ بمقارنة بسيطة مع متاجر ثانية تعاملت معها',
    'ابدأ بردة فعلك أول ما فتحت الطلب',
    'ابدأ بنصيحة لغيرك يطلب من المتجر',
]


def _ai_store_review(persona):
    """تقييم متجر متنوّع وغير مكرر — يدوّر الجوانب والبداية ويمنع التكرار."""
    aspects = random.sample(STORE_ASPECTS, k=2)
    opener = random.choice(STORE_OPENERS)
    used_block = _used_texts_block(limit=15)
    prompt = f"""اكتب تقييم قصير (8-16 كلمة) لمتجر "مهووس للعطور" بلهجة سعودية عامية.
العميل: {persona['name']}، {persona['label']}، عمره {persona['age']}، من {persona['city']}.
## ركّز على هذين الجانبين تحديداً (لا غيرهما): {aspects[0]} و{aspects[1]}.
## قواعد:
- {opener}
- لا تبدأ بكلمة "متجر" ولا بنفس الصيغ الجاهزة الشائعة
- لهجة سعودية عفوية، بدون فصحى
- لا تكرر أياً من هذه الصياغات السابقة:
{used_block if used_block else '(لا يوجد سابق)'}
أرجع JSON فقط: {{"rating": 5, "text": "..."}}"""
    rv = _ai_unique_json(prompt, max_tokens=200, attempts=4)
    if rv and rv.get('text') and not _is_dup(rv['text']):
        _register(rv['text'])
        if USE_ANTI_REPEAT:
            try:
                ar_archive_review(rv['text'], 'متجر مهووس', persona.get('name', ''))
            except Exception:
                pass
        return rv
    # شبكة أمان فريدة: اختر من المجموعة نصاً غير مستخدم
    pool = list(STORE_REVIEWS.get(5, ['متجر ممتاز والعطور أصلية والتوصيل سريع']))
    random.shuffle(pool)
    for t in pool:
        if not _is_dup(t):
            _register(t)
            return {'rating': 5, 'text': t}
    # نادر: كل المجموعة مستخدمة — اقبل آخر ناتج AI إن وُجد وإلا واحداً من المجموعة
    t = (rv.get('text') if rv else None) or random.choice(pool)
    _register(t)
    return {'rating': 5, 'text': t}

# ═══════════ Fallback بدون AI ═══════════
FALLBACK_M = [
    'ثباته قوي وريحته رجالية فخمة، {n} من أفضل ما جربت',
    'صراحة عجبني مرة، الفوحان ممتاز وريحته تلفت الانتباه',
    'طلبته وعجبني كثير، ريحته مميزة وثابتة طول اليوم',
    'سعره مناسب لجودته والتوصيل كان سريع، أنصح فيه',
    'من يوم ما جربت {n} وأنا ما غيرته، ريحة رجالية محترمة',
    'والله ريحته فخمة وثباته خرافي، يستاهل كل ريال',
    'كل ما ألبسه أحد يسألني وش عطرك، {n} ريحته تجنن',
]
FALLBACK_F = [
    'ريحته ناعمة وأنثوية، كل البنات سألوني عنه',
    'حلو مررره ويثبت طول اليوم 😍، {n} صار المفضل عندي',
    'جبته هدية لنفسي وما ندمت أبداً، ريحته تجنن',
    'ريحته فخمة والتغليف كان رائع من مهووس',
    'صراحة فاجأني، {n} ريحته راقية وتدوم ساعات طويلة',
    'كل ما ألبسه أحس بثقة، ريحة أنثوية أموت عليها',
]

def _pg_to_gender(pg):
    """تحويل تصنيف العطر العربي إلى وسيط ReviewGenerator"""
    if pg == 'رجالي':
        return 'male'
    if pg == 'نسائي':
        return 'female'
    return 'unisex'


def _fallback_single(product, persona=None):
    """شبكة أمان: محرك القوالب الضخم (review_generator) عند تعطّل الـ AI.

    يلجأ للمصفوفات الثابتة فقط إذا فشل المحرك أو لم يتوفر.
    """
    pg = product.get('g', 'مشترك')
    if persona and persona.get('gender'):
        gender = 'male' if persona['gender'] == 'male' else 'female'
    else:
        gender = _pg_to_gender(pg)

    if USE_REVIEW_GEN and fallback_gen is not None:
        try:
            res = fallback_gen.generate_reviews(
                product['name'], product.get('price', 0), gender=gender, count=1)
            if res:
                return {'product': product['name'], 'price': product.get('price', 0),
                        'brand': product.get('brand', ''), 'pg': pg,
                        'rating': res[0]['rating'], 'text': res[0]['text']}
        except Exception as e:
            print(f'⚠️ fallback_gen single error: {e}')

    # آخر شبكة أمان: مصفوفات ثابتة
    short = ' '.join(product['name'].split()[:3])
    pool = FALLBACK_F if gender == 'female' else FALLBACK_M
    txt = random.choice(pool).replace('{n}', short)
    return {'product': product['name'], 'price': product.get('price', 0),
            'brand': product.get('brand', ''), 'pg': pg,
            'rating': 5 if random.random() < .7 else 4, 'text': txt}


def _fallback_reviews(persona, perfumes):
    """تقييمات احتياطية لمجموعة عطور عبر محرك القوالب الضخم"""
    return [_fallback_single(pf, persona) for pf in perfumes]

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
    pool = [p for p in PRODUCTS if p['g'] in arch['prefers']
            and arch['price'][0] <= p['price'] <= arch['price'][1]]
    if len(pool) < 3:
        pool = [p for p in PRODUCTS if p['g'] in arch['prefers']]
    if len(pool) < 3:
        pool = PRODUCTS[:]

    # استخدام محرك الترند المتقدم إذا متوفر
    if USE_TRENDING:
        weights = [calculate_product_weight(p.get('name',''), p.get('brand','')) for p in pool]
    else:
        trend_lower = [b.lower() for b in TRENDING_BRANDS]
        weights = []
        for p in pool:
            brand = p.get('brand','').lower()
            name = p.get('name','').lower()
            is_trend = any(tb in brand or tb in name for tb in trend_lower)
            weights.append(3.0 if is_trend else 1.0)

    count = random.randint(*arch['count'])
    count = min(count, len(pool))

    selected = []
    pool_copy = list(pool)
    w_copy = list(weights)
    for _ in range(count):
        if not pool_copy: break
        picks = random.choices(range(len(pool_copy)), weights=w_copy, k=1)
        idx = picks[0]
        selected.append(pool_copy[idx])
        pool_copy.pop(idx)
        w_copy.pop(idx)

    return selected

STORE_REVIEWS = {
    5:['متجر عطور أصلية وتوصيل سريع','التغليف فخم والعطور أصلية ١٠٠٪',
       'أفضل متجر عطور أونلاين بالسعودية','توصيل سريع وتغليف احترافي',
       'متجر موثوق والأسعار منافسة','تجربة شراء ممتازة','أنصح فيه بقوة'],
    4:['كويس بس التوصيل تأخر شوي','تجربة جيدة بشكل عام'],
}

# ═══════════ الأسماء والمدن والعناوين ═══════════
def _name(g):
    key='male' if g=='male' else 'female'
    return random.choice(NAMES.get(key,['مستخدم']))+' '+random.choice(NAMES.get('family_names',['السعودي']))

def _city():
    cities=NAMES.get('cities',[{'name':'الرياض','weight':1}])
    return random.choices(cities,weights=[c.get('weight',1) for c in cities],k=1)[0]['name']

# ═══════════ عنوان وطني سعودي ═══════════
CITY_DATA = {
    'الرياض':{'postal_range':(11411,13999),'districts':[
        ('العليا','شارع العليا العام'),('النخيل','شارع الأمير محمد بن سعد'),('الملقا','طريق أنس بن مالك'),
        ('الياسمين','شارع عبدالرحمن الداخل'),('حطين','شارع التخصصي'),('الورود','شارع الورود'),
        ('السليمانية','شارع الأمير سلطان'),('الربوة','طريق الإمام الشافعي'),('المروج','طريق الملك فهد'),
        ('الصحافة','طريق أبو بكر الصديق'),('النرجس','شارع محمد بن عبدالوهاب')]},
    'جدة':{'postal_range':(21411,23999),'districts':[
        ('الحمراء','شارع فلسطين'),('الروضة','شارع الأمير سلطان'),('الشاطئ','طريق الكورنيش'),
        ('البوادي','شارع الأمير ماجد'),('الفيصلية','شارع الأمير فهد'),('النعيم','شارع حراء'),
        ('المحمدية','شارع التحلية'),('السامر','طريق المدينة')]},
    'الدمام':{'postal_range':(31411,34999),'districts':[
        ('الشاطئ','طريق الكورنيش'),('الفيصلية','شارع الملك فيصل'),('الريان','شارع الريان'),
        ('الجلوية','شارع الظهران'),('المريكبات','شارع الملك خالد'),('الأمانة','طريق الخليج')]},
    'مكة المكرمة':{'postal_range':(21955,24999),'districts':[
        ('العزيزية','طريق الملك عبدالعزيز'),('الشوقية','شارع الشوقية'),('النسيم','شارع النسيم'),
        ('الزاهر','شارع الزاهر'),('الرصيفة','شارع إبراهيم الخليل')]},
    'المدينة المنورة':{'postal_range':(41411,42999),'districts':[
        ('العزيزية','طريق الملك عبدالله'),('قربان','شارع قربان'),('الحرة الشرقية','شارع سلطانة'),
        ('الدفاع','شارع أبو بكر الصديق'),('المناخة','شارع المناخة')]},
    'الخبر':{'postal_range':(31411,34999),'districts':[
        ('الحزام الذهبي','شارع الأمير تركي'),('اليرموك','شارع اليرموك'),('العليا','شارع الأمير فيصل'),
        ('الثقبة','شارع الملك سعود'),('الروابي','شارع الروابي')]},
    'أبها':{'postal_range':(61411,62999),'districts':[
        ('المنسك','شارع الملك فيصل'),('الوردتين','شارع الأمير سلطان'),('المفتاحة','شارع الفن')]},
    'تبوك':{'postal_range':(71411,71999),'districts':[
        ('المروج','شارع الأمير فهد'),('الفيصلية','طريق الملك فهد'),('السليمانية','شارع السلام')]},
    'بريدة':{'postal_range':(51411,52999),'districts':[
        ('الصفراء','شارع الخبيب'),('الفايزية','طريق الملك عبدالعزيز'),('الإسكان','شارع الحرمين')]},
    'حائل':{'postal_range':(81411,81999),'districts':[
        ('المنتزه','شارع الملك فيصل'),('العزيزية','طريق الأمير سلطان'),('النقرة','شارع النقرة')]},
}

def _national_address(city_name):
    cdata = CITY_DATA.get(city_name, {'postal_range':(11411,13999),'districts':[('المركز','شارع العام')]})
    dist, street = random.choice(cdata['districts'])
    building = str(random.randint(1000, 9999))
    postal = str(random.randint(*cdata['postal_range']))
    extra = str(random.randint(1000, 9999))
    return {
        'building': building, 'street': street, 'district': dist,
        'city': city_name, 'postal': postal, 'extra': extra,
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

@app.route('/api/generate', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def generate(): return jsonify(_gen_one())

@app.route('/api/batch', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def batch():
    n = _safe_int((request.get_json(silent=True) or {}).get('count', 5), 5, 1, 20)
    results = [_gen_one() for _ in range(n)]
    return jsonify({'results': results, 'count': n})

@app.route('/api/regen-review', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def regen_review():
    d = request.get_json(silent=True) or {}
    arch = next((a for a in ARCHETYPES if a['id']==d.get('archId','')), random.choice(ARCHETYPES))
    product = {'name':d.get('product',''),'price':d.get('price',0),'brand':d.get('brand',''),'g':d.get('pg','مشترك')}
    persona = _make_persona_for_arch(arch)
    rv = _ai_single_review(persona, product)
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
    reviews = _ai_reviews(persona, perfumes)
    return jsonify({'perfumes': perfumes, 'reviews': reviews})

@app.route('/api/new-phone', methods=['POST'])
def new_phone():
    return jsonify({'phone': _phone()})

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

# مجموعة ردود احتياطية متنوّعة (بدل '👍' المتكرر) — تُختار بلا تكرار
THREAD_FALLBACKS = [
    'إي صح كلامك', 'توني أطلبه', 'يعطيك العافية على المعلومة', 'نفس رأيي تماماً',
    'شكراً للتوضيح', 'جربته وعجبني', 'الله يعطيك العافية', 'كلامك سليم 100%',
    'وأنا أؤكد كلامك', 'فدتني، مشكور', 'بطلبه بسبب كلامك', 'أتفق معك',
]


def _unique_thread_fallback():
    """رد احتياطي فريد من المجموعة (يتجنّب التكرار قدر الإمكان)."""
    pool = list(THREAD_FALLBACKS)
    random.shuffle(pool)
    for t in pool:
        if not _is_dup(t):
            return t
    return random.choice(pool)


@app.route('/api/generate-thread', methods=['POST'])
@rate_limit(RATE_LIMIT_GENERATE)
def api_generate_thread():
    """توليد محادثة: تقييم رئيسي + ردود من عملاء آخرين"""
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

    # استدعاء الـ AI لكل رد — كل رد فريد لا يتكرر
    thread_replies = []
    for reply_info in thread_data['replies']:
        text = _ai_unique_text(reply_info['prompt'], max_tokens=150,
                               attempts=3, parser=parse_ai_reply)
        if not text or _is_dup(text):
            text = _unique_thread_fallback()
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

