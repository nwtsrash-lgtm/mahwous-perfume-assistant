"""
محرك الأتمتة الكامل — Full Automation Engine
يتصفح المتجر كمستخدم حقيقي:
  1. يجلب إيميل من Boomlify
  2. يسجل في المتجر
  3. يقرأ OTP من Boomlify ويدخله
  4. يملأ البيانات (الاسم، القب)
  5. يتصفح المنتجات ويضيفها للسلة
  6. ينتظر الدفع (يدوي)
  7. يكتب التقييمات ويرسلها
"""

import asyncio
import json
import random
import re
import logging
import time
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

logger = logging.getLogger('automation')

STEALTH = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'languages',{get:()=>['ar-SA','ar','en-US','en']});
window.chrome={runtime:{},loadTimes:()=>({}),csi:()=>({})};
Object.defineProperty(navigator,'plugins',{get:()=>{const p=[{name:'Chrome PDF Plugin'},{name:'Chrome PDF Viewer'},{name:'Native Client'}];p.length=3;return p;}});
"""


class StoreAutomation:
    """أتمتة كاملة للمتاجر السعودية"""

    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.store_page = None
        self.boomlify_page = None
        self.status = 'idle'
        self.steps_log = []
        self.temp_email = ''
        self.otp_code = ''
        self.persona = {}

    def _log(self, step, msg):
        entry = {'step': step, 'message': msg, 'time': time.strftime('%H:%M:%S')}
        self.steps_log.append(entry)
        logger.info(f'[{step}] {msg}')
        self.status = step

    # ─────────────────────────────────────────
    #  إطلاق المتصفح
    # ─────────────────────────────────────────
    async def launch(self):
        """إطلاق متصفح مرئي Stealth"""
        self._log('launch', '🚀 إطلاق المتصفح...')
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled',
                  '--no-sandbox', '--lang=ar-SA', '--window-size=1300,800']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1300, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
            locale='ar-SA', timezone_id='Asia/Riyadh',
            geolocation={'latitude': 24.7136, 'longitude': 46.6753},
            permissions=['geolocation'], color_scheme='light',
        )
        await self.context.add_init_script(STEALTH)
        self._log('launch', '✅ المتصفح جاهز')

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.pw: await self.pw.stop()
        except: pass

    # ─────────────────────────────────────────
    #  الخطوة 1: جلب إيميل من Boomlify
    # ─────────────────────────────────────────
    async def get_boomlify_email(self):
        """فتح Boomlify وجلب الإيميل المؤقت (React SPA)"""
        self._log('email', '📧 فتح Boomlify...')
        self.boomlify_page = await self.context.new_page()
        await self.boomlify_page.goto('https://boomlify.com/ar', wait_until='networkidle', timeout=40000)
        self._log('email', '⏳ انتظار تحميل React...')
        await asyncio.sleep(10)  # React SPA needs time to render

        email = ''

        for attempt in range(8):
            # الطريقة 1: قراءة من localStorage (Boomlify يخزن الإيميلات هناك)
            if not email:
                try:
                    stored = await self.boomlify_page.evaluate('''() => {
                        // Check localStorage for any email data
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            const val = localStorage.getItem(key);
                            if (val && val.includes('@') && !val.includes('boomlify.com')) {
                                try {
                                    const parsed = JSON.parse(val);
                                    // Look for email field in parsed objects
                                    if (typeof parsed === 'object') {
                                        for (const [k, v] of Object.entries(parsed)) {
                                            if (typeof v === 'string' && v.includes('@') && v.includes('.') 
                                                && !v.includes('boomlify.com') && !v.includes('google.com')
                                                && v.length > 5 && v.length < 60) {
                                                return v;
                                            }
                                            // Check nested objects
                                            if (typeof v === 'object' && v !== null) {
                                                for (const [k2, v2] of Object.entries(v)) {
                                                    if (typeof v2 === 'string' && v2.includes('@') && v2.includes('.')
                                                        && !v2.includes('boomlify.com') && v2.length > 5) {
                                                        return v2;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                } catch(e) {
                                    // Maybe it's a plain email string
                                    const emailMatch = val.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
                                    if (emailMatch && !emailMatch[0].includes('boomlify.com')) {
                                        return emailMatch[0];
                                    }
                                }
                            }
                        }
                        return '';
                    }''')
                    if stored and '@' in stored:
                        email = stored.strip()
                        self._log('email', f'✅ إيميل من localStorage: {email}')
                except Exception as e:
                    logger.debug(f'localStorage read error: {e}')

            # الطريقة 2: النقر على زر النسخ وقراءة clipboard
            if not email:
                try:
                    copy_btns = await self.boomlify_page.query_selector_all('button')
                    for btn in copy_btns:
                        try:
                            text = await btn.inner_text()
                            # Look for copy button (usually has copy icon or "نسخ" text)
                            aria = await btn.get_attribute('aria-label') or ''
                            title = await btn.get_attribute('title') or ''
                            if any(w in (text + aria + title).lower() for w in ['copy', 'نسخ', 'clipboard']):
                                await btn.click()
                                await asyncio.sleep(0.5)
                                clipboard = await self.boomlify_page.evaluate('navigator.clipboard.readText().catch(()=>"")')
                                if clipboard and '@' in clipboard:
                                    email = clipboard.strip()
                                    self._log('email', f'✅ إيميل من clipboard: {email}')
                                    break
                        except: continue
                except: pass

            # الطريقة 3: البحث في النص المرئي عن نمط إيميل
            if not email:
                try:
                    visible_email = await self.boomlify_page.evaluate('''() => {
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
                        const ignore = ['boomlify.com', 'example.com', 'google.com', 'email.com'];
                        while (walker.nextNode()) {
                            const text = walker.currentNode.textContent;
                            const matches = text.match(emailRegex);
                            if (matches) {
                                for (const m of matches) {
                                    if (!ignore.some(ig => m.toLowerCase().includes(ig)) && m.length < 60) {
                                        return m;
                                    }
                                }
                            }
                        }
                        return '';
                    }''')
                    if visible_email and '@' in visible_email:
                        email = visible_email.strip()
                        self._log('email', f'✅ إيميل من DOM: {email}')
                except: pass

            # الطريقة 4: البحث في inputs
            if not email:
                for sel in ['input[readonly]', 'input[type="text"]', 'input[type="email"]', 'input']:
                    try:
                        els = await self.boomlify_page.query_selector_all(sel)
                        for el in els:
                            val = await el.get_attribute('value') or ''
                            if '@' in val and '.' in val and len(val) > 5 and 'boomlify.com' not in val:
                                email = val.strip()
                                self._log('email', f'✅ إيميل من input: {email}')
                                break
                    except: continue
                    if email: break

            if email:
                break

            self._log('email', f'⏳ محاولة {attempt+1}/8 — انتظار تحميل الإيميل...')
            await asyncio.sleep(3)

        if email:
            self.temp_email = email
            self._log('email', f'✅ الإيميل الجاهز: {email}')
        else:
            # حفظ screenshot للتشخيص
            try:
                await self.boomlify_page.screenshot(path='debug_boomlify.png')
                self._log('email', '📸 تم حفظ screenshot: debug_boomlify.png')
            except: pass
            self._log('email', '⚠️ لم يتم العثور على إيميل — تحقق من صفحة Boomlify')

        return email

    # ─────────────────────────────────────────
    #  الخطوة 2: تسجيل في المتجر
    # ─────────────────────────────────────────
    async def register_on_store(self, store_url, email=None, store_config=None):
        """فتح المتجر وإدخال الإيميل للتسجيل (يدعم Salla)"""
        email = email or self.temp_email

        self._log('register', f'🏪 فتح المتجر: {store_url}')
        self.store_page = await self.context.new_page()
        await self.store_page.goto(store_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)

        # تخطي preloader إذا وجد
        try:
            skip = await self.store_page.query_selector('.preloader-skip')
            if skip and await skip.is_visible():
                await skip.click()
                await asyncio.sleep(1)
        except: pass

        # إذا ما فيه إيميل، نفتح المتجر بس ونخلي المستخدم يسجل يدوياً
        if not email:
            self._log('register', '⚠️ لا يوجد إيميل — سجّل يدوياً من نافذة Boomlify')
            # نفتح نافذة الدخول على كل حال
            try:
                await self.store_page.evaluate("salla.event.dispatch('login::open')")
                await asyncio.sleep(2)
                self._log('register', '🔓 نافذة الدخول مفتوحة — أدخل الإيميل يدوياً')
            except: pass
            return True

        # فتح نافذة الدخول عبر Salla JS API
        self._log('register', '🔓 فتح نافذة تسجيل الدخول (Salla)...')
        try:
            await self.store_page.evaluate("salla.event.dispatch('login::open')")
            await asyncio.sleep(3)
            self._log('register', '✅ نافذة الدخول مفتوحة')
        except:
            # fallback: النقر على أيقونة المستخدم
            user_btns = [
                'button[onclick*="login"]', '.sicon-user', 'i.sicon-user',
                'button:has-text("دخول")', 'a:has-text("حسابي")',
            ]
            for sel in user_btns:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el:
                        parent = await el.evaluate_handle('e => e.closest("button") || e.closest("a") || e')
                        await parent.as_element().click()
                        self._log('register', '✅ تم النقر على أيقونة المستخدم')
                        await asyncio.sleep(3)
                        break
                except: continue

        # إدخال الإيميل في نافذة Salla
        email_selectors = [
            'input[type="email"]', 'input[name="email"]',
            'input[placeholder*="إيميل"]', 'input[placeholder*="email"]',
            'input[placeholder*="البريد"]', 'input[placeholder*="بريد"]',
            '#email', 'input[name="identifier"]',
            'salla-login-modal input[type="email"]',
        ]

        entered = False
        for attempt in range(5):
            for sel in email_selectors:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await asyncio.sleep(0.3)
                        await el.fill('')
                        await self._human_type(el, email)
                        entered = True
                        self._log('register', f'✅ تم إدخال الإيميل: {email}')
                        break
                except: continue
            if entered: break
            await asyncio.sleep(1)

        if not entered:
            self._log('register', '⚠️ أدخل الإيميل يدوياً في نافذة الدخول')
            return False

        # النقر على زر الإرسال
        await asyncio.sleep(1)
        submit_selectors = [
            'button[type="submit"]', 'button:has-text("دخول")',
            'button:has-text("إرسال")', 'button:has-text("متابعة")',
            'button:has-text("تسجيل")', '.btn-primary',
        ]

        for sel in submit_selectors:
            try:
                el = await self.store_page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    self._log('register', '✅ تم إرسال طلب الدخول — انتظر رمز التحقق')
                    await asyncio.sleep(3)
                    break
            except: continue

        return True

    # ─────────────────────────────────────────
    #  الخطوة 3: قراءة OTP من Boomlify
    # ─────────────────────────────────────────
    async def get_otp_from_boomlify(self, max_wait=120):
        """انتظار وقراءة رمز التحقق من Boomlify"""
        self._log('otp', '⏳ انتظار رمز التحقق من Boomlify...')

        if not self.boomlify_page:
            self._log('otp', '❌ صفحة Boomlify غير مفتوحة')
            return ''

        await self.boomlify_page.bring_to_front()
        start = time.time()

        while time.time() - start < max_wait:
            try:
                # تحديث الصفحة / النقر على تحديث
                refresh_btns = [
                    'button:has-text("تحديث")', 'button:has-text("Refresh")',
                    '.refresh-btn', '#refresh', 'button.reload',
                    'button:has-text("تحقق")', 'button:has-text("Check")',
                ]
                for sel in refresh_btns:
                    try:
                        el = await self.boomlify_page.query_selector(sel)
                        if el and await el.is_visible():
                            await el.click()
                            await asyncio.sleep(2)
                            break
                    except: continue

                # البحث عن رسائل جديدة
                msg_selectors = [
                    '.mail-item', '.message-item', '.inbox-item',
                    'tr.mail', '.email-item', '.msg-row',
                    'table tbody tr', '.message-list-item',
                    '.mail-list-item', 'div[class*="mail"]',
                ]

                for sel in msg_selectors:
                    try:
                        msgs = await self.boomlify_page.query_selector_all(sel)
                        if msgs and len(msgs) > 0:
                            # النقر على أول رسالة
                            await msgs[0].click()
                            await asyncio.sleep(2)
                            self._log('otp', '📩 تم العثور على رسالة!')

                            # استخراج OTP من محتوى الرسالة
                            body = await self.boomlify_page.content()
                            otp = self._extract_otp(body)
                            if otp:
                                self.otp_code = otp
                                self._log('otp', f'✅ رمز التحقق: {otp}')
                                return otp
                    except: continue

                # محاولة قراءة OTP من محتوى الصفحة مباشرة
                body = await self.boomlify_page.content()
                otp = self._extract_otp(body)
                if otp:
                    self.otp_code = otp
                    self._log('otp', f'✅ رمز التحقق: {otp}')
                    return otp

            except Exception as e:
                logger.debug(f'OTP poll error: {e}')

            self._log('otp', f'⏳ جاري الانتظار... ({int(time.time()-start)}s)')
            await asyncio.sleep(5)

        self._log('otp', '⚠️ انتهت المهلة - أدخل الرمز يدوياً')
        return ''

    def _extract_otp(self, text):
        """استخراج رمز OTP من النص"""
        # أنماط شائعة لرموز التحقق
        patterns = [
            r'(?:رمز|كود|code|otp|verify|verification)[\s:]*(\d{4,6})',
            r'(\d{4,6})[\s]*(?:هو رمز|is your|verification|تحقق)',
            r'<strong>(\d{4,6})</strong>',
            r'class="[^"]*otp[^"]*"[^>]*>(\d{4,6})',
            r'(\d{4})',  # أي رقم من 4 أرقام
            r'(\d{6})',  # أي رقم من 6 أرقام
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                code = match.group(1)
                if 4 <= len(code) <= 6:
                    return code
        return ''

    # ─────────────────────────────────────────
    #  الخطوة 4: إدخال OTP في المتجر
    # ─────────────────────────────────────────
    async def enter_otp(self, otp=None):
        """إدخال رمز التحقق في المتجر"""
        otp = otp or self.otp_code
        if not otp:
            self._log('enter_otp', '⚠️ لا يوجد رمز تحقق')
            return False

        if not self.store_page:
            self._log('enter_otp', '❌ صفحة المتجر غير مفتوحة')
            return False

        await self.store_page.bring_to_front()
        await asyncio.sleep(1)
        self._log('enter_otp', f'🔑 إدخال الرمز: {otp}')

        # البحث عن حقول OTP
        otp_selectors = [
            'input[name="otp"]', 'input[name="code"]', 'input[name="verification"]',
            'input.otp-input', 'input[placeholder*="رمز"]', 'input[placeholder*="code"]',
            'input[type="tel"]', 'input[maxlength="4"]', 'input[maxlength="6"]',
            'input[inputmode="numeric"]', '.otp-field input',
        ]

        # محاولة 1: حقل واحد
        for sel in otp_selectors:
            try:
                el = await self.store_page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await el.fill('')
                    await self._human_type(el, otp)
                    self._log('enter_otp', '✅ تم إدخال الرمز')
                    await asyncio.sleep(1)

                    # النقر على تأكيد
                    confirm_sels = [
                        'button[type="submit"]', 'button:has-text("تأكيد")',
                        'button:has-text("تحقق")', 'button:has-text("دخول")',
                    ]
                    for cs in confirm_sels:
                        try:
                            btn = await self.store_page.query_selector(cs)
                            if btn and await btn.is_visible():
                                await btn.click()
                                break
                        except: continue

                    await asyncio.sleep(3)
                    return True
            except: continue

        # محاولة 2: حقول OTP متعددة (كل رقم في خانة)
        try:
            otp_inputs = await self.store_page.query_selector_all('input[maxlength="1"]')
            if otp_inputs and len(otp_inputs) >= len(otp):
                for i, digit in enumerate(otp):
                    await otp_inputs[i].click()
                    await otp_inputs[i].fill(digit)
                    await asyncio.sleep(0.15)
                self._log('enter_otp', '✅ تم إدخال الرمز (حقول متعددة)')
                await asyncio.sleep(2)
                return True
        except: pass

        self._log('enter_otp', '⚠️ أدخل الرمز يدوياً')
        return False

    # ─────────────────────────────────────────
    #  الخطوة 5: تعبئة البيانات (اسم، لقب)
    # ─────────────────────────────────────────
    async def fill_profile(self, persona=None):
        """تعبئة بيانات الملف الشخصي"""
        persona = persona or self.persona
        first = persona.get('first_name', 'محمد')
        last = persona.get('last_name', 'السعودي')
        full = persona.get('name', f'{first} {last}')
        city = persona.get('city', 'الرياض')

        if not self.store_page:
            return False

        await self.store_page.bring_to_front()
        self._log('profile', f'👤 تعبئة البيانات: {full} — {city}')

        field_map = {
            'first_name': [
                'input[name="first_name"]', 'input[name="fname"]',
                'input[placeholder*="الاسم الأول"]', 'input[placeholder*="الاسم"]',
                '#first_name', '#fname',
            ],
            'last_name': [
                'input[name="last_name"]', 'input[name="lname"]',
                'input[placeholder*="اسم العائلة"]', 'input[placeholder*="اللقب"]',
                '#last_name', '#lname',
            ],
            'name': [
                'input[name="name"]', 'input[placeholder*="الاسم الكامل"]',
                '#name', '#full_name',
            ],
            'city': [
                'input[name="city"]', 'select[name="city"]',
                'input[placeholder*="المدينة"]',
            ],
        }

        values = {
            'first_name': first, 'last_name': last,
            'name': full, 'city': city,
        }

        filled = []
        for field, sels in field_map.items():
            for sel in sels:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el and await el.is_visible():
                        tag = await el.evaluate('e => e.tagName.toLowerCase()')
                        if tag == 'select':
                            options = await el.query_selector_all('option')
                            for opt in options:
                                text = await opt.inner_text()
                                if city in text:
                                    val = await opt.get_attribute('value')
                                    await el.select_option(val)
                                    filled.append(field)
                                    break
                        else:
                            await el.click()
                            await el.fill('')
                            await self._human_type(el, values[field])
                            filled.append(field)
                        break
                except: continue

        self._log('profile', f'✅ تم تعبئة: {", ".join(filled) if filled else "لم يتم العثور على حقول"}')
        self._log('profile', '📱 أدخل رقم الجوال يدوياً الآن')
        return True

    # ─────────────────────────────────────────
    #  الخطوة 6: تصفح المنتجات وإضافة للسلة
    # ─────────────────────────────────────────
    async def browse_and_add_to_cart(self, store_url, store_config=None, num_products=2):
        """تصفح المنتجات وإضافة عشوائية للسلة"""
        if not self.store_page:
            return []

        self._log('cart', '🔍 تصفح المنتجات...')

        # استخدام trending_url من الإعدادات أو الرابط الافتراضي
        trending_url = store_url
        if store_config and store_config.get('trending_url'):
            trending_url = store_config['trending_url']

        try:
            await self.store_page.goto(trending_url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(5)

            # تخطي preloader
            try:
                skip = await self.store_page.query_selector('.preloader-skip')
                if skip and await skip.is_visible(): await skip.click()
            except: pass
        except:
            self._log('cart', '⚠️ فشل تحميل صفحة المنتجات')

        # تمرير الصفحة لتحميل المنتجات
        for _ in range(4):
            await self.store_page.evaluate('window.scrollBy(0, 600)')
            await asyncio.sleep(1)

        # جمع روابط المنتجات (Salla: /p/ format)
        product_links = []
        link_selectors = [
            'a[href*="/p/"]',
            '.s-product-card-entry a',
            '.product-entry a',
            'a[href*="/product"]',
        ]

        for sel in link_selectors:
            try:
                els = await self.store_page.query_selector_all(sel)
                for el in els:
                    href = await el.get_attribute('href')
                    if href and ('/p/' in href or '/product' in href):
                        full = href if href.startswith('http') else f"https://mahwous.com{href}"
                        if full not in product_links:
                            product_links.append(full)
            except: continue

        if not product_links:
            self._log('cart', '⚠️ لم يتم العثور على منتجات — تصفح يدوياً')
            return []

        self._log('cart', f'📦 تم العثور على {len(product_links)} منتج')

        # اختيار عشوائي وإضافة للسلة
        selected = random.sample(product_links, min(num_products, len(product_links)))
        added = []

        for url in selected:
            try:
                await self.store_page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(3)

                # تخطي preloader
                try:
                    skip = await self.store_page.query_selector('.preloader-skip')
                    if skip and await skip.is_visible(): await skip.click()
                except: pass

                # جلب اسم المنتج
                name = ''
                for sel in ['h1', '.product-title', '.product-name', '.s-product-card-entry__title']:
                    try:
                        el = await self.store_page.query_selector(sel)
                        if el: name = (await el.inner_text()).strip()[:50]; break
                    except: continue

                # النقر على "أضف للسلة" (Salla web component)
                cart_sels = [
                    'salla-add-product-button',
                    'button:has-text("أضف")',
                    'button:has-text("السلة")',
                    '.s-add-to-cart-btn',
                    'button[class*="add"]',
                    '.add-to-cart',
                ]
                for sel in cart_sels:
                    try:
                        el = await self.store_page.query_selector(sel)
                        if el and await el.is_visible():
                            await el.click()
                            added.append(name or url)
                            self._log('cart', f'🛒 تمت إضافة: {name or url}')
                            await asyncio.sleep(2)
                            break
                    except: continue

            except Exception as e:
                logger.debug(f'Cart error: {e}')

        self._log('cart', f'✅ تم إضافة {len(added)} منتج للسلة')
        self._log('cart', '💳 أكمل الدفع يدوياً الآن')
        return added

    # ─────────────────────────────────────────
    #  الخطوة 7: كتابة التقييمات
    # ─────────────────────────────────────────
    async def submit_reviews(self, reviews, store_url):
        """كتابة وإرسال التقييمات على المتجر"""
        if not self.store_page or not reviews:
            return False

        self._log('review', '⭐ بدء كتابة التقييمات...')
        await self.store_page.bring_to_front()

        for i, review in enumerate(reviews):
            text = review.get('text', '')
            rating = review.get('rating', 5)
            product_url = review.get('product_url', '')

            if product_url:
                try:
                    await self.store_page.goto(product_url, wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(2)
                except: continue

            # البحث عن نموذج التقييم
            review_triggers = [
                'button:has-text("تقييم")', 'a:has-text("تقييم")',
                'button:has-text("رأيك")', '.write-review',
                'a:has-text("اكتب تقييم")', '.review-btn',
            ]
            for sel in review_triggers:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await asyncio.sleep(2)
                        break
                except: continue

            # إدخال التقييم النصي
            review_fields = [
                'textarea[name*="review"]', 'textarea[name*="comment"]',
                'textarea[placeholder*="تقييم"]', 'textarea[placeholder*="رأيك"]',
                'textarea', '.review-textarea',
            ]
            for sel in review_fields:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await self._human_type(el, text)
                        self._log('review', f'📝 تم كتابة التقييم {i+1}')
                        break
                except: continue

            # اختيار النجوم
            try:
                stars = await self.store_page.query_selector_all('.star, .rating-star, [data-rating]')
                if stars and len(stars) >= rating:
                    await stars[rating - 1].click()
                    await asyncio.sleep(0.5)
            except: pass

            # إرسال
            for sel in ['button[type="submit"]', 'button:has-text("إرسال")', 'button:has-text("نشر")']:
                try:
                    el = await self.store_page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        self._log('review', f'✅ تم إرسال التقييم {i+1}')
                        await asyncio.sleep(2)
                        break
                except: continue

        self._log('review', '🎉 تم إرسال جميع التقييمات!')
        return True

    # ─────────────────────────────────────────
    #  التدفق الكامل
    # ─────────────────────────────────────────
    async def full_flow(self, store_url, persona, store_config=None):
        """تشغيل التدفق الكامل"""
        self.persona = persona
        self.steps_log = []

        try:
            # 1. إطلاق المتصفح
            await self.launch()

            # 2. جلب إيميل
            email = await self.get_boomlify_email()
            if not email:
                self._log('email', '⚠️ افتح Boomlify وانسخ الإيميل يدوياً')

            # 3. تسجيل في المتجر
            await self.register_on_store(store_url, email, store_config)

            # 4. قراءة OTP
            otp = await self.get_otp_from_boomlify(max_wait=90)

            # 5. إدخال OTP
            if otp:
                await self.enter_otp(otp)

            # 6. تعبئة البيانات
            await self.fill_profile(persona)

            # 7. تصفح وإضافة للسلة
            await self.browse_and_add_to_cart(store_url, store_config)

            self._log('done', '✅ انتهى! أدخل رقم الجوال وأكمل الدفع يدوياً')

        except Exception as e:
            self._log('error', f'❌ خطأ: {str(e)}')

        return self.steps_log

    # ─────────────────────────────────────────
    #  كتابة إنسانية
    # ─────────────────────────────────────────
    async def _human_type(self, element, text, speed=0.05):
        """كتابة حرف بحرف كإنسان"""
        for char in text:
            await element.type(char, delay=random.uniform(30, 120))
            if random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.1, 0.3))

    def get_status(self):
        return {
            'status': self.status,
            'email': self.temp_email,
            'otp': self.otp_code,
            'steps': self.steps_log[-10:],  # آخر 10 خطوات
        }
