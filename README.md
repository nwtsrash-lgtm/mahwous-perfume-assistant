# 🌸 نظام أتمتة العطور السعودية

نظام محلي لأتمتة تصفح متاجر العطور السعودية، اختيار المنتجات الترند، إضافتها للسلة، وتوليد تقييمات واقعية.

## ⚡ التشغيل السريع

### 1. تثبيت المتطلبات

```bash
cd perfume_bot
pip install -r requirements.txt
playwright install chromium
```

### 2. تشغيل النظام

```bash
python app.py
```

### 3. فتح المتصفح

افتح: [http://localhost:5000](http://localhost:5000)

---

## 🏗️ هيكل المشروع

```
perfume_bot/
├── app.py                  # سيرفر Flask الرئيسي
├── scraper.py              # التصفح الآلي (Playwright)
├── database.py             # قاعدة بيانات SQLite
├── review_generator.py     # مولد التقييمات العربية
├── names.json              # 100 اسم ذكر + 100 أنثى
├── review_templates.json   # قوالب التقييمات
├── stores_config.json      # تكوين المتاجر
├── requirements.txt        # المتطلبات
├── templates/
│   └── index.html          # الواجهة الرئيسية
└── static/
    ├── style.css           # التنسيقات (داكن + ذهبي)
    └── script.js           # منطق الواجهة
```

## 🛍️ المتاجر المدعومة

| المتجر | الرابط | المنصة |
|--------|--------|--------|
| خبير العطور | alkhabeershop.com | Salla |
| سارة ستور | sarahmakeup37.com | Salla |
| قصر الطيب | qasralteeb.com | Salla |
| عساف | 3saf.com | مخصص |
| متجر مخصص | أي رابط | Salla/عام |

## 📋 طريقة الاستخدام

### الخطوة 1: توليد شخصية
- اضغط "✨ توليد شخصية جديدة"
- يتم اختيار اسم سعودي عشوائي

### الخطوة 2: تصفح الترند
- اختر المتجر من القائمة
- اضغط "🔍 تصفح الترند"
- يفتح متصفح Playwright ويجلب المنتجات الأكثر مبيعاً

### الخطوة 3: إضافة للسلة
- اضغط "🛒 إضافة للسلة" بجانب المنتج
- المتصفح يفتح صفحة المنتج ويضيفه للسلة
- ⚠️ **يتوقف عند صفحة الدفع - أكمل الدفع يدوياً**

### الخطوة 4: توليد التقييمات
- بعد استلام المنتج، غيّر الحالة إلى "delivered"
- اضغط "📝 توليد تقييم"
- يظهر 3 تقييمات واقعية بالعربية
- انسخ التقييم والصقه في صفحة المتجر

## ⚠️ تنبيهات مهمة

- **لا يكمل الدفع أبداً** - يتوقف عند صفحة الدفع
- **لا ينشر التقييمات** - يعرضها فقط للنسخ اليدوي
- بعض المتاجر تستخدم Cloudflare - النظام يحاول تجاوزها تلقائياً
- إذا تغير تصميم المتجر، عدّل `stores_config.json`

## 🔧 تخصيص المتاجر

لإضافة متجر جديد، أضف في `stores_config.json`:

```json
{
    "name": "اسم المتجر",
    "name_en": "store_id",
    "base_url": "https://store.com",
    "platform": "salla",
    "trending_url": "https://store.com/best-selling",
    "selectors": {
        "product_card": ".product-item",
        "product_name": ".product-title",
        "product_price": ".price",
        "add_to_cart": ".add-to-cart"
    }
}
```

## 📝 API Endpoints

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| POST | `/api/persona/generate` | توليد شخصية جديدة |
| GET | `/api/personas` | قائمة الشخصيات |
| POST | `/api/scrape/trending` | جلب المنتجات الترند |
| POST | `/api/cart/add` | إضافة للسلة |
| POST | `/api/order/create` | إنشاء طلب |
| PUT | `/api/order/{id}/status` | تحديث حالة الطلب |
| POST | `/api/review/generate` | توليد تقييمات |
| GET | `/api/orders` | قائمة الطلبات |
| GET | `/api/stats` | الإحصائيات |

## 🐛 حل المشاكل

### المتصفح لا يفتح
```bash
playwright install chromium
```

### خطأ في تحميل الموقع
- تأكد من اتصال الإنترنت
- المتجر قد يكون متوقف مؤقتاً
- جرب تغيير `headless=False` في السكرابر

### لم يجد المنتجات
- المتجر قد يكون غيّر تصميمه
- عدّل selectors في `stores_config.json`
- راجع `debug_screenshot.png` للتشخيص
