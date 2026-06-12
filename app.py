# -*- coding: utf-8 -*-
import sys, json, random, requests as http_req, time
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
CORS(app)
BASE_DIR = Path(__file__).parent

# ═══════════════════════════════════════════════════════════
# استيراد المحركات الجديدة (مع fallback آمن)
# ═══════════════════════════════════════════════════════════
try:
    from personas_engine import generate_persona, generate_review_params, build_master_prompt, ARCHETYPES as NEW_ARCHETYPES
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
    from review_patterns import pick_pattern, pick_rating, get_pattern_description, REVIEW_PATTERNS, RATING_DISTRIBUTION
    USE_PATTERNS = True
    print('\u2705 review_patterns loaded')
except ImportError:
    USE_PATTERNS = False
    print('\u26a0\ufe0f review_patterns not found')

try:
    from anti_repeat import (archive_review as ar_archive_review, archive_batch as ar_archive_batch,
                             get_used_texts as ar_get_used_texts, get_archive_stats as ar_get_archive_stats,
                             clear_archive as ar_clear_archive, format_used_texts_block, is_duplicate)
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
ARCHIVE_FILE = BASE_DIR / 'archive.json'

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
import os
# حمّل .env يدوياً
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    for line in _env_path.read_text(encoding='utf-8').strip().split('\n'):
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

AI_KEY = os.environ.get('AI_KEY', '')
AI_URL = 'https://openrouter.ai/api/v1/chat/completions'
AI_MODEL = 'google/gemini-2.5-flash'

def _ai_call(prompt, max_tokens=1200):
    """استدعاء AI عبر OpenRouter"""
    try:
        r = http_req.post(AI_URL, headers={
            'Authorization': f'Bearer {AI_KEY}',
            'Content-Type': 'application/json',
        }, json={
            'model': AI_MODEL,
            'messages': [{'role':'user','content':prompt}],
            'max_tokens': max_tokens,
            'temperature': 1.0,
        }, timeout=60)
        data = r.json()
        if r.status_code != 200:
            err = data.get('error',{}).get('message','unknown')
            print(f'⚠️ AI HTTP {r.status_code}: {err}')
            return None
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f'❌ AI Error: {e}')
        return None

