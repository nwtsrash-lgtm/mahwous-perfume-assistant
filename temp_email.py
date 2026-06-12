"""
مولد الإيميلات المؤقتة مع صندوق الوارد
يستخدم mail.tm API (نطاقات شرعية تقبلها المتاجر)
+ 1secmail كخيار احتياطي
"""

import json
import random
import string
import time
import urllib.request
import urllib.error
from pathlib import Path


class TempEmailGenerator:
    """مولد إيميلات مؤقتة حقيقية بنطاقات مقبولة"""

    MAILTM_API = 'https://api.mail.tm'
    SECMAIL_API = 'https://www.1secmail.com/api/v1/'

    def __init__(self):
        self.active_emails = []
        self._load_state()

    def _load_state(self):
        path = Path(__file__).parent / 'emails_state.json'
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.active_emails = json.load(f)
            except Exception:
                self.active_emails = []

    def _save_state(self):
        path = Path(__file__).parent / 'emails_state.json'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.active_emails, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _http_request(self, url, method='GET', data=None, headers=None, timeout=15):
        """طلب HTTP موحد"""
        hdrs = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}
        if headers:
            hdrs.update(headers)
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            return None

    # ─────────────────────────────────────────────
    #  mail.tm - نطاقات شرعية
    # ─────────────────────────────────────────────
    def _get_mailtm_domains(self):
        """جلب النطاقات المتاحة من mail.tm"""
        result = self._http_request(f'{self.MAILTM_API}/domains')
        if result and 'hydra:member' in result:
            return [d['domain'] for d in result['hydra:member'] if d.get('isActive')]
        return []

    def _create_mailtm_email(self):
        """إنشاء إيميل عبر mail.tm"""
        domains = self._get_mailtm_domains()
        if not domains:
            return None

        domain = random.choice(domains)
        username = ''.join(random.choices(string.ascii_lowercase, k=4)) + \
                   ''.join(random.choices(string.digits, k=3))
        email = f'{username}@{domain}'
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        # إنشاء الحساب
        result = self._http_request(
            f'{self.MAILTM_API}/accounts',
            method='POST',
            data={'address': email, 'password': password}
        )

        if not result or 'id' not in result:
            return None

        # الحصول على التوكن
        token_result = self._http_request(
            f'{self.MAILTM_API}/token',
            method='POST',
            data={'address': email, 'password': password}
        )

        token = token_result.get('token', '') if token_result else ''

        return {
            'email': email,
            'password': password,
            'token': token,
            'account_id': result.get('id', ''),
            'domain': domain,
            'provider': 'mail.tm',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'messages': 0
        }

    # ─────────────────────────────────────────────
    #  1secmail - خيار احتياطي
    # ─────────────────────────────────────────────
    def _create_secmail_email(self):
        """إنشاء إيميل عبر 1secmail (احتياطي)"""
        result = self._http_request(f'{self.SECMAIL_API}?action=genRandomMailbox&count=1')
        if result and len(result) > 0:
            email = result[0]
            login, domain = email.split('@')
            return {
                'email': email,
                'login': login,
                'domain': domain,
                'provider': '1secmail',
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'messages': 0
            }
        return None

    # ─────────────────────────────────────────────
    #  واجهة عامة
    # ─────────────────────────────────────────────
    def create_email(self, count=1):
        """إنشاء إيميلات مؤقتة (mail.tm أولاً ← 1secmail احتياطي)"""
        results = []
        for _ in range(count):
            # محاولة mail.tm أولاً (نطاقات أفضل)
            entry = self._create_mailtm_email()
            if not entry:
                # احتياطي: 1secmail
                entry = self._create_secmail_email()
            if entry:
                self.active_emails.append(entry)
                results.append(entry)

        self._save_state()
        return results

    def check_inbox(self, email):
        """فحص صندوق الوارد"""
        entry = next((e for e in self.active_emails if e['email'] == email), None)
        if not entry:
            return []

        if entry.get('provider') == 'mail.tm':
            return self._check_mailtm_inbox(entry)
        else:
            return self._check_secmail_inbox(email)

    def _check_mailtm_inbox(self, entry):
        """فحص وارد mail.tm"""
        token = entry.get('token', '')
        if not token:
            return []
        result = self._http_request(
            f'{self.MAILTM_API}/messages',
            headers={'Authorization': f'Bearer {token}'}
        )
        if result and 'hydra:member' in result:
            messages = []
            for msg in result['hydra:member']:
                messages.append({
                    'id': msg.get('id', ''),
                    'from': msg.get('from', {}).get('address', ''),
                    'subject': msg.get('subject', ''),
                    'date': msg.get('createdAt', ''),
                    'intro': msg.get('intro', ''),
                    'seen': msg.get('seen', False)
                })
            entry['messages'] = len(messages)
            self._save_state()
            return messages
        return []

    def _check_secmail_inbox(self, email):
        """فحص وارد 1secmail"""
        login, domain = email.split('@')
        result = self._http_request(
            f'{self.SECMAIL_API}?action=getMessages&login={login}&domain={domain}'
        )
        if result:
            for e in self.active_emails:
                if e['email'] == email:
                    e['messages'] = len(result)
            self._save_state()
            return result
        return []

    def read_message(self, email, message_id):
        """قراءة رسالة"""
        entry = next((e for e in self.active_emails if e['email'] == email), None)
        if not entry:
            return None

        if entry.get('provider') == 'mail.tm':
            token = entry.get('token', '')
            if not token:
                return None
            return self._http_request(
                f'{self.MAILTM_API}/messages/{message_id}',
                headers={'Authorization': f'Bearer {token}'}
            )
        else:
            login, domain = email.split('@')
            return self._http_request(
                f'{self.SECMAIL_API}?action=readMessage&login={login}&domain={domain}&id={message_id}'
            )

    def get_active_emails(self):
        return self.active_emails

    def delete_email(self, email):
        self.active_emails = [e for e in self.active_emails if e['email'] != email]
        self._save_state()
