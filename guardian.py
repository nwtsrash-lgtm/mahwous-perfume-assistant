#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guardian.py — الحارس التنفيذي للعقل المدبّر (v4)
=================================================
يحوّل بروتوكولات الدستور النثرية إلى فحص حتمي مربوط بـ git، يصعب تزويره.
بدل أن يلصق المبرمج grep حرًّا (قابلًا للتلفيق)، يشغّل هذا الحارس ويلصق مخرجه:
حتمي، مربوط بـ HEAD، يُعاد إنتاجه بنفس النتيجة.

الاستخدام:  python guardian.py
- بلا تبعيّات خارجية (stdlib فقط).
- لا ينفّذ كود التطبيق إطلاقًا — يحلّله عبر AST (تحليل ساكن آمن).
- يخرج برمز 1 إذا سقط أي فحص حرِج (صالح لبوابة CI).
"""
import ast
import re
import sys
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')  # لضمان طباعة العربية/الإيموجي على ويندوز
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'personas_engine.py'
APP = ROOT / 'app.py'

SANCTIONED_BRANCH = 'master'                       # مصدر الحقيقة الوحيد (الدستور)
DANGER_BRANCHES = {'claude/recursing-cray-91346c'}  # فرع خطر موثّق: لا يُدمج (مصيدة #3)


# ───────────────────────── git ─────────────────────────
def _git(args):
    try:
        return subprocess.run(['git', *args], cwd=str(ROOT),
                              capture_output=True, text=True, encoding='utf-8').stdout.strip()
    except Exception as e:
        return f'<git error: {e}>'


def git_stamp():
    return {
        'head': _git(['rev-parse', '--short', 'HEAD']),
        'branch': _git(['rev-parse', '--abbrev-ref', 'HEAD']),
        'dirty': bool(_git(['status', '--porcelain'])),
        'branches': [b.lstrip('*+ ').strip() for b in _git(['branch']).splitlines() if b.strip()],
    }


# ──────────────── AST: استخراج قائمة معرّفات ────────────────
def module_list_ids(path, var='ARCHETYPES'):
    """يُرجع قائمة قيم 'id' من قائمة module-level باسم var — عبر AST، بلا تنفيذ."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in tree.body:  # module-level فقط (نتجاهل import alias)
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.List, ast.Tuple)):
            if any(isinstance(t, ast.Name) and t.id == var for t in node.targets):
                ids = []
                for el in node.value.elts:
                    if isinstance(el, ast.Dict):
                        for k, v in zip(el.keys, el.values):
                            if isinstance(k, ast.Constant) and k.value == 'id' and isinstance(v, ast.Constant):
                                ids.append(v.value)
                return ids
    return None


def check_archetypes_parity():
    """مصيدة #1: يجب تطابق العدد وكل id بين personas_engine.py و app.py."""
    eng, app = module_list_ids(ENGINE), module_list_ids(APP)
    r = {'engine_count': None if eng is None else len(eng),
         'app_count': None if app is None else len(app)}
    if eng is None or app is None:
        r['status'] = 'ERROR'
        return r
    se, sa = set(eng), set(app)
    r['in_engine_not_app'] = sorted(se - sa)
    r['in_app_not_engine'] = sorted(sa - se)
    r['dups'] = sorted({x for x in eng if eng.count(x) > 1} | {x for x in app if app.count(x) > 1})
    r['status'] = 'PASS' if (se == sa and len(eng) == len(app) and not r['dups']) else 'FAIL'
    return r


def check_fallback_as_review():
    """قانون 4: يصطاد نصًّا مثبّتًا/احتياطيًا يُعاد كـ تقييم (dict فيه 'text') بدل رفع 503."""
    tree = ast.parse(APP.read_text(encoding='utf-8'), filename=str(APP))
    hits = []
    for node in ast.walk(tree):
        # (أ) return لقاموس شكله تقييم، ونصّه ثابت أو من متغيّر fallback
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            tv = None
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(k, ast.Constant) and k.value == 'text':
                    tv = v
            if tv is not None:
                keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
                is_review = 'rating' in keys  # قاموس شكله تقييم كامل (rating+text) = فبركة صريحة
                if isinstance(tv, ast.Constant) and isinstance(tv.value, str):
                    label = 'return-تقييم-مفبرك(rating+نص-حرفي)' if is_review else 'return-نص-ثابت'
                    hits.append((label, node.lineno, repr(tv.value)[:42]))
                elif isinstance(tv, ast.Name) and 'fallback' in tv.id.lower():
                    hits.append(('return-متغيّر-fallback', node.lineno, tv.id))
        # (ب) إسناد سلسلة حرفية لمتغيّر اسمه fallback* (النص الوهمي الجاهز)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name) and 'fallback' in t.id.lower():
                    hits.append(('نص-fallback-مثبّت', node.lineno, repr(node.value.value)[:42]))
    return hits


