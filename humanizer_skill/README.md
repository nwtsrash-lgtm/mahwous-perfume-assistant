# طبقة الأنسنة (Humanizer) — الدمج في مشروع «مساعد شراء العطور»

هذا المجلّد يحتفظ بالمصدر المرجعي لمهارة **Signs of AI writing** (`SKILL.md`،
ترخيص MIT، انظر `LICENSE`) كـ«مواصفة تصميم» فقط. المنطق التنفيذي الفعلي في
[`../humanizer.py`](../humanizer.py).

## لماذا لم نستورد الأنماط الـ33 حرفياً؟

`SKILL.md` مكتوب لتنظيف **مقالات إنجليزية طويلة** (شرطة `—`، «vibrant tapestry»،
تجنّب copula، Title Case...). مشروعنا يولّد **مراجعات عطور سعودية قصيرة جداً**:
من ٤٥٢ عيّنة طول حقيقية، **٦٤٪ ≤ ٣ كلمات** و~٨٥٪ ≤ ٦ كلمات. تطبيق منظّف مقالات
حرفياً على مراجعة من كلمتين = سوء مطابقة يشوّه النص، ويصطدم بقسم *DETECTION
GUIDANCE* في المهارة نفسها الذي يحذّر من «الإيجابيات الكاذبة».

لذلك ترجمنا **الأنماط القابلة للنقل** إلى الواقع العربي، وتركنا ما لا ينطبق.

## خريطة أنماط SKILL → التنفيذ في humanizer.py

| نمط SKILL (الإنجليزي) | المعالجة عندنا |
|---|---|
| §4 Promotional language, §7 AI vocabulary, §32 Aphorisms | `AR_MARKETING_TELLS` — مبالغات **إعلانية فصيحة** («يخطف الأنفاس»، «منقطع النظير»، «تحفة فنية»). كشف + منع بالبرومبت، **لا حذف** |
| §20 Collaborative artifacts, §22 Sycophancy | `AR_CHATBOT_ARTIFACTS` — «إليك تقييمي»، «يسعدني»، «بالطبع». تُزال من الأطراف بأمان |
| §28 Signposting | `AR_SIGNPOSTING` — «دعونا نستعرض» |
| §25 Generic positive conclusions | `AR_GENERIC_CLOSERS` — «أنصح الجميع بتجربته»، «في الختام» |
| §10 Rule of three | `_RULE_OF_THREE_RE` — كشف في النص الأطول فقط |
| §14 Em dashes, §15 Boldface, §16 Inline lists, §17 Title case, §18 Emojis, §19 Curly quotes | `strip_typographic` + `strip_emoji` — زخرفة غير محتوى، تُزال بأمان |
| Voice Calibration (اختياري) | `voice_calibration_block()` — يتعلّم من `real_reviews_bank` + مراجعات المنافسين المكشوطة (خط `mahalli`) |

## القرار المعماري (تمييز الجودة)

**حماس اللهجة السعودية الأصيل ليس بصمة ذكاء اصطناعي.** المراجعات الحقيقية مليئة بـ
«خرافي»، «يجنّن»، «رهيب»، «يستاهل». الفلتر يستهدف **السجلّ الإعلاني الفصيح** حصراً،
ولا يمسّ حماس العامية — تماماً كما يوصي قسم «Signs of human writing» في المهارة.

## الطبقات الثلاث ونقاط التوصيل

1. **استباقي (أفضل رافعة):** `anti_tell_line()` + `voice_calibration_block()` تُحقَنان في
   - `personas_engine.build_master_prompt` (مسار المراجعات، length-aware)
   - `store_review.build_store_prompt` (مسار المتجر — يرثه Flask وStreamlit)
2. **كشف:** `content_tells()` تُغذّي حلقات إعادة التوليد في الحُرّاس القائمة
   (`app.py._write_review`, `_ai_store_review`, ونظائرها في `streamlit_app.py`).
3. **تنظيف (Middleware):** `humanize_output()` هو المدخل الموحّد — يمرّ عليه كل نص
   قبل `_humanize` في كلا التطبيقين.

المصدر الأصلي: <https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>
