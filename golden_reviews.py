# -*- coding: utf-8 -*-
"""بنك التقييمات الذهبية — 120+ تقييم بجودة بشرية حقيقية
كل تقييم = قصة مصغرة بتفاصيل حقيقية وعاطفة صادقة
"""
import random

# ═══════════════════════════════════════════════════════════
#  التقييمات الذهبية — مرتبة حسب نوع القصة
# ═══════════════════════════════════════════════════════════

GOLDEN_REVIEWS = [
    # ══════════════════════════════════════════
    #  القسم 1: أول مرة أطلب (first_time) — 15 تقييم
    #  القوس العاطفي: تردد → مفاجأة → ثقة
    # ══════════════════════════════════════════
    {
        'text': 'كنت متردد أطلب عطر أونلاين أول مرة بس لما وصل الطلب وشفت التغليف والكرت الشخصي حسيت إني تعاملت مع ناس يهتمون مو بس متجر',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'remove_fear',
    },
    {
        'text': 'أول تجربة لي أطلب عطر من النت وأنا خايف يطلع مزيف بس الباركود طابق والسيريال واضح ارتحت وبطلب مرة ثانية',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'male',
        'marketing_goal': 'remove_fear',
    },
    {
        'text': 'صاحبتي نصحتني أجرب وأنا مترددة بس والله ما ندمت أحلى قرار',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'female',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'شفته بتيك توك وقلت أجرب ما توقعت يكون بهالمستوى بصراحة فاق توقعاتي',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'create_desire',
    },
    {
        'text': 'خذته من غير ما أشمه بناء على التقييمات وما خاب ظني',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'ما كنت أعرف المتجر بس صاحبي أرسل لي الرابط وقال جرب ما راح تندم جربت وفعلا ما ندمت',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'طلبته وأنا مسافر ولما رجعت لقيته عند الباب التوصيل كان أسرع مني',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'male',
        'marketing_goal': 'fast_delivery',
    },
    {
        'text': 'قارنت أسعاره مع 3 متاجر ثانية ولقيته الأرخص وأصلي طلبت بدون تفكير',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'price_value',
    },
    {
        'text': 'ما توقعت إن متجر أونلاين يهتم بالتفاصيل كذا حتى الكرتون مغلف بشكل يصلح هدية',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'quality_packaging',
    },
    {
        'text': 'أول عطر أشتريه من النت وصل بيومين مع عينتين مجانية لمسة حلوة',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'fast_delivery',
    },
    {
        'text': 'جربت أطلب بعد ما شفت ريفيو بالانستقرام وفعلا نفس اللي وصفوه',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'female',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'استخدمت تابي وطلبت ووصل قبل الموعد كل شي سهل',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'both',
        'marketing_goal': 'easy_purchase',
    },
    {
        'text': 'كنت بأخذه من السوق بس لقيته عندهم أرخص بـ 80 ريال وأصلي مئة بالمئة',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'male',
        'marketing_goal': 'price_value',
    },
    {
        'text': 'أعترف كنت أشك بس العطر أصلي والتغليف أفضل من اللي اشتريته من المحل',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'male',
        'marketing_goal': 'remove_fear',
    },
    {
        'text': 'بنتي قالت لي ماما اطلبي من هالمتجر أنا طلبت منهم قبل ومدحتهم لي وفعلا صدقت',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'first_time_buyer', 'gender': 'female',
        'marketing_goal': 'family_recommendation',
    },

    # ══════════════════════════════════════════
    #  القسم 2: هدية لشخص عزيز (gift) — 15 تقييم
    #  القوس العاطفي: حب → ترقب → سعادة المُهدى له
    # ══════════════════════════════════════════
    {
        'text': 'جبته هدية لأمي بعيد ميلادها ولما شمته قالت يذكرني بريحة أمك الله يرحمها ما شفت أمي تفرح بهدية زي كذا',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'male',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'أخذته هدية لزوجي بعيد زواجنا ولما فتحه ابتسم وقال هذا ذوقك من يوم عرفتك',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'هديته لخويي بتخرجه وفرح فيه مرة وقال أحسن هدية جتني',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'gift_giver', 'gender': 'male',
        'marketing_goal': 'gift_idea',
    },
    {
        'text': 'جبته لأختي الصغيرة وكل يوم ترسل لي سناب وهي ترشه',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'gift_idea',
    },
    {
        'text': 'أبوي ما يحب أحد يختار له بس لما شم هالعطر قال زين اخترت',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'both',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'طلبته هدية مع التغليف الخاص وصل بكيس فخم جاهز للإهداء ما احتجت أسوي شي',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'gift_giver', 'gender': 'both',
        'marketing_goal': 'quality_packaging',
    },
    {
        'text': 'هديته لزوجتي وبعدها بأسبوع لقيتها طالبة نفسه لأمها من نفس المتجر',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'male',
        'marketing_goal': 'viral_recommendation',
    },
    {
        'text': 'شريته لولدي اللي يتخرج وحطيته بالسيارة مع بوكيه ورد ولما فتحه دمعت عينه',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'كل سنة أهدي أبوي عطر وهالسنة اختلفت وطلبت من هنا وقال لي أحسن عطر أهديتني',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'gift_giver', 'gender': 'both',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'خويي تزوج وكنت أدور هدية مميزة شفته وطلبته وقال لي بالحفل هذا أحسن شي وصلني',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'gift_giver', 'gender': 'male',
        'marketing_goal': 'gift_idea',
    },
    {
        'text': 'جبتها هدية لصاحبتي وبعد يومين رسلت لي رابط المتجر تقول أبي أطلب لنفسي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'viral_recommendation',
    },
    {
        'text': 'أخذته كهدية بدون مناسبة بس عشان أسعد أمي وفعلا سعدت وصارت ترش منه كل يوم',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'both',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'طلبت 3 حبات هدايا للعيد لأخواتي وكل وحدة فرحت بس الكبيرة قالت وش المتجر أبي أطلب زيادة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'viral_recommendation',
    },
    {
        'text': 'هديته لمعلمتي آخر يوم دراسة وقالت أحلى هدية السنة',
        'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'gift_giver', 'gender': 'female',
        'marketing_goal': 'gift_idea',
    },
    {
        'text': 'الوالد يحب العود بس جبت له هالعطر يجربه وصار يلبسه للدوام كل يوم',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'gift_giver', 'gender': 'both',
        'marketing_goal': 'convert_traditional',
    },

    # ══════════════════════════════════════════
    #  القسم 3: لحظات اجتماعية (social_moment) — 15 تقييم
    #  القوس العاطفي: رش العطر → تفاعل اجتماعي → فخر
    # ══════════════════════════════════════════
    {
        'text': 'رحت العزيمة عند خالي ورشيته وأبوي اللي عمره ما يعلق على شي قال وش هالريحة الحلوة يا ولدي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'زميلتي بالدوام كل يوم تسألني وش عطرك وأنا أصرفها لأني ما أبي نفس الريحة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'female',
        'marketing_goal': 'exclusivity',
    },
    {
        'text': 'كابتن أوبر وقفني مخصوص وقال بالله وش عطرك أرسل لي الرابط',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'دخلت الاجتماع ورشيته قبلها بنص ساعة والمدير قال ريحة حلوة وش السر',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'confidence',
    },
    {
        'text': 'لبسته لحفلة التخرج وبنات دفعتي كلهم يرسلون بالقروب يسألون وش العطر',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'female',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'محاسب بندة سألني عن عطري وهو يحاسبني الحين صار يلبسه',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'دخلت المصعد وطلعت واللي دخل بعدي لحقني للموقف يسأل عن العطر',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'sillage',
    },
    {
        'text': 'بيوم الجمعة رشيته للصلاة واللي جنبي بالصف قال ما شاء الله ريحة طيبة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'كنت بالمقهى وصاحبتي شمتني وطلبت نفسه من نفس المتجر وهي جالسة جنبي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'female',
        'marketing_goal': 'viral_purchase',
    },
    {
        'text': 'زوجتي من النوع اللي ما تمدح بس لما رشيته قالت لي اليوم ريحتك حلوة هذا أكبر مديح',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'ولدي الصغير كل ما أرش عطر يقول ماما حلوة ريحتك وهذا العطر أكثر واحد يحبه',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'female',
        'marketing_goal': 'emotional_connection',
    },
    {
        'text': 'رجعت من الاستراحة والشباب يرسلون بالواتساب يطلبون الرابط',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'viral_recommendation',
    },
    {
        'text': 'بنت أختي شمت عبايتي وقالت خالتي وش تحطين ريحتك دايم حلوة أرسلت لها الرابط',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'female',
        'marketing_goal': 'viral_recommendation',
    },
    {
        'text': 'أخوي سرق العطر من غرفتي واضطريت أطلب واحد ثاني',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'male',
        'marketing_goal': 'social_proof',
    },
    {
        'text': 'بالعيد الكل سأل وش عطرك وأنا بس أبتسم',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'social_moment', 'gender': 'both',
        'marketing_goal': 'exclusivity',
    },

    # ══════════════════════════════════════════
    #  القسم 4: عميل عائد (returning_customer) — 15 تقييم
    #  القوس العاطفي: ثقة → ولاء → توصية
    # ══════════════════════════════════════════
    {
        'text': 'خامس طلب لي من مهووس وكل مرة التعامل يتحسن آخر مرة حطوا كرت شكر مكتوب باليد هالشي يخليك تحب المتجر',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'male',
        'marketing_goal': 'loyalty',
    },
    {
        'text': 'ثاني قارورة أطلبها من نفس العطر خلصت الأولى بـ 4 شهور يعني فعلا يستاهل',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'repurchase_proof',
    },
    {
        'text': 'من يوم عرفت مهووس مقاطع محلات المولات توفر أكثر والعطور أصلية مئة بالمئة',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'male',
        'marketing_goal': 'defection_story',
    },
    {
        'text': 'رابع مرة أطلب والحين صرت أوصي كل أحد فيهم',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'loyalty',
    },
    {
        'text': 'ثالث طلب وكالعادة يوصل بسرعة ومغلف بطريقة تخليك تحس إنهم يهتمون فيك',
        'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'loyalty',
    },
    {
        'text': 'صرت أعرف روتينهم بالتوصيل أطلب السبت يوصل الاثنين دايم على الموعد',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'male',
        'marketing_goal': 'reliability',
    },
    {
        'text': 'كل ما نزل عطر جديد عندهم أطلبه على طول صرت أثق باختياراتهم',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'female',
        'marketing_goal': 'trust_curation',
    },
    {
        'text': 'مرة غلطوا بالطلب واتصلت فيهم ردوا لي فلوسي وأرسلوا الصح مع هدية اعتذار هالشي يخلي العميل يرجع',
        'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'service_recovery',
    },
    {
        'text': 'عندي اشتراك معهم بالعروض وكل مرة يجيني خصم حصري ما يجي لغيري',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'female',
        'marketing_goal': 'exclusivity',
    },
    {
        'text': 'سادس عطر أطلبه منهم ولا مرة وحدة ندمت على شي',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'male',
        'marketing_goal': 'loyalty',
    },
    {
        'text': 'كنت أشتري من متجر ثاني بس من يوم جربت مهووس ما رجعت',
        'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'defection_story',
    },
    {
        'text': 'حتى لما طلبت بالتقسيط كان الموضوع سهل ومريح تابي وخلاص',
        'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'easy_purchase',
    },
    {
        'text': 'كل طلب يجيني فيه عينة جديدة أجربها وبسببها اكتشفت عطور ما كنت بأشتريها',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'female',
        'marketing_goal': 'discovery',
    },
    {
        'text': 'تواصلت معهم بالواتساب يسألون عن ذوقي ونصحوني بعطر ما كنت أعرفه وطلع أحلى شي عندي',
        'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'returning_customer', 'gender': 'female',
        'marketing_goal': 'personal_service',
    },
    {
        'text': 'خلاص صرت زبون دائم ما أفكر وين أطلب',
        'rating': 5, 'type': 'store', 'stage': 'ambassador',
        'story_type': 'returning_customer', 'gender': 'both',
        'marketing_goal': 'loyalty',
    },

    # ══════════════════════════════════════════
    #  القسم 5: الصديق الصادق (honest_friend) — 20 تقييم
    #  3-4 نجوم — صادق بس ما ينفّر
    # ══════════════════════════════════════════
    {
        'text': 'بكون صريح العطر مو الأقوى ثبات لكن ريحته فيها شي يخليك تبتسم لو تحب الهادية هذا حقك',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'trust',
    },
    {
        'text': 'ريحته تسوى كل ريال بس لو أكون صادق يبي تجديد بعد 4 ساعات على الجلد على الثوب بطل يمسك لليوم الثاني',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'honest_value',
    },
    {
        'text': 'حلو للدوام بس لو تبيه حق مناسبة تبي شي أقوى منه بصراحة',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'use_case',
    },
    {
        'text': 'العطر ممتاز بالشتاء بس بالصيف يتبخر بسرعة يبي تجربه بالوقت المناسب',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'seasonal_advice',
    },
    {
        'text': 'الريحة حلوة أول ساعتين بعدها تصير سكن سنت على الجلد بس على القماش تمسك أكثر',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'usage_tip',
    },
    {
        'text': 'عندي أكثر من 20 عطر وهذا دخل التوب 5 مو لأنه الأقوى بس لأنه الأكثر تنوع ينفع لكل شي',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'expert_endorsement',
    },
    {
        'text': 'لو تبي عطر يومي خفيف ما يزعج أحد هذا هو بس لو تبي ثقيل للمناسبات شوف غيره',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'use_case',
    },
    {
        'text': 'جربته أسبوعين وحسيته يتغير على بشرتي بس على ملابسي ثابت ومميز',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'female',
        'marketing_goal': 'body_chemistry',
    },
    {
        'text': 'السعر ممتاز والريحة حلوة بس الحجم أتمنى لو كان أكبر شوي',
        'rating': 4, 'type': 'product', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'honest_value',
    },
    {
        'text': 'التغليف كان بسيط شوي بس العطر نفسه ممتاز يستاهل كل ريال',
        'rating': 4, 'type': 'product', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'honest_value',
    },
    {
        'text': 'يمكن ذوقي مختلف بس توقعته أقوى من كذا بكثير لكن التعامل مع المتجر كان ممتاز ردوا لي فلوسي بدون تعقيد',
        'rating': 2, 'type': 'product', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'service_recovery',
    },
    {
        'text': 'ما ناسب بشرتي بس أعرف إنه حلو لأن زوجي يلبس نفسه ويثبت عليه',
        'rating': 3, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'female',
        'marketing_goal': 'body_chemistry',
    },
    {
        'text': 'الفوحان أول ساعة قوي مرة بعدها يهدى ويصير ناعم وهادي أنا أحبه كذا بس اللي يبي قوي طول الوقت يمكن ما يناسبه',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'scent_evolution',
    },
    {
        'text': 'توقعت يكون أثقل من كذا بصراحة بس ريحته لطيفة وما تزعج أحد',
        'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'manage_expectations',
    },
    {
        'text': 'حلو بسعره ما أقول لا بس فيه عطور أثبت بنفس الفئة السعرية',
        'rating': 3, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'male',
        'marketing_goal': 'honest_comparison',
    },
    {
        'text': 'التوصيل تأخر يومين عن الموعد بس العطر وصل سليم والريحة تستاهل الانتظار',
        'rating': 4, 'type': 'store', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'balanced_store',
    },
    {
        'text': 'الكرتون كان كبير على الفاضي بس العطر جا سليم وما انكسر',
        'rating': 4, 'type': 'store', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'balanced_store',
    },
    {
        'text': 'ريحته عادية مو سيئة بس ما فيها شي مميز يخليك تقول واو',
        'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'honest_value',
    },
    {
        'text': 'العطر نفسه حلو بس تأخروا بالشحن وما تواصلوا معي كان ودي لو يرسلون تحديث',
        'rating': 3, 'type': 'store', 'stage': 'first_time',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'constructive_feedback',
    },
    {
        'text': 'مو سيء بس عندي عطور أحسن منه بنفس السعر برضو من نفس المتجر',
        'rating': 3, 'type': 'product', 'stage': 'returning',
        'story_type': 'honest_friend', 'gender': 'both',
        'marketing_goal': 'cross_sell_hint',
    },

    # ══════════════════════════════════════════
    #  القسم 6: قصيرة وكسولة (lazy) — 20 تقييم
    #  1-4 كلمات — كأن الشخص مستعجل
    # ══════════════════════════════════════════
    {
        'text': 'ممتاز', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'يستاهل', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'والله حلو', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'وصل سليم', 'rating': 5, 'type': 'store', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'delivery_confirm',
    },
    {
        'text': 'تمام وصل', 'rating': 5, 'type': 'store', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'delivery_confirm',
    },
    {
        'text': 'زين', 'rating': 4, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'عادي', 'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'neutral',
    },
    {
        'text': 'حلو واجد', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'ريحته حلوة', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'مو سيء', 'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'neutral',
    },
    {
        'text': 'يمشي الحال', 'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'neutral',
    },
    {
        'text': 'شكرا مهووس', 'rating': 5, 'type': 'store', 'stage': 'returning',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'store_mention',
    },
    {
        'text': 'بطلب مره ثانيه', 'rating': 5, 'type': 'store', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'repurchase_intent',
    },
    {
        'text': 'أنصح فيه', 'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'recommendation',
    },
    {
        'text': 'نظيف وخفيف', 'rating': 4, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'يثبت طول اليوم', 'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'performance',
    },
    {
        'text': 'ما يخيب', 'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'reliability',
    },
    {
        'text': 'جميل', 'rating': 5, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'quick_positive',
    },
    {
        'text': 'الله يعطيكم العافية', 'rating': 5, 'type': 'store', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'gratitude',
    },
    {
        'text': 'مقبول', 'rating': 3, 'type': 'product', 'stage': 'first_time',
        'story_type': 'lazy', 'gender': 'both', 'marketing_goal': 'neutral',
    },

    # ══════════════════════════════════════════
    #  القسم 7: تجربة حسية (sensory_journey) — 10 تقييم
    #  وصف تطور العطر عبر الساعات
    # ══════════════════════════════════════════
    {
        'text': 'أول ما رشيته فاحت ريحة حمضيات منعشة بعد نص ساعة طلع الورد والزعفران وبعد 4 ساعات صار عود ناعم ودافئ قصة كاملة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'male',
        'marketing_goal': 'scent_education',
    },
    {
        'text': 'ريحته تبدأ قوية وبعد ساعة تهدى وتصير هادية وناعمة هالتحول هو سر جماله',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'both',
        'marketing_goal': 'scent_evolution',
    },
    {
        'text': 'على الجلد يعطي ريحة مسك ناعمة بس على القماش يصير أقوى وأعمق جربوا على الشماغ',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'male',
        'marketing_goal': 'usage_tip',
    },
    {
        'text': 'بخة وحدة على المعصم كافية ليوم كامل ما يبي مبالغة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'both',
        'marketing_goal': 'value_longevity',
    },
    {
        'text': 'ثباته 8 ساعات على الجلد ويوم كامل على الثوب فوحانه متر ونص تقريبا',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'male',
        'marketing_goal': 'performance_data',
    },
    {
        'text': 'بالصيف يتبخر أسرع بس ريحته المنعشة تسوى بالشتا يكون أثقل وأدفى',
        'rating': 4, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'both',
        'marketing_goal': 'seasonal_advice',
    },
    {
        'text': 'السر إنك ترشه على نقاط النبض المعصم والرقبة وتخلي الباقي يفوح طبيعي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'both',
        'marketing_goal': 'usage_tip',
    },
    {
        'text': 'جربت أخلطه مع رشة مسك الختام والنتيجة كانت شي ثاني بالمعنى الحرفي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'male',
        'marketing_goal': 'layering_cross_sell',
    },
    {
        'text': 'بشرتي دهنية والعطور عادة ما تمسك بس هذا ثبت 6 ساعات ما صدقت',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'female',
        'marketing_goal': 'body_chemistry',
    },
    {
        'text': 'ريحته على الشعر شي ثاني تفوح مع الحركة وتمسك لليوم الثاني',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'sensory_journey', 'gender': 'female',
        'marketing_goal': 'usage_tip',
    },

    # ══════════════════════════════════════════
    #  القسم 8: الروتين اليومي (daily_ritual) — 10 تقييم
    #  العطر كجزء من الحياة اليومية
    # ══════════════════════════════════════════
    {
        'text': 'صار عطري حق الدوام كل صباح نفس البخة ونفس الإحساس بالثقة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'daily_essential',
    },
    {
        'text': 'حطيته بالسيارة وصرت كل ما أركب ريحته تبدأ يومي بطريقة حلوة',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'daily_ritual', 'gender': 'male',
        'marketing_goal': 'daily_essential',
    },
    {
        'text': 'طالبة 3 حبات وحدة بالشنطة ووحدة بالبيت ووحدة بالسيارة ما أقدر أكون بدونه',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'female',
        'marketing_goal': 'multiple_purchase',
    },
    {
        'text': 'من 6 شهور وأنا ألبسه كل يوم وما مليت منه',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'longevity_love',
    },
    {
        'text': 'صار ريحتي المعروفة الناس تعرفني فيه',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'signature_scent',
    },
    {
        'text': 'أرشه بعد الوضوء وقبل ما أروح الدوام صار جزء من روتيني الصباحي',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'daily_ritual', 'gender': 'male',
        'marketing_goal': 'daily_essential',
    },
    {
        'text': 'خلصت العلبة الأولى بـ 3 شهور وطلبت الثانية على طول هذا دليل',
        'rating': 5, 'type': 'product', 'stage': 'returning',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'repurchase_proof',
    },
    {
        'text': 'لي سنة أستخدمه ولسا ما لقيت بديل',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'irreplaceable',
    },
    {
        'text': 'حتى بإجازتي السبت أرشه لو ما طلعت من البيت صار إدمان',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'addiction',
    },
    {
        'text': 'عطري حق البيت والدوام والمناسبات ما أحتاج غيره',
        'rating': 5, 'type': 'product', 'stage': 'ambassador',
        'story_type': 'daily_ritual', 'gender': 'both',
        'marketing_goal': 'versatility',
    },
]


