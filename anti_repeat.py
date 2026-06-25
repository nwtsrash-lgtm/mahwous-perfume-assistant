# -*- coding: utf-8 -*-
"""نظام مكافحة التكرار المتقدم"""
import sys, os, json, time, re
from pathlib import Path
from collections import OrderedDict, deque

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get('DATA_DIR', str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_FILE = DATA_DIR / 'archive.json'
MAX_ARCHIVE = 500  # Updated to 500

TRACKED_WORDS = [
    # كلمات المديح المحترقة
    'فخم', 'فخمة', 'فخامة', 'يجنن', 'خرافي', 'رهيب', 'أسطوري',
    'جبار', 'دمار', 'بطل', 'خيال', 'خيالي', 'يهبل', 'هيبة',
    'روعة', 'روعه', 'واجد', 'شي ثاني', 'مو طبيعي',
    # كلمات الثبات
    'ثابت', 'ثباته', 'فواح', 'فوحان', 'يثبت', 'يفوح',
    # عبارات متكررة
    'أسرع من البرق', 'أسرع من هنقرستيشن', 'والله', 'والله العظيم',
    'يلفت الانتباه', 'شموخ', 'طول اليوم', 'مره حلو',
    # سياقات محترقة
    'شيبان المسجد', 'حارس العمارة', 'كل ما ألبسه', 'سألوني',
    'وقفني', 'يسأل', 'يسألني',
    # عبارات ختامية متكررة
    'ما راح أندم', 'أنصح فيه', 'لا يفوتكم', 'ما يطوفكم',
    'بطلب مره ثانية', 'صار المفضل', 'ما أستغني عنه',
    # وصف متكرر
    'يعبي المكان', 'يملى المكان', 'ريحة رجال', 'ريحة شيوخ',
    'ريحة ملوك', 'تحفة', 'إدمان', 'مدمن عليه',
]

# أنماط هيكلية متكررة يجب تتبعها
TRACKED_PATTERNS = [
    'كل ما ألبسه {شخص} يسألني',
    'وصلني أسرع من {شيء}',
    '{شخص} سألني وش عطرك',
    'جبته هدية ل{شخص} وفرح/ت فيه',
    'صار عطري اليومي',
    '{شخص} طلب الرابط',
    'ريحته {صفة} و{صفة}',
]

# سياقات مستخدمة يجب تبديلها
TRACKED_CONTEXTS = [
    'مسجد', 'حارس', 'عمارة', 'مصعد', 'سيارة', 'أوبر',
    'زواج', 'عزيمة', 'تخرج', 'مقابلة', 'دوام', 'جمعة',
    'نادي', 'سوق', 'مطعم', 'مقهى', 'طيارة', 'فندق',
]

_context_usage = deque(maxlen=50)
_pattern_structure_usage = deque(maxlen=30)

def _load_archive():
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'reviews':[], 'store_reviews':[], 'personas':[]}
    return {'reviews':[], 'store_reviews':[], 'personas':[]}

def _save_archive(archive):
    if len(archive.get('reviews', [])) > MAX_ARCHIVE:
        archive['reviews'] = archive['reviews'][-MAX_ARCHIVE:]
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive, f, ensure_ascii=False, indent=1)

def get_used_texts(limit=40):
    arc = _load_archive()
    texts = [r.get('text','') for r in arc.get('reviews',[])]
    return texts[-limit:] if len(texts) > limit else texts

def archive_review(review_text, product_name, persona_name):
    arc = _load_archive()
    arc['reviews'].append({
        'text': review_text,
        'product': product_name,
        'persona': persona_name,
        'ts': int(time.time())
    })
    _save_archive(arc)
    register_text(review_text, persona_name)

def archive_batch(reviews, persona_name):
    arc = _load_archive()
    for rv in reviews:
        arc['reviews'].append({
            'text': rv.get('text',''),
            'product': rv.get('product',''),
            'persona': persona_name,
            'ts': int(time.time())
        })
        register_text(rv.get('text', ''), persona_name)
    _save_archive(arc)

