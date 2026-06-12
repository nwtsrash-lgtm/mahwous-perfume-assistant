# -*- coding: utf-8 -*-
import streamlit as st
import json, random, requests as http_req, time, os
from pathlib import Path

st.set_page_config(page_title="🌸 مساعدي في شراء العطور", layout="centered", initial_sidebar_state="collapsed")

BASE_DIR = Path(__file__).parent

# ═══════════ تحميل البيانات ═══════════
@st.cache_data
def load_names():
    with open(BASE_DIR / 'names.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_catalog():
    with open(BASE_DIR / 'catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

NAMES = load_names()
PRODUCTS = load_catalog()

# ═══════════ AI ═══════════
AI_KEY = os.environ.get('AI_KEY', '')
if not AI_KEY:
    _env = BASE_DIR / '.env'
    if _env.exists():
        for line in _env.read_text(encoding='utf-8').strip().split('\n'):
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                if k.strip() == 'AI_KEY':
                    AI_KEY = v.strip()
AI_URL = 'https://openrouter.ai/api/v1/chat/completions'
AI_MODEL = 'google/gemini-2.5-flash'

def ai_call(prompt, max_tokens=1200):
    try:
        r = http_req.post(AI_URL, headers={
            'Authorization': f'Bearer {AI_KEY}',
            'Content-Type': 'application/json',
        }, json={
            'model': AI_MODEL,
            'messages': [{'role':'user','content':prompt}],
            'max_tokens': max_tokens, 'temperature': 1.0,
        }, timeout=60)
        data = r.json()
        if r.status_code != 200:
            return None
        return data['choices'][0]['message']['content'].strip()
    except:
        return None

def clean_json(result):
    result = result.strip()
    if result.startswith('```'):
        result = result.split('\n', 1)[1] if '\n' in result else result[3:]
        if result.endswith('```'): result = result[:-3]
    return result.strip()

# ═══════════ أرشيف ═══════════
ARCHIVE_FILE = BASE_DIR / 'archive.json'

def load_archive():
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'reviews':[]}
    return {'reviews':[]}

def save_archive(arc):
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(arc, f, ensure_ascii=False)

def get_used_texts(limit=40):
    arc = load_archive()
    texts = [r.get('text','') for r in arc.get('reviews',[])]
    return texts[-limit:]

def archive_batch(reviews, persona_name):
    arc = load_archive()
    for rv in reviews:
        arc['reviews'].append({'text':rv.get('text',''),'product':rv.get('product',''),
                               'persona':persona_name,'ts':int(time.time())})
    save_archive(arc)

# ═══════════ شخصيات ═══════════
ARCHETYPES = [
    {'id':'شاب_جامعي','g':'male','label':'شاب جامعي','emoji':'🎓','age':(18,23),'price':(0,300),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'رجل_أعمال','g':'male','label':'رجل أعمال','emoji':'👔','age':(30,50),'price':(400,2000),'prefers':['رجالي','مشترك'],'count':(3,6)},
    {'id':'خبير_عطور','g':'male','label':'خبير عطور','emoji':'🧪','age':(25,40),'price':(200,2000),'prefers':['رجالي','مشترك'],'count':(3,7)},
    {'id':'أب_عائلة','g':'male','label':'أب عائلة','emoji':'👨‍👧','age':(35,55),'price':(100,500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'شاب_رياضي','g':'male','label':'شاب رياضي','emoji':'💪','age':(20,30),'price':(100,400),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'كبير_سن','g':'male','label':'رجل كبير','emoji':'👴','age':(55,75),'price':(100,600),'prefers':['رجالي','مشترك'],'count':(2,3)},
    {'id':'موظف','g':'male','label':'موظف','emoji':'🏢','age':(25,45),'price':(150,500),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'بنت_عصرية','g':'female','label':'بنت عصرية','emoji':'💅','age':(20,28),'price':(100,600),'prefers':['نسائي','مشترك'],'count':(3,6)},
    {'id':'أم_سعودية','g':'female','label':'أم سعودية','emoji':'👩‍🦱','age':(38,55),'price':(100,800),'prefers':['نسائي','مشترك'],'count':(2,5)},
    {'id':'عروس','g':'female','label':'عروس','emoji':'👰','age':(21,30),'price':(300,2000),'prefers':['نسائي','مشترك'],'count':(4,8)},
    {'id':'موظفة','g':'female','label':'موظفة','emoji':'👩‍💻','age':(24,40),'price':(150,600),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'خبيرة_تجميل','g':'female','label':'خبيرة تجميل','emoji':'💄','age':(25,38),'price':(200,1000),'prefers':['نسائي','مشترك'],'count':(3,6)},
    {'id':'طالبة','g':'female','label':'طالبة جامعية','emoji':'📚','age':(18,23),'price':(0,250),'prefers':['نسائي','مشترك'],'count':(2,3)},
    {'id':'جدة','g':'female','label':'سيدة كبيرة','emoji':'👵','age':(55,75),'price':(100,500),'prefers':['نسائي','مشترك'],'count':(2,3)},
    {'id':'مقارن','g':'male','label':'مقارن أسعار','emoji':'📊','age':(25,40),'price':(100,600),'prefers':['رجالي','مشترك'],'count':(3,5)},
    {'id':'هدايا_رجل','g':'male','label':'يشتري هدايا','emoji':'🎁','age':(25,45),'price':(200,1000),'prefers':['نسائي','مشترك'],'count':(2,4)},
    {'id':'هدايا_أنثى','g':'female','label':'تشتري هدايا','emoji':'🎀','age':(22,45),'price':(200,800),'prefers':['رجالي','مشترك'],'count':(2,4)},
    {'id':'محب_تسوق','g':'male','label':'محب تسوق','emoji':'🛍️','age':(22,35),'price':(100,800),'prefers':['رجالي','مشترك'],'count':(3,6)},
    {'id':'محبة_تسوق','g':'female','label':'محبة تسوق','emoji':'👛','age':(22,35),'price':(100,800),'prefers':['نسائي','مشترك'],'count':(3,6)},
]

TRENDING = ['ديور','شانيل','توم فورد','لطافة','أرماني','بربري','كارولينا','لانكوم','فرساتشي','جوتشي','جان بول','أمواج','نارسيسو','بولغاري','كالفن','مونت بلانك','دولتشي','بوشرون','هوجو','جيرلان','كريد','سوفاج','خمرة']
TREND_LOW = [b.lower() for b in TRENDING]

# ═══════════ عناوين ═══════════
CITY_DATA = {
    'الرياض':{'postal':(11411,13999),'dists':[('العليا','شارع العليا'),('النخيل','شارع الأمير محمد'),('الملقا','طريق أنس بن مالك'),('الياسمين','شارع عبدالرحمن الداخل'),('حطين','شارع التخصصي'),('الورود','شارع الورود')]},
    'جدة':{'postal':(21411,23999),'dists':[('الحمراء','شارع فلسطين'),('الروضة','شارع الأمير سلطان'),('الشاطئ','طريق الكورنيش'),('البوادي','شارع الأمير ماجد'),('النعيم','شارع حراء')]},
    'الدمام':{'postal':(31411,34999),'dists':[('الشاطئ','طريق الكورنيش'),('الفيصلية','شارع الملك فيصل'),('الريان','شارع الريان')]},
    'مكة المكرمة':{'postal':(21955,24999),'dists':[('العزيزية','طريق الملك عبدالعزيز'),('الشوقية','شارع الشوقية'),('النسيم','شارع النسيم')]},
    'المدينة المنورة':{'postal':(41411,42999),'dists':[('العزيزية','طريق الملك عبدالله'),('قربان','شارع قربان'),('الدفاع','شارع أبو بكر الصديق')]},
    'الخبر':{'postal':(31411,34999),'dists':[('الحزام الذهبي','شارع الأمير تركي'),('اليرموك','شارع اليرموك'),('العليا','شارع الأمير فيصل')]},
    'أبها':{'postal':(61411,62999),'dists':[('المنسك','شارع الملك فيصل'),('المفتاحة','شارع الفن')]},
    'تبوك':{'postal':(71411,71999),'dists':[('المروج','شارع الأمير فهد'),('الفيصلية','طريق الملك فهد')]},
    'بريدة':{'postal':(51411,52999),'dists':[('الصفراء','شارع الخبيب'),('الفايزية','طريق الملك عبدالعزيز')]},
    'حائل':{'postal':(81411,81999),'dists':[('المنتزه','شارع الملك فيصل'),('العزيزية','طريق الأمير سلطان')]},
}
PREFIXES = ['050','051','053','054','055','056','057','058','059']

def pick_city():
    cities = NAMES.get('cities',[{'name':'الرياض','weight':1}])
    return random.choices(cities,weights=[c.get('weight',1) for c in cities],k=1)[0]['name']

def make_address(city):
    cd = CITY_DATA.get(city,{'postal':(11411,13999),'dists':[('المركز','شارع العام')]})
    dist, street = random.choice(cd['dists'])
    b = str(random.randint(1000,9999))
    p = str(random.randint(*cd['postal']))
    return f'{b} {street}، حي {dist}، {city} {p}'

def make_phone():
    return random.choice(PREFIXES)+''.join([str(random.randint(0,9)) for _ in range(7)])

def pick_products(arch):
    pool = [p for p in PRODUCTS if p['g'] in arch['prefers'] and arch['price'][0]<=p['price']<=arch['price'][1]]
    if len(pool)<3: pool = [p for p in PRODUCTS if p['g'] in arch['prefers']]
    if len(pool)<3: pool = PRODUCTS[:]
    weights = []
    for p in pool:
        nm = (p.get('brand','')+p.get('name','')).lower()
        weights.append(3.0 if any(t in nm for t in TREND_LOW) else 1.0)
    count = min(random.randint(*arch['count']), len(pool))
    sel, pc, wc = [], list(pool), list(weights)
    for _ in range(count):
        if not pc: break
        idx = random.choices(range(len(pc)),weights=wc,k=1)[0]
        sel.append(pc.pop(idx)); wc.pop(idx)
    return sel

def gen_reviews(persona, perfumes):
    pf_list = '\n'.join([f'{i+1}. {p["name"]} ({p["brand"]}, {p["price"]} ر.س)' for i,p in enumerate(perfumes)])
    used = get_used_texts()
    ub = ''
    if used:
        ub = '\n\n⛔ لا تكرر أي صياغة مشابهة لهذه:\n'+'\n'.join([f'- {t}' for t in used[-30:]])
    prompt = f"""أنت عميل سعودي حقيقي يكتب تقييمات على متجر عطور إلكتروني.

بيانات الشخصية:
- {persona['label']}، {'رجل' if persona['gender']=='male' else 'امرأة'}، {persona['age']} سنة، من {persona['city']}

العطور:
{pf_list}

## قواعد كتابة التقييم:
1. الطول: من 3 كلمات إلى 25 كلمة فقط. بعضها قصير مثل "ممتاز" أو "روعة"
2. لا تذكر اسم العطر في كل تقييم
3. لا تضع إيموجي إلا نادراً
4. لا تبدأ كل تقييم بنفس الطريقة
5. لهجة سعودية عامية حسب المدينة (نجدية/حجازية/شرقية)
6. نوّع بين: تقييم قصير، توصيل، تغليف، ثبات، ريحة، هدية، مقارنة، تكرار شراء
7. التقييم 5 نجوم غالباً، أحياناً 4، نادراً 3
{ub}

أرجع JSON فقط بدون أي نص:
[{{"product":"اسم العطر","rating":5,"text":"التقييم"}}]"""

    result = ai_call(prompt, 2000)
    if not result:
        return [{'product':p['name'],'rating':5,'text':'ممتاز','brand':p['brand'],'price':p['price']} for p in perfumes]
    try:
        reviews = json.loads(clean_json(result))[:len(perfumes)]
        for i,rv in enumerate(reviews):
            if i<len(perfumes):
                rv['product']=perfumes[i]['name']; rv['brand']=perfumes[i]['brand']; rv['price']=perfumes[i]['price']
        archive_batch(reviews, persona.get('name',''))
        return reviews
    except:
        return [{'product':p['name'],'rating':5,'text':'ممتاز','brand':p['brand'],'price':p['price']} for p in perfumes]

def gen_store_review(persona):
    prompt = f"""اكتب تقييم قصير (10-20 كلمة) لمتجر "مهووس للعطور" بلهجة سعودية عامية.
العميل: {persona['label']}، عمره {persona['age']}، من {persona['city']}.
أرجع JSON فقط: {{"rating":5,"text":"..."}}"""
    result = ai_call(prompt, 200)
    if not result: return {'rating':5,'text':'متجر ممتاز والعطور أصلية'}
    try: return json.loads(clean_json(result))
    except: return {'rating':5,'text':'متجر ممتاز والعطور أصلية'}

def gen_persona():
    arch = random.choice(ARCHETYPES)
    age = random.randint(*arch['age'])
    city = pick_city()
    key = 'male' if arch['g']=='male' else 'female'
    name = random.choice(NAMES.get(key,['مستخدم']))+' '+random.choice(NAMES.get('family_names',['السعودي']))
    perfumes = pick_products(arch)
    persona = {'name':name,'city':city,'gender':arch['g'],'age':age,'label':arch['label'],
               'emoji':arch['emoji'],'archId':arch['id'],'address':make_address(city),'phone':make_phone()}
    return persona, perfumes, arch

# ═══════════ CSS ═══════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
* { font-family: 'Tajawal', sans-serif !important; }
.main { direction: rtl; text-align: right; }
h1 { background: linear-gradient(135deg, #ddb562, #f4e4b0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
.persona-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(221,181,98,0.2); border-radius: 12px; padding: 16px; margin: 10px 0; }
.review-box { background: rgba(221,181,98,0.08); border-right: 3px solid #ddb562; padding: 10px 14px; margin: 6px 0; border-radius: 0 8px 8px 0; }
.stars { color: #ddb562; font-size: 14px; }
.product-tag { display: inline-block; background: rgba(221,181,98,0.15); color: #ddb562; padding: 2px 10px; border-radius: 20px; font-size: 13px; margin: 2px; }
.info-row { color: #9a9080; font-size: 14px; margin: 4px 0; }
.store-review { background: rgba(221,181,98,0.12); border: 1px solid rgba(221,181,98,0.3); border-radius: 10px; padding: 12px; margin: 8px 0; }
.copy-text { background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 6px; font-size: 13px; margin: 4px 0; direction: ltr; }
</style>
""", unsafe_allow_html=True)

# ═══════════ الواجهة ═══════════
st.markdown("<h1>🌸 مساعدي في شراء العطور</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:#9a9080;font-size:14px'>🧠 ذكاء اصطناعي • {len(PRODUCTS):,} عطر • لهجات سعودية • أرشيف ذكي ({len(load_archive().get('reviews',[]))} تقييم)</p>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: st.link_button("📧 بريد مؤقت", "https://boomlify.com/ar/dashboard")
with col2: st.link_button("🛒 مهووس", "https://mahwous.com")
with col3: st.link_button("📦 محلي", "http://localhost:5000")

st.divider()
count = st.selectbox("عدد الشخصيات:", [1,3,5,10], index=0)

if st.button("✨ ولّد شخصيات جديدة", type="primary", use_container_width=True):
    results = []
    progress = st.progress(0, text="جاري التوليد بالذكاء الاصطناعي...")
    for i in range(count):
        progress.progress((i)/count, text=f"🧠 شخصية {i+1} من {count}...")
        persona, perfumes, arch = gen_persona()
        reviews = gen_reviews(persona, perfumes)
        store = gen_store_review(persona)
        results.append({'persona':persona,'perfumes':perfumes,'reviews':reviews,'store':store})
    progress.progress(1.0, text=f"✅ {count} شخصية جاهزة!")
    st.session_state['results'] = results

if 'results' in st.session_state:
    for idx, r in enumerate(st.session_state['results']):
        p = r['persona']
        with st.container():
            st.markdown(f"""<div class="persona-card">
<h3>{p['emoji']} {p['name']}</h3>
<div class="info-row">📍 {p['city']} • {p['label']} • {p['age']} سنة</div>
<div class="info-row">📱 {p['phone']}</div>
<div class="info-row">🏠 {p['address']}</div>
</div>""", unsafe_allow_html=True)

            # نسخ البيانات
            copy_data = f"{p['name']}\n{p['phone']}\n{p['city']}\n{p['address']}"
            st.code(copy_data, language=None)

            # المنتجات
            st.markdown(f"**🧴 المنتجات ({len(r['perfumes'])})**")
            for pf in r['perfumes']:
                g_icon = '👨' if pf['g']=='رجالي' else '👩' if pf['g']=='نسائي' else '👤'
                st.markdown(f"<span class='product-tag'>{g_icon} {pf['name']} — {pf['price']} ر.س</span>", unsafe_allow_html=True)

            # التقييمات
            st.markdown("**💬 التقييمات**")
            for rv in r['reviews']:
                stars = '★' * rv.get('rating',5) + '☆' * (5-rv.get('rating',5))
                st.markdown(f"""<div class="review-box">
<div style="font-size:13px;color:#9a9080">{rv.get('product','')}</div>
<div class="stars">{stars}</div>
<div>{rv.get('text','')}</div>
</div>""", unsafe_allow_html=True)

            # تقييم المتجر
            s = r['store']
            s_stars = '★' * s.get('rating',5)
            st.markdown(f"""<div class="store-review">
<b>🏪 تقييم المتجر</b><br>
<span class="stars">{s_stars}</span> {s.get('text','')}
</div>""", unsafe_allow_html=True)

            st.divider()

    # مسح الأرشيف
    with st.expander("⚙️ إعدادات"):
        arc = load_archive()
        st.write(f"📦 الأرشيف: {len(arc.get('reviews',[]))} تقييم محفوظ")
        if st.button("🗑️ مسح الأرشيف"):
            save_archive({'reviews':[]})
            st.success("تم مسح الأرشيف")
            st.rerun()