# ═══════════════════════════════════════════════════════════
#  الدوال
# ═══════════════════════════════════════════════════════════

def pick_golden_review(rating=None, review_type=None, gender=None, stage=None, story_type=None, exclude_texts=None):
    """اختيار تقييم ذهبي بفلترة ذكية"""
    pool = list(GOLDEN_REVIEWS)
    if rating is not None:
        pool = [r for r in pool if r['rating'] == rating]
    if review_type:
        pool = [r for r in pool if r['type'] == review_type]
    if gender and gender != 'both':
        pool = [r for r in pool if r['gender'] in (gender, 'both')]
    if stage:
        pool = [r for r in pool if r['stage'] == stage]
    if story_type:
        pool = [r for r in pool if r['story_type'] == story_type]
    if exclude_texts:
        pool = [r for r in pool if r['text'] not in exclude_texts]
    if not pool:
        pool = list(GOLDEN_REVIEWS)
    return random.choice(pool)


def pick_golden_exemplars(count=3, gender=None, story_type=None):
    """اختيار نماذج ذهبية متنوعة للبرومبت"""
    pool = list(GOLDEN_REVIEWS)
    if gender and gender != 'both':
        pool = [r for r in pool if r['gender'] in (gender, 'both')]
    if story_type:
        pool = [r for r in pool if r['story_type'] == story_type]
    if len(pool) < count:
        pool = list(GOLDEN_REVIEWS)
    selected = random.sample(pool, min(count, len(pool)))
    return [r['text'] for r in selected]


def get_story_types():
    """قائمة أنواع القصص المتاحة"""
    return list(set(r['story_type'] for r in GOLDEN_REVIEWS))


def get_stats():
    """إحصائيات البنك"""
    from collections import Counter
    types = Counter(r['story_type'] for r in GOLDEN_REVIEWS)
    ratings = Counter(r['rating'] for r in GOLDEN_REVIEWS)
    review_types = Counter(r['type'] for r in GOLDEN_REVIEWS)
    return {
        'total': len(GOLDEN_REVIEWS),
        'story_types': dict(types),
        'ratings': dict(ratings),
        'review_types': dict(review_types),
    }


if __name__ == '__main__':
    import json
    stats = get_stats()
    print(f'\n=== Golden Reviews Bank ===')
    print(f'Total: {stats["total"]}')
    print(f'Story types: {json.dumps(stats["story_types"], ensure_ascii=False, indent=2)}')
    print(f'Ratings: {stats["ratings"]}')
    print(f'Types: {stats["review_types"]}')
    print(f'\n--- Sample Reviews ---')
    for st in get_story_types():
        r = pick_golden_review(story_type=st)
        print(f'\n[{st}] ({r["rating"]}⭐) "{r["text"][:60]}..."')
