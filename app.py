# -*- coding: utf-8 -*-
import json, random, requests as http_req, time
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
BASE_DIR = Path(__file__).parent

with open(BASE_DIR / 'names.json', 'r', encoding='utf-8') as f:
    NAMES = json.load(f)

# ═══════════════════════════════════════════════════════════
# أرشيف — يحفظ كل النصوص السابقة لمنع التكرار
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
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive, f, ensure_ascii=False, indent=1)

def _get_used_texts(archive, limit=40):
    """آخر 40 نص مستخدم لإرسالها للـ AI"""
    texts = [r.get('text','') for r in archive.get('reviews',[])]
    return texts[-limit:] if len(texts)>limit else texts

def _archive_review(review_text, product_name, persona_name):
    """حفظ تقييم في الأرشيف"""
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
    arc = _load_archive()
    for rv in reviews:
        arc['reviews'].append({
            'text': rv.get('text',''),
            'product': rv.get('product',''),
            'persona': persona_name,
            'ts': int(time.time())
        })
    _save_archive(arc)

print(f'📦 الأرشيف: {len(_load_archive().get("reviews",[]))} تقييم محفوظ')

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
    """توليد تقييمات AI فريدة لكل عطر حسب الشخصية"""
    pf_list = '\n'.join([f'{i+1}. {p["name"]} ({p["brand"]}, {p["price"]} ر.س)' for i,p in enumerate(perfumes)])

    # جلب النصوص المستخدمة سابقاً
    used = _get_used_texts(_load_archive())
    used_block = ''
    if used:
        used_block = '\n\n⛔ لا تكرر أي صياغة مشابهة لهذه:\n' + '\n'.join([f'- {t}' for t in used[-30:]])

    prompt = f"""أنت عميل سعودي حقيقي يكتب تقييمات على متجر عطور إلكتروني.

بيانات الشخصية:
- {persona['label']}، {'رجل' if persona['gender']=='male' else 'امرأة'}، {persona['age']} سنة، من {persona['city']}

العطور:
{pf_list}

## قواعد كتابة التقييم (مبنية على تحليل تقييمات حقيقية):

1. الطول: من 3 كلمات إلى 25 كلمة فقط. بعضها قصير جداً مثل "ممتاز" أو "روعة" أو "حلو مرة"
2. لا تذكر اسم العطر في كل تقييم. بعض العملاء يكتبون فقط رأيهم بدون ذكر الاسم
3. لا تضع إيموجي أو نقاط أو علامات ترقيم إلا نادراً وبشكل طبيعي
4. لا تبدأ كل تقييم بنفس الطريقة. نوّع بشكل كبير
5. اكتب بلهجة عامية سعودية طبيعية حسب مدينة الشخص:
   - الرياض/القصيم/حائل: نجدية (مرة، وايد حلو، ذا الشي، كفو)
   - جدة/مكة/المدينة: حجازية (كتير، قوي، يا سلام، حبيته)
   - الدمام/الخبر: شرقية (حلو، يجنن، مرة حلو، فله)
6. أنماط التقييمات الحقيقية (نوّع بينها):
   - تقييم قصير جداً: "ممتاز" / "جميل" / "روعة مو طبيعي" / "كفو"
   - عن التوصيل: "وصلني بسرعة" / "الشحن سريع ماشاء الله"
   - عن التغليف: "التغليف نظيف ومرتب" / "وصل مغلف بشكل فخم"
   - عن الثبات: "يثبت طول اليوم" / "الثبات خرافي"
   - عن الريحة بدون ذكر الاسم: "ريحته فخمة" / "الريحة تجنن"
   - تجربة شخصية: "جربته وطلع روعة" / "استخدمته شهر كامل"
   - هدية: "جبته هدية وانبسطوا فيه" / "هديت خوي وعجبه"
   - مقارنة: "أحسن من اللي عندي" / "سعره أحلى من المحلات"
   - تكرار شراء: "ثاني مرة أطلب" / "مو أول مرة وبإذن الله مو الأخيرة"
   - مع ملاحظة بسيطة: "حلو بس خفيف شوي" / "كويس بس التوصيل تأخر"
7. التقييم 5 نجوم في الغالب، أحياناً 4، ونادراً 3
8. لا تكتب تقييم أطول من سطر واحد. الواقعية أهم من الكمال
{used_block}

أرجع JSON فقط بدون أي نص:
[
  {{"product": "اسم العطر", "rating": 5, "text": "التقييم"}},
  ...
]"""

    result = _ai_call(prompt, max_tokens=2000)
    if not result:
        return _fallback_reviews(persona, perfumes)

    # تنظيف الرد
    result = result.strip()
    if result.startswith('```'):
        result = result.split('\n', 1)[1] if '\n' in result else result[3:]
        if result.endswith('```'):
            result = result[:-3]
        result = result.strip()

    try:
        reviews = json.loads(result)
        # تقييم واحد فقط لكل منتج — لا أكثر
        reviews = reviews[:len(perfumes)]
        seen_texts = set()
        final = []
        for i, rv in enumerate(reviews):
            if i < len(perfumes):
                rv['price'] = perfumes[i]['price']
                rv['brand'] = perfumes[i]['brand']
                rv['pg'] = perfumes[i]['g']
                rv['product'] = perfumes[i]['name']
                # منع تكرار نفس النص
                txt = rv.get('text','').strip()
                if txt in seen_texts:
                    txt = txt + ' 👍' if not txt.endswith('👍') else txt[:-2]
                seen_texts.add(txt)
                rv['text'] = txt
                final.append(rv)
        # حفظ في الأرشيف
        _archive_batch(final, persona.get('name',''))
        return final
    except:
        return _fallback_reviews(persona, perfumes)