# ──────────────── لينت الخط الأحمر للمخرَج ────────────────
_EMOJI = re.compile('[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⌀-⏿️]')
_DIGIT = re.compile('[0-9٠-٩]')
_NUMBERING = re.compile(r'(^|\n)\s*\d+\s*[.)\-]')


def lint_review(text):
    v = []
    if _EMOJI.search(text):
        v.append('emoji')
    if _NUMBERING.search(text):
        v.append('numbering')
    if _DIGIT.search(text):
        v.append('digit')
    return v


# ───────────────────────── main ─────────────────────────
def main():
    g = git_stamp()
    parity = check_archetypes_parity()
    fb = check_fallback_as_review()
    fails = []

    bar = '═' * 62
    print(bar)
    print('  🛡  الحارس التنفيذي — العقل المدبّر  (guardian.py)')
    print(bar)
    print(f"  HEAD: {g['head']}  |  الفرع: {g['branch']}  |  الشجرة: {'متسخة ⚠' if g['dirty'] else 'نظيفة'}")
    print(f"  الفروع الموجودة: {', '.join(g['branches'])}")
    print('-' * 62)

    # [1] تطابق ARCHETYPES
    print(f"  [1] تطابق ARCHETYPES: {parity['status']}"
          f"  (engine={parity.get('engine_count')}  app={parity.get('app_count')})")
    if parity.get('in_engine_not_app'):
        print(f"      ⚠ في المحرّك وغائبة عن app (يسقط lookup → random): {parity['in_engine_not_app']}")
    if parity.get('in_app_not_engine'):
        print(f"      ⚠ في app وغائبة عن المحرّك: {parity['in_app_not_engine']}")
    if parity.get('dups'):
        print(f"      ⚠ id مكرّر: {parity['dups']}")
    if parity['status'] != 'PASS':
        fails.append('ARCHETYPES-parity')

    # [2] قانون 4 — نص احتياطي كتقييم
    print(f"  [2] قانون 4 (نص احتياطي كتقييم): {'مشبوه ⚠' if fb else 'نظيف'}")
    for h in fb:
        print(f"      ⚠ {h[0]} @ app.py:{h[1]}  {h[2] if len(h) > 2 else ''}")
    if fb:
        fails.append('fallback-as-review(Law4)')

    # [3] فروع غير master
    undoc = [b for b in g['branches'] if b != SANCTIONED_BRANCH]
    danger = [b for b in g['branches'] if b in DANGER_BRANCHES]
    print(f"  [3] فروع غير master: {undoc or 'لا شيء'}")
    if danger:
        print(f"      ☠ فرع خطر معروف (لا يُدمج في master): {danger}")

    # [4] لينت عيّنة المخرَج إن وُجدت
    sample = ROOT / 'SAMPLE_50.txt'
    if sample.exists():
        bad = []
        for i, ln in enumerate(sample.read_text(encoding='utf-8').splitlines(), 1):
            ln = ln.strip()
            if ln and lint_review(ln):
                bad.append((i, lint_review(ln), ln[:30]))
        print(f"  [4] لينت SAMPLE_50.txt: {'نظيف كليًّا' if not bad else str(len(bad)) + ' سطر مخالف'}")
        for b in bad[:8]:
            print(f"      ⚠ سطر {b[0]}: {b[1]}  «{b[2]}»")
        if bad:
            fails.append('output-redline')
    else:
        print('  [4] لينت SAMPLE_50.txt: (غير موجود — تخطّي)')

    # ── صيغة الحكم الإلزامية (حتمية) ──
    status = 'REJECT' if fails else ('CONDITIONAL' if undoc else 'ACCEPT')
    print(bar)
    print('  صيغة الحكم الإلزامية — حتمية ومربوطة بـ git (غير قابلة للتلفيق):')
    print(f"STATUS: {status}")
    print(f"EVIDENCE_SEEN: نعم — تحليل AST + git على HEAD {g['head']} (فحص حتمي لا منقول)")
    print(f"SYNC_TRAP_CHECKED: ARCHETYPES({parity['status']}) / fallback({'HIT' if fb else 'clean'})"
          f" / branches({len(undoc)}-غير-موثّق)")
    print("VISION_PASS: لا ينطبق — فحص بنية لا توليد")
    print(f"NEXT_COMMAND: {'أصلح: ' + ' ؛ '.join(fails) if fails else ('راجع الفروع غير الموثّقة' if undoc else 'المرور نظيف — تابع')}")
    print(bar)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