def _ai_reviews(persona, perfumes):
    """توليد تقييمات AI فريدة لكل عطر — يستخدم MASTER_PROMPT المتقدم"""
    # جلب النصوص المستخدمة
    if USE_ANTI_REPEAT:
        used_block = format_used_texts_block(limit=30)
    else:
        used = _get_used_texts(_load_archive())
        used_block = '\n'.join([f'- {t}' for t in used[-30:]]) if used else ''

    all_reviews = []
    for pf in perfumes:
        # توليد معايير التقييم لكل منتج
        if USE_NEW_PERSONAS and USE_PATTERNS:
            params = generate_review_params(persona)
            prompt = build_master_prompt(persona, pf['name'], params, used_block)
        else:
            # fallback إلى البرومبت القديم
            rating = 5 if random.random() < 0.6 else (4 if random.random() < 0.7 else 3)
            prompt = f"""اكتب تقييم واحد كعميل سعودي حقيقي.
العميل: {persona['label']}، {'رجل' if persona['gender']=='male' else 'امرأة'}، {persona['age']} سنة، من {persona['city']}
العطر: {pf['name']}
اكتب 3-20 كلمة بلهجة سعودية. التقييم {rating} نجوم.
{'لا تكرر: ' + used_block if used_block else ''}
أرجع JSON فقط: {{"rating": {rating}, "text": "التقييم"}}"""
            params = {'rating': rating, 'pattern': 'scent_no_name'}

        result = _ai_call(prompt, max_tokens=400)
        if not result:
            all_reviews.append(_fallback_single(pf))
            continue

        # تنظيف الرد
        result = result.strip()
        if result.startswith('```'):
            result = result.split('\n', 1)[1] if '\n' in result else result[3:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()

        try:
            rv = json.loads(result)
            rv['price'] = pf['price']
            rv['brand'] = pf['brand']
            rv['pg'] = pf['g']
            rv['product'] = pf['name']
            rv['pattern'] = params.get('pattern', '')

            # تطبيق أخطاء إملائية إذا الشخصية تحتاج
            if USE_DIALECTS and persona.get('has_typo', False):
                rv['text'] = apply_typos(rv['text'], probability=1.0)

            # التحقق من التكرار — أعد التوليد بنص مختلف بدل إضافة فراغ بلا معنى
            if USE_ANTI_REPEAT and is_duplicate(rv.get('text', '')):
                retry = _ai_call(
                    prompt + '\n\n⚠️ تنبيه: التقييم السابق كان مكرراً. اكتب نصاً مختلفاً تماماً ببداية وكلمات مختلفة.',
                    max_tokens=400)
                if retry:
                    retry = retry.strip()
                    if retry.startswith('```'):
                        retry = retry.split('\n', 1)[1] if '\n' in retry else retry[3:]
                        if retry.endswith('```'):
                            retry = retry[:-3]
                        retry = retry.strip()
                    try:
                        rv2 = json.loads(retry)
                        if rv2.get('text') and not is_duplicate(rv2['text']):
                            rv['text'] = rv2['text']
                            if 'rating' in rv2:
                                rv['rating'] = rv2['rating']
                    except Exception:
                        pass

            all_reviews.append(rv)
        except:
            all_reviews.append(_fallback_single(pf))

    # حفظ في الأرشيف
    _archive_batch(all_reviews, persona.get('name', ''))
    return all_reviews

def _ai_single_review(persona, product):
    """توليد تقييم واحد بالـ AI — يستخدم MASTER_PROMPT المتقدم"""
    if USE_ANTI_REPEAT:
        used_block = format_used_texts_block(limit=15)
    else:
        used = _get_used_texts(_load_archive(), limit=20)
        used_block = '\n'.join([f'- {t}' for t in used[-15:]]) if used else ''

    if USE_NEW_PERSONAS and USE_PATTERNS:
        params = generate_review_params(persona)
        prompt = build_master_prompt(persona, product['name'], params, used_block)
    else:
        prompt = f"""اكتب تقييم واحد فقط كعميل سعودي حقيقي.
العميل: {persona['label']}، {'رجل' if persona['gender']=='male' else 'امرأة'}، {persona['age']} سنة، من {persona['city']}
العطر: {product['name']}
اكتب 3-20 كلمة بلهجة سعودية. التقييم 4 أو 5.
{'لا تكرر: ' + used_block if used_block else ''}
أرجع JSON فقط: {{"rating": 5, "text": "التقييم"}}"""

    result = _ai_call(prompt, max_tokens=300)
    if not result:
        return _fallback_single(product)

    result = result.strip()
    if result.startswith('```'):
        result = result.split('\n', 1)[1] if '\n' in result else result[3:]
        if result.endswith('```'): result = result[:-3]
        result = result.strip()

    try:
        rv = json.loads(result)
        rv['product'] = product['name']
        rv['price'] = product['price']
        rv['brand'] = product['brand']
        rv['pg'] = product.get('g','مشترك')
        if USE_DIALECTS and persona.get('has_typo', False):
            rv['text'] = apply_typos(rv['text'], probability=1.0)
        _archive_review(rv['text'], product['name'], persona.get('name',''))
        return rv
    except:
        return _fallback_single(product)

def _ai_store_review(persona):
    """تقييم متجر بالـ AI"""
    prompt = f"""اكتب تقييم قصير (10-20 كلمة) لمتجر "مهووس للعطور" بلهجة سعودية عامية.
العميل: {persona['name']}، {persona['label']}، عمره {persona['age']}، من {persona['city']}.
اذكر شي مثل: التوصيل، التغليف، الأصالة، خدمة العملاء.
أرجع JSON فقط: {{"rating": 5, "text": "..."}}"""
    result = _ai_call(prompt, max_tokens=200)
    if not result:
        return {'rating':5,'text':'متجر ممتاز والعطور أصلية والتوصيل سريع'}
    result = result.strip()
    if result.startswith('```'):
        result = result.split('\n', 1)[1] if '\n' in result else result[3:]
        if result.endswith('```'): result = result[:-3]
        result = result.strip()
    try:
        return json.loads(result)
    except:
        return {'rating':5,'text':'متجر ممتاز والعطور أصلية والتوصيل سريع'}

# ═══════════ Fallback بدون AI ═══════════
FALLBACK_M = [
    'عطر {n} ثباته قوي وريحته رجالية فخمة، أنصح فيه',
    '{n} من أفضل العطور اللي جربتها، الفوحان ممتاز',
    'طلبت {n} وعجبني كثير، ريحته مميزة وتلفت الانتباه',
    '{n} سعره مناسب لجودته، والتوصيل كان سريع',
]
FALLBACK_F = [
    '{n} ريحته ناعمة وأنثوية، كل البنات سألوني عنه',
    'عطر {n} حلو مررره ويثبت طول اليوم 😍',
    'جبت {n} هدية لنفسي وما ندمت أبداً',
    '{n} ريحته فخمة والتغليف كان رائع من مهووس',
]

def _fallback_reviews(persona, perfumes):
    pool = FALLBACK_F if persona['gender']=='female' else FALLBACK_M
    reviews = []
    for pf in perfumes:
        tpl = random.choice(pool)
        short = ' '.join(pf['name'].split()[:3])
        txt = tpl.replace('{n}', short)
        rt = 5 if random.random() < .7 else 4
        reviews.append({'product':pf['name'],'price':pf['price'],'brand':pf['brand'],
                        'pg':pf['g'],'rating':rt,'text':txt})
    return reviews

def _fallback_single(product):
    short = ' '.join(product['name'].split()[:3])
    return {'product':product['name'],'price':product['price'],'brand':product['brand'],
            'pg':product.get('g','مشترك'),'rating':5,
            'text':f'{short} عطر ممتاز وريحته تجنن، أنصح فيه بقوة'}

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
]