def clear_archive():
    _save_archive({'reviews':[], 'store_reviews':[], 'personas':[]})

def get_archive_stats():
    arc = _load_archive()
    return {
        'total_reviews': len(arc.get('reviews',[])),
        'max_capacity': MAX_ARCHIVE,
        'last_10': [{'text':r['text'],'product':r.get('product',''),'persona':r.get('persona','')}
                    for r in arc.get('reviews',[])[-10:]]
    }

def _normalize(text):
    if not text:
        return ''
    t = re.sub(r'[^؀-ۿ\s]', '', text)
    return re.sub(r'\s+', ' ', t).strip()

def _tokenize_arabic(text):
    text = re.sub(r'[^\u0600-\u06FF\s]', '', text)
    return set(text.split())

def _get_bigrams(text):
    tokens = text.split()
    return set(zip(tokens, tokens[1:]))

def _jaccard_similarity(text1, text2):
    tokens1 = _tokenize_arabic(text1)
    tokens2 = _tokenize_arabic(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union) if union else 0.0

def _bigram_overlap(text1, text2):
    b1 = _get_bigrams(text1)
    b2 = _get_bigrams(text2)
    return len(b1 & b2)

_session_norm = OrderedDict()
_session_recent = deque(maxlen=200)
_SESSION_CAP = 8000

# Burned Words tracking
_word_usage_history = deque(maxlen=20)
_persona_keywords = {}

def register_text(text, persona_name=None):
    n = _normalize(text)
    if not n:
        return
    _session_norm[n] = True
    _session_norm.move_to_end(n)
    while len(_session_norm) > _SESSION_CAP:
        _session_norm.popitem(last=False)
    _session_recent.append(text)
    
    # Track words for burnout
    _word_usage_history.append(text)
    
    # Track persona fingerprint
    if persona_name:
        if persona_name not in _persona_keywords:
            _persona_keywords[persona_name] = set()
        for w in TRACKED_WORDS:
            if w in text:
                _persona_keywords[persona_name].add(w)

def is_registered(text):
    return _normalize(text) in _session_norm

def reset_session_texts():
    _session_norm.clear()
    _session_recent.clear()
    _word_usage_history.clear()
    _persona_keywords.clear()

def is_duplicate(new_text, threshold=0.35, is_store_review=False):
    if not new_text or len(new_text.split()) < 3:
        return True # Empty or too short
        
    norm = _normalize(new_text)
    if not norm:
        return True
        
    if norm in _session_norm:
        return True
        
    for old in list(get_used_texts(limit=100)) + list(_session_recent):
        on = _normalize(old)
        if on and on == norm:
            return True
        if _jaccard_similarity(new_text, old) > threshold:
            return True
        if _bigram_overlap(new_text, old) >= 3:
            return True
            
    return False

def get_burned_words():
    """الكلمات المحروقة التي لا يجب استخدامها الآن"""
    burned = []
    text_history = " ".join(_word_usage_history)
    for w in TRACKED_WORDS:
        if text_history.count(w) >= 3:
            burned.append(w)
    return burned

def get_persona_fingerprint(persona_name):
    """الكلمات التي استخدمها الشخص سابقاً"""
    return list(_persona_keywords.get(persona_name, set()))

# --- Pattern Tracking ---
_pattern_counts = {}

def track_pattern(pattern_name):
    global _pattern_counts
    _pattern_counts[pattern_name] = _pattern_counts.get(pattern_name, 0) + 1

def get_pattern_counts():
    return dict(_pattern_counts)

def reset_pattern_counts():
    global _pattern_counts
    _pattern_counts = {}

def should_cooldown(pattern_name, max_consecutive=3):
    return _pattern_counts.get(pattern_name, 0) >= max_consecutive

# --- Cooldown for repeated adjectives ---
_adjective_counts = {}

