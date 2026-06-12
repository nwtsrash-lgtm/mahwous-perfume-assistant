# -*- coding: utf-8 -*-
"""نظام مكافحة التكرار المتقدم"""
import json, time, re
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARCHIVE_FILE = BASE_DIR / 'archive.json'
MAX_ARCHIVE = 200  # FIFO limit

def _load_archive():
    """تحميل الأرشيف"""
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'reviews':[], 'store_reviews':[], 'personas':[]}
    return {'reviews':[], 'store_reviews':[], 'personas':[]}

def _save_archive(archive):
    """حفظ الأرشيف مع FIFO"""
    # FIFO: keep only last MAX_ARCHIVE
    if len(archive.get('reviews', [])) > MAX_ARCHIVE:
        archive['reviews'] = archive['reviews'][-MAX_ARCHIVE:]
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive, f, ensure_ascii=False, indent=1)

def get_used_texts(limit=40):
    """آخر N نص مستخدم"""
    arc = _load_archive()
    texts = [r.get('text','') for r in arc.get('reviews',[])]
    return texts[-limit:] if len(texts) > limit else texts

def archive_review(review_text, product_name, persona_name):
    """حفظ تقييم واحد"""
    arc = _load_archive()
    arc['reviews'].append({
        'text': review_text,
        'product': product_name,
        'persona': persona_name,
        'ts': int(time.time())
    })
    _save_archive(arc)

def archive_batch(reviews, persona_name):
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

def clear_archive():
    """مسح الأرشيف"""
    _save_archive({'reviews':[], 'store_reviews':[], 'personas':[]})

def get_archive_stats():
    """إحصائيات الأرشيف"""
    arc = _load_archive()
    return {
        'total_reviews': len(arc.get('reviews',[])),
        'max_capacity': MAX_ARCHIVE,
        'last_10': [{'text':r['text'],'product':r.get('product',''),'persona':r.get('persona','')}
                    for r in arc.get('reviews',[])[-10:]]
    }

# --- Semantic Dedup ---
def _tokenize_arabic(text):
    """تفكيك النص العربي لكلمات"""
    text = re.sub(r'[^\u0600-\u06FF\s]', '', text)  # Arabic chars only
    return set(text.split())

def _jaccard_similarity(text1, text2):
    """حساب التشابه الدلالي بين نصين"""
    tokens1 = _tokenize_arabic(text1)
    tokens2 = _tokenize_arabic(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union) if union else 0.0

def is_duplicate(new_text, threshold=0.6):
    """هل النص مكرر دلالياً؟"""
    used = get_used_texts(limit=50)
    for old_text in used:
        if _jaccard_similarity(new_text, old_text) > threshold:
            return True
    return False

# --- Pattern Tracking ---
_pattern_counts = {}  # tracks pattern usage in current session

def track_pattern(pattern_name):
    """تتبع استخدام نمط"""
    global _pattern_counts
    _pattern_counts[pattern_name] = _pattern_counts.get(pattern_name, 0) + 1

def get_pattern_counts():
    """عدد مرات استخدام كل نمط"""
    return dict(_pattern_counts)

def reset_pattern_counts():
    """إعادة تعيين عداد الأنماط"""
    global _pattern_counts
    _pattern_counts = {}

def should_cooldown(pattern_name, max_consecutive=3):
    """هل يحتاج تبريد؟ بعد max_consecutive استخدام متتالي"""
    return _pattern_counts.get(pattern_name, 0) >= max_consecutive

# --- Cooldown for repeated adjectives ---
_adjective_counts = {}

def track_adjective(adj):
    """تتبع الصفة المستخدمة"""
    global _adjective_counts
    _adjective_counts[adj] = _adjective_counts.get(adj, 0) + 1

def needs_adjective_cooldown(adj, max_uses=3):
    """هل الصفة تحتاج تبريد؟"""
    return _adjective_counts.get(adj, 0) >= max_uses

def reset_adjective_counts():
    """إعادة تعيين عداد الصفات"""
    global _adjective_counts
    _adjective_counts = {}

def format_used_texts_block(limit=30):
    """تنسيق النصوص المستخدمة لإرسالها للـ AI"""
    used = get_used_texts(limit)
    if not used:
        return ''
    return '\n'.join([f'- {t}' for t in used])

# Standalone test
if __name__ == '__main__':
    print(f'✅ Anti-Repeat loaded')
    print(f'   Archive: {get_archive_stats()["total_reviews"]} reviews')
    print(f'   Max: {MAX_ARCHIVE}')
    t1 = 'عطر ممتاز وريحته حلوة'
    t2 = 'عطر ريحته حلوة وممتاز'
    print(f'   Similarity test: {_jaccard_similarity(t1, t2):.2f}')
    print(f'   Is duplicate: {is_duplicate(t1)}')