def _ai_single_review(persona, product):
    """توليد تقييم واحد بالـ AI"""
    used = _get_used_texts(_load_archive(), limit=20)
    used_block = ''
    if used:
        used_block = '\n⛔ لا تكرر هذه النصوص السابقة:\n' + '\n'.join([f'- {t}' for t in used[-15:]])

    prompt = f"""اكتب تقييم واحد فقط كعميل سعودي حقيقي.

العميل: {persona['label']}، {'رجل' if persona['gender']=='male' else 'امرأة'}، {persona['age']} سنة، من {persona['city']}
العطر: {product['name']}

القواعد:
- اكتب من 3 إلى 20 كلمة فقط
- ليس ضروري تذكر اسم العطر
- بدون إيموجي
- لهجة سعودية عامية طبيعية
- التقييم 4 أو 5
{used_block}

أرجع JSON فقط:
{{"rating": 5, "text": "التقييم"}}"""

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
        # حفظ في الأرشيف
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
    """اختيار عطور ذكية حسب الشخصية مع ترجيح الترند"""
    pool = [p for p in PRODUCTS if p['g'] in arch['prefers']
            and arch['price'][0] <= p['price'] <= arch['price'][1]]
    if len(pool) < 3:
        pool = [p for p in PRODUCTS if p['g'] in arch['prefers']]
    if len(pool) < 3:
        pool = PRODUCTS[:]

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
SAUDI_PREFIXES = ['050','051','053','054','055','056','057','058','059']
def _phone():
    return random.choice(SAUDI_PREFIXES) + ''.join([str(random.randint(0,9)) for _ in range(7)])

# ═══════════ توليد شخصية كاملة ═══════════
def _gen_one():
    arch = random.choice(ARCHETYPES)
    age = random.randint(*arch['age'])
    perfumes = _pick_products(arch)

    city = _city()
    addr = _national_address(city)
    persona = {
        'name': _name(arch['g']), 'city': city, 'gender': arch['g'], 'age': age,
        'label': arch['label'], 'emoji': arch['emoji'], 'archId': arch['id'],
        'address': addr, 'phone': _phone()
    }

    # تقييمات بالذكاء الاصطناعي
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

@app.route('/api/archive/clear', methods=['POST'])
def archive_clear():
    _save_archive({'reviews':[], 'store_reviews':[], 'personas':[]})
    return jsonify({'status':'ok','message':'تم مسح الأرشيف'})

if __name__ == '__main__':
    arc = _load_archive()
    print('='*50)
    print('🌸 مساعدي في شراء العطور — AI Mode')
    print(f'   {len(ARCHETYPES)} شخصية × {len(PRODUCTS)} عطر')
    print(f'   AI: {AI_MODEL}')
    print(f'   📦 أرشيف: {len(arc.get("reviews",[]))} تقييم محفوظ')
    print('   http://localhost:5000')
    print('='*50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
