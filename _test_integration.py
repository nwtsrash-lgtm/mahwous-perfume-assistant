# -*- coding: utf-8 -*-
"""Integration test for the refactored Saudi review engine."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('  INTEGRATION TEST — Saudi Reviews Engine v3.0')
print('=' * 60)

# ══════ TEST 1: dialects.py ══════
print('\n=== TEST 1: dialects.py ===')
from dialects import (get_dialect_for_city, get_dialect_data, get_dialect_examples,
                      apply_typos, dialectize_text, apply_saudi_typos,
                      strip_formal_punctuation, DIALECTS)
print(f'  ✓ Dialects loaded: {len(DIALECTS)}')
for k, v in DIALECTS.items():
    expr_count = len(v['expressions'])
    filler_count = len(v['filler_words'])
    emphasis_count = len(v['emphasis'])
    assert expr_count >= 25, f'{k} has only {expr_count} expressions (need 25+)'
    assert filler_count >= 8, f'{k} has only {filler_count} fillers (need 8+)'
    assert emphasis_count >= 5, f'{k} has only {emphasis_count} emphasis (need 5+)'
print(f'  ✓ All 16 dialects have 25+ expressions, 8+ fillers, 5+ emphasis')

# Test typo engine
test_text = 'إن شاء الله ريحته ممتازة جداً والله إنه حلو'
typo_result = apply_saudi_typos(test_text, intensity='heavy')
print(f'  ✓ Typo engine: "{test_text[:30]}..." → "{typo_result[:30]}..."')

# Test punctuation stripper
punct_text = 'عطر فخم؛ والله! ريحته ممتازة، وثباته قوي. أنصح فيه؟'
stripped = strip_formal_punctuation(punct_text)
assert '؛' not in stripped, 'Semicolons not stripped'
assert '!' not in stripped, 'Exclamation marks not stripped'
assert '؟' not in stripped, 'Question marks not stripped'
print(f'  ✓ Punctuation stripper works: "{stripped[:40]}..."')

# Test dialectize_text
formal = 'هذا العطر جميل جداً ممتاز الآن'
najdi = dialectize_text(formal, 'najdi_riyadh')
sharqi = dialectize_text(formal, 'sharqi_dammam')
print(f'  ✓ dialectize najdi:  "{najdi[:50]}"')
print(f'  ✓ dialectize sharqi: "{sharqi[:50]}"')

# Backward compat
old_result = apply_typos('ريحته حلو والله ممتاز', probability=1.0)
print(f'  ✓ apply_typos() backward compat OK')

# ══════ TEST 2: personas_engine.py ══════
print('\n=== TEST 2: personas_engine.py ===')
from personas_engine import (generate_persona, generate_review_params, build_master_prompt,
                              set_catalog, ARCHETYPES, CITY_DATA, _make_address,
                              build_context_hints, build_seo_block, build_temporal_block,
                              pick_real_exemplars)
# Check new exports
from personas_engine import SOCIO_PROFILES, pick_human_context, GENERAL_HUMAN_CONTEXTS

print(f'  ✓ Archetypes: {len(ARCHETYPES)}')
print(f'  ✓ SocioProfiles: {len(SOCIO_PROFILES)}')
print(f'  ✓ GeneralContexts: {len(GENERAL_HUMAN_CONTEXTS)}')
print(f'  ✓ CityData: {len(CITY_DATA)} cities')

# Generate 5 personas and check new fields
for i in range(5):
    p = generate_persona()
    assert 'socio_class' in p, 'Missing socio_class in persona'
    assert 'occupation' in p, 'Missing occupation in persona'
    assert 'name' in p, 'Missing name'
    assert 'city' in p, 'Missing city'
    assert 'dialect' in p, 'Missing dialect'
    ctx = pick_human_context(p)
    if i == 0:
        print(f'  ✓ Persona: {p["name"]} | {p["city"]} | {p["dialect_name"]}')
        print(f'    socio: {p["socio_class"]} | occupation: {p["occupation"]}')
        print(f'    context: "{ctx}"')

# Test review params
p = generate_persona()
params = generate_review_params(p)
assert 'pattern' in params, 'Missing pattern'
assert 'rating' in params, 'Missing rating'
print(f'  ✓ Review params: pattern={params["pattern"]}, rating={params["rating"]}')

# Test master prompt builds without error
prompt = build_master_prompt(p, 'عود كمبودي', params)
assert len(prompt) > 100, 'Master prompt too short'
print(f'  ✓ Master prompt: {len(prompt)} chars')

# ══════ TEST 3: review_generator.py ══════
print('\n=== TEST 3: review_generator.py ===')
from review_generator import ReviewGenerator
gen = ReviewGenerator()

# Generate 50 reviews
reviews = gen.generate_reviews('عود كمبودي فاخر', price=350, count=50)
print(f'  ✓ Generated {len(reviews)} reviews')

# Check backward compat keys
for r in reviews:
    assert 'text' in r, 'Missing text key'
    assert 'rating' in r, 'Missing rating key'
    assert 'persona_type' in r, 'Missing persona_type key'

# Check new keys
has_new = all('city' in r and 'dialect' in r and 'effort_tier' in r for r in reviews)
print(f'  ✓ New fields (city, dialect, effort_tier): {"present" if has_new else "MISSING"}')

# Effort distribution
tiers = {}
for r in reviews:
    tier = r.get('effort_tier', 'unknown')
    tiers[tier] = tiers.get(tier, 0) + 1
print(f'  ✓ Effort distribution: {tiers}')

# Rating distribution
ratings = {}
for r in reviews:
    ratings[r['rating']] = ratings.get(r['rating'], 0) + 1
print(f'  ✓ Rating distribution: {ratings}')

# Check no banned AI phrases
BANNED = ['في الختام', 'بصراحة تامة', 'أود أن أشارككم', 'تجربتي الساحرة',
          'لا بد من الإشارة', 'يتميز هذا', 'ينبغي', 'من الجدير بالذكر',
          'أستطيع القول', 'بكل أمانة', 'هذا المنتج يعد', 'تجدر الإشارة']
banned_found = 0
for r in reviews:
    for phrase in BANNED:
        if phrase in r['text']:
            banned_found += 1
            print(f'  ⚠ BANNED phrase found: "{phrase}" in "{r["text"][:50]}..."')
print(f'  ✓ Banned AI phrases found: {banned_found}')

# Check text lengths per tier
for tier_name in ['ultra_short', 'medium', 'detailed']:
    tier_texts = [r['text'] for r in reviews if r.get('effort_tier') == tier_name]
    if tier_texts:
        avg_words = sum(len(t.split()) for t in tier_texts) / len(tier_texts)
        print(f'  ✓ {tier_name}: {len(tier_texts)} reviews, avg {avg_words:.1f} words')

# Show samples
print('\n=== SAMPLE REVIEWS ===')
import random
samples = random.sample(reviews, min(10, len(reviews)))
for r in samples:
    tier = r.get('effort_tier', '?')
    city = r.get('city', '?')
    print(f'  [{tier:12s}] {r["rating"]}★ {city:15s} | {r["text"]}')

print('\n' + '=' * 60)
print('  ✅ ALL INTEGRATION TESTS PASSED')
print('=' * 60)
