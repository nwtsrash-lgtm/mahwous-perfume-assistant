# -*- coding: utf-8 -*-
"""اختبارات طبقة الأنسنة humanizer — كشف/تنظيف/معايرة صوت + ضمانات السلامة."""
import humanizer as hz


# ═══════════ الكشف ═══════════
def test_detect_marketing_register():
    tells = hz.detect('عطر تحفة فنية يخطف الأنفاس')
    assert 'مبالغة دعائية فصحى' in tells


def test_detect_chatbot_artifact():
    assert 'آثار مساعد آلي' in hz.detect('إليك تقييمي عن العطر')


def test_detect_generic_closer():
    assert 'خاتمة تحفيزية عامة' in hz.detect('ريحته حلوة أنصح الجميع بتجربته')


def test_detect_emoji_and_markdown_and_dash():
    tells = hz.detect('عطر **رائع** — جميل 🔥')
    assert 'إيموجي/رموز' in tells
    assert 'شرطة AI (—)' in tells
    assert 'زخرفة ماركداون' in tells


def test_clean_input_has_no_tells():
    assert hz.detect('ثباته حلو وريحته فخمة') == []


# ═══════════ الفلسفة: حماس اللهجة ليس بصمة AI ═══════════
def test_dialect_enthusiasm_not_flagged():
    for real in ['ثباته خرافي ويجنّن', 'ريحته تجنن', 'فوحانه رهيب', 'يستاهل كل ريال']:
        assert hz.detect(real) == [], f'حماس عامية اعتُبر بصمة: {real}'


def test_dialect_enthusiasm_untouched_by_clean():
    s = 'ثباته خرافي ويجنّن'
    assert hz.clean(s) == s


# ═══════════ التنظيف ═══════════
def test_clean_strips_emoji():
    assert '🔥' not in hz.clean('ريحته حلوة 🔥🌟')
    assert 'ريحته حلوة' in hz.clean('ريحته حلوة 🔥🌟')


def test_clean_strips_chatbot_frame():
    out = hz.clean('إليك تقييمي: العطر ثباته ممتاز')
    assert out.startswith('العطر') or 'العطر ثباته ممتاز' in out
    assert 'إليك' not in out


def test_clean_strips_trailing_closer():
    out = hz.clean('ريحته فخمة وثباته قوي طول اليوم في الختام أنصح الجميع بتجربته')
    assert 'أنصح الجميع بتجربته' not in out
    assert 'ريحته فخمة' in out


def test_clean_strips_markdown_bold():
    assert '*' not in hz.clean('عطر **رائع** وثابت')


def test_clean_converts_em_dash():
    assert '—' not in hz.clean('عطر جميل — وثابت')


def test_clean_converts_curly_quotes():
    out = hz.clean('قال “ممتاز” عنه')
    assert '“' not in out and '”' not in out


# ═══════════ ضمانات السلامة (قانون-4) ═══════════
def test_clean_never_empties_nonempty():
    # نص كله «إطار» — يجب ألا يُفرَّغ
    for s in ['إليك', 'بالطبع', 'تحفة فنية', 'أنصح الجميع بتجربته', '🔥', 'دعني']:
        assert hz.clean(s).strip(), f'أُفرِغ نص غير فارغ: {s!r}'


def test_clean_empty_stays_empty():
    assert hz.clean('') == ''
    assert hz.clean('   ') == ''


def test_clean_preserves_content_words_of_marketing():
    # المبالغة لا تُحذف (تُمنع بالبرومبت) — التنظيف محافظ
    out = hz.clean('العطر تحفة فنية')
    assert 'العطر' in out and 'تحفة' in out


def test_micro_review_only_safe_ops():
    # مراجعة قصيرة عادية تمرّ بلا تغيير جوهري
    assert hz.clean('ريحته تدوم طويل') == 'ريحته تدوم طويل'


# ═══════════ معايرة الصوت ═══════════
def test_voice_block_review_nonempty():
    blk = hz.voice_calibration_block(kind='review', gender='male', n=4)
    assert blk and 'اكتب' in blk


def test_voice_block_store_uses_bank():
    blk = hz.voice_calibration_block(kind='store', n=4)
    assert isinstance(blk, str)  # قد يكون فارغاً بأمان إن غاب البنك، لكن لا يرمي


def test_voice_block_gender_female():
    blk = hz.voice_calibration_block(kind='review', gender='أنثى', n=3)
    assert isinstance(blk, str)


def test_anti_tell_line_compact():
    line = hz.anti_tell_line()
    assert 'إعلان' in line and 'يخطف الأنفاس' in line


def test_scraped_voices_loaded_and_clean():
    # عيّنة الصوت الحقيقية يجب ألا تحوي مبالغات دعائية (كي لا نعلّم البوت بصمته)
    voices = hz._load_scraped_voices()
    assert len(voices) > 50
    for v in voices[:200]:
        assert not hz._MARKETING_RE.search(v)


# ═══════════ content_tells (تنجو من _humanize) ═══════════
def test_content_tells_excludes_typographic():
    # إيموجي/شرطة/ماركداون ليست علامات محتوى (يزيلها التنظيف)
    ct = hz.content_tells('عطر **رائع** 🔥 يخطف الأنفاس')
    assert 'إيموجي/رموز' not in ct
    assert 'مبالغة دعائية فصحى' in ct


def test_stats_shape():
    s = hz.stats()
    assert s['marketing_tells'] > 20 and s['scraped_voices'] >= 0


# ═══════════ تكرار كلمة محورية (قوالب ملتصقة / سهو الـAI) ═══════════
def test_detect_nonadjacent_word_repeat():
    tells = hz.detect(
        'المقدمه فريشه والقلب زهري والقاعده مسك أبيض المقدمه حاره شوي والقلب ناعم'
    )
    assert 'تكرار كلمة محورية' in tells


def test_repeat_detection_is_content_tell():
    ct = hz.content_tells(
        'ثباته على الجلد أقل شوي بس على القماش وحش أنصح فيه خلوه بقائمتكم ثباته يختلف حسب البشره'
    )
    assert 'تكرار كلمة محورية' in ct


def test_adjacent_repeat_not_flagged():
    # «فخم فخم» تشديد لهجة مقصود ومعاير على بيانات منافسين حقيقية — ليس عيباً
    assert hz.detect('فخم فخم بمعنى الكلمة والله صراحه') == []


def test_single_mention_not_flagged():
    # ذكر عادي لكلمة («يهبل») مرة واحدة يجب ألا يُحسب تكراراً
    assert hz.detect('هذا العطر يهبل صراحه وريحته حلوة جدا ما توقعت يكون بهالجوده') == []


def test_repeat_not_flagged_on_micro_review():
    # المايكرو-مراجعة (≤6 كلمات) لا تخضع لفحص التكرار — لا معنى له بهالطول
    assert hz.detect('يهبل ويفوز يهبل') == []