def track_adjective(adj):
    global _adjective_counts
    _adjective_counts[adj] = _adjective_counts.get(adj, 0) + 1

def needs_adjective_cooldown(adj, max_uses=3):
    return _adjective_counts.get(adj, 0) >= max_uses

def reset_adjective_counts():
    global _adjective_counts
    _adjective_counts = {}

def track_context(context_type):
    """تسجيل استخدام سياق"""
    _context_usage.append(context_type)

def is_context_burned(context_type, lookback=15):
    """هل السياق مستخدم في آخر N تقييم؟"""
    recent = list(_context_usage)[-lookback:]
    return context_type in recent

def get_available_contexts(lookback=15):
    """السياقات المتاحة التي لم تُستخدم مؤخراً"""
    recent = set(list(_context_usage)[-lookback:])
    return [c for c in TRACKED_CONTEXTS if c not in recent]

def track_pattern_structure(structure):
    """تسجيل استخدام نمط هيكلي"""
    _pattern_structure_usage.append(structure)

def is_pattern_structure_burned(structure, lookback=10):
    """هل النمط الهيكلي مستخدم مؤخراً؟"""
    recent = list(_pattern_structure_usage)[-lookback:]
    return structure in recent

def extract_context_from_review(review_text):
    """استخراج السياق من نص التقييم"""
    for ctx in TRACKED_CONTEXTS:
        if ctx in review_text:
            return ctx
    return None

def extract_pattern_structure(review_text):
    """استخراج النمط الهيكلي من التقييم"""
    structures = []
    if any(w in review_text for w in ['سألني', 'يسألني', 'سألوني']):
        structures.append('compliment_question')
    if any(w in review_text for w in ['وصلني', 'وصل']):
        structures.append('delivery_comment')
    if any(w in review_text for w in ['جبته هدية', 'هديته', 'جبتها هدية']):
        structures.append('gift_story')
    if any(w in review_text for w in ['صار المفضل', 'صار عطري', 'ما أستغني']):
        structures.append('loyalty_declaration')
    if any(w in review_text for w in ['أول ما', 'لما جربته', 'أول ما رشيته']):
        structures.append('first_impression')
    return '_'.join(structures) if structures else 'generic'

def register_review_full(review_text, persona_name=None):
    """تسجيل كامل للتقييم: نص + سياق + نمط"""
    register_text(review_text, persona_name)
    
    # Track context
    ctx = extract_context_from_review(review_text)
    if ctx:
        track_context(ctx)
    
    # Track pattern structure
    structure = extract_pattern_structure(review_text)
    track_pattern_structure(structure)

def format_used_texts_block(limit=30, persona_name=None):
    used = get_used_texts(limit)
    burned = get_burned_words()
    fingerprint = get_persona_fingerprint(persona_name) if persona_name else []
    available_contexts = get_available_contexts()
    
    block = ""
    if used:
        block += "تقييمات سابقة (لا تكرر صياغتها أبداً):\n"
        block += '\n'.join([f'- {t}' for t in used]) + '\n'
        
    if burned:
        block += f"\nكلمات محظورة لأنها استخدمت بكثرة (ممنوع استخدامها نهائياً): {', '.join(burned)}\n"
        
    if fingerprint:
        block += f"\nهذا الشخص استخدم هذه الكلمات في تقييمات سابقة له، لا تجعله يكررها: {', '.join(fingerprint)}\n"
    
    if available_contexts:
        block += f"\nسياقات متاحة للاستخدام (اختر واحد فقط إذا احتجت): {', '.join(available_contexts[:5])}\n"
        
    return block

if __name__ == '__main__':
    print(f'✅ Anti-Repeat loaded')
    t1 = 'عطر ممتاز وريحته حلوة'
    t2 = 'عطر ريحته حلوة وممتاز'
    print(f'   Similarity test: {_jaccard_similarity(t1, t2):.2f}')
    print(f'   Is duplicate: {is_duplicate(t1)}')