# ═══════════ الكتالوج الكامل من ملف المتجر ═══════════
with open(BASE_DIR / 'catalog.json', 'r', encoding='utf-8') as f:
    PRODUCTS = json.load(f)
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

@app.route('/api/generate', methods=['POST'])
def generate(): return jsonify(_gen_one())

@app.route('/api/batch', methods=['POST'])
def batch():
    n = min(int((request.get_json(silent=True) or {}).get('count', 5)), 20)
    results = [_gen_one() for _ in range(n)]
    return jsonify({'results': results, 'count': n})

@app.route('/api/regen-review', methods=['POST'])
def regen_review():
    d = request.get_json(silent=True) or {}
    arch = next((a for a in ARCHETYPES if a['id']==d.get('archId','')), random.choice(ARCHETYPES))
    product = {'name':d.get('product',''),'price':d.get('price',0),'brand':d.get('brand',''),'g':d.get('pg','مشترك')}
    persona = {'name':'عميل','label':arch['label'],'gender':arch['g'],
               'age':random.randint(*arch['age']),'city':_city()}
    rv = _ai_single_review(persona, product)
    return jsonify(rv)

@app.route('/api/add-perfumes', methods=['POST'])
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
    persona = {'name':'عميل','label':arch['label'],'gender':arch['g'],
               'age':random.randint(*arch['age']),'city':_city()}
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

if __name__ == '__main__':
    arc = _load_archive()
    print('='*50)
    print('Perfume Assistant - AI Mode (Enhanced)')
    print(f'   {len(ARCHETYPES)} archetypes x {len(PRODUCTS)} products')
    print(f'   AI: {AI_MODEL}')
    print(f'   Archive: {len(arc.get("reviews",[]))} reviews (max 200 FIFO)')
    print(f'   New Engines: Personas={USE_NEW_PERSONAS} Dialects={USE_DIALECTS} Patterns={USE_PATTERNS}')
    print(f'   Anti-Repeat={USE_ANTI_REPEAT} Trending={USE_TRENDING} Intel={USE_INTEL}')
    print('   http://localhost:5000')
    print('='*50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
