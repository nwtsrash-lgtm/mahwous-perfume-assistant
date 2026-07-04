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
import json
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


ENTRY_FILES = ['app.py', 'streamlit_app.py']       # مدخلا التطبيق (مصيدة #2) — يُمسحان معًا
_FAKE_FUNC = re.compile(r'fallback|dummy|fake|template', re.I)


def _call_name(f):
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _review_dicts(value):
    """قواميس التقييم داخل قيمة return: dict مباشر / list / list-comprehension."""
    if isinstance(value, ast.Dict):
        return [value]
    if isinstance(value, ast.List):
        return [e for e in value.elts if isinstance(e, ast.Dict)]
    if isinstance(value, ast.ListComp) and isinstance(value.elt, ast.Dict):
        return [value.elt]
    return []


def _fake_text_class(tv, lit_vars):
    """يصنّف قيمة 'text' إن كانت فبركة (ليست ناتج الـ AI). يرجع تصنيفًا أو None."""
    if isinstance(tv, ast.Constant) and isinstance(tv.value, str) and tv.value.strip():
        return 'نص-حرفي'
    if isinstance(tv, ast.Name):
        if tv.id in lit_vars:
            return 'متغيّر-من-نص-حرفي'
        if 'fallback' in tv.id.lower():
            return 'متغيّر-fallback'
    if isinstance(tv, ast.Call):
        fn = _call_name(tv.func)
        if fn and _FAKE_FUNC.search(fn):
            return f'استدعاء-{fn}()'
    return None


def check_fallback_as_review(paths=None):
    """قانون 4 (مصيدة #2): في *أي* دالة، أي return لقاموس تقييم (rating+text) نصّه ليس ناتج الـ AI
    — نص حرفي / متغيّر من نص حرفي / متغيّر fallback / استدعاء دالة fallback|dummy|fake|template —
    = فبركة تُرفض. يمسح مدخلي التطبيق معًا (app.py + streamlit_app.py) عبر AST، بلا تنفيذ."""
    if paths is None:
        paths = [ROOT / f for f in ENTRY_FILES]
    hits = []
    for p in (Path(x) for x in paths):
        if not p.exists():
            continue
        tree = ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
        seen = set()
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            # متغيّرات أُسنِد إليها نص حرفي غير فارغ ولو مرّة داخل هذه الدالة (يلتقط الفرع الاحتياطي)
            lit_vars = {t.id for m in ast.walk(fn)
                        if isinstance(m, ast.Assign) and isinstance(m.value, ast.Constant)
                        and isinstance(m.value.value, str) and m.value.value.strip()
                        for t in m.targets if isinstance(t, ast.Name)}
            for n in ast.walk(fn):
                if not isinstance(n, ast.Return):
                    continue
                for d in _review_dicts(n.value):
                    keys = [k.value for k in d.keys if isinstance(k, ast.Constant)]
                    if 'rating' not in keys or 'text' not in keys:
                        continue
                    tv = next((v for k, v in zip(d.keys, d.values)
                               if isinstance(k, ast.Constant) and k.value == 'text'), None)
                    cls = _fake_text_class(tv, lit_vars)
                    if cls and n.lineno not in seen:
                        seen.add(n.lineno)
                        hits.append((f'{p.name} [text={cls}]', n.lineno, ''))
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


# ──────────── العينة الذهبية — فحص البصمة مقابل المواصفة ────────────
def check_golden_sample():
    """مصيدة #5: golden_sample.json يجب أن يطابق مواصفته المختومة حرفيًا.

    الإيموجي هنا ليس خطًّا أحمر بل حصة مقنّنة (spec.emoji_rate) — الدستور المعدَّل.
    الأرقام تبقى خطًّا أحمر. النزيف الدلالي والبتر والتكرار = رفض.
    يرجع None إذا لا ملف (تخطٍّ)، وإلا قائمة مشاكل (فارغة = PASS).
    """
    p = ROOT / 'golden_sample.json'
    if not p.exists():
        return None
    try:
        from semantic_guard import guard_violations, has_context, has_reservation
    except ImportError:
        return ['semantic_guard.py مفقود — لا يمكن فحص الذهب']
    d = json.loads(p.read_text(encoding='utf-8'))
    reviews, spec = d.get('reviews', []), d.get('spec', {})
    problems = []
    if len(reviews) != 30:
        problems.append(f'العدد {len(reviews)} ≠ 30')
    want = {int(k): v for k, v in spec.get('ratings', {}).items()}
    got = {}
    seen = set()
    emoji_n = 0
    for i, r in enumerate(reviews, 1):
        text, rating = r.get('text', ''), int(r.get('rating', 0))
        got[rating] = got.get(rating, 0) + 1
        if rating < 3:
            problems.append(f'#{i}: نجوم سلبية {rating} داخل الذهب')
        if _EMOJI.search(text):
            emoji_n += 1
        if _DIGIT.search(text):
            problems.append(f'#{i}: أرقام (خط أحمر) «{text[:24]}»')
        gv = guard_violations(text, max_words=spec.get('max_words', 4))
        if gv:
            problems.append(f'#{i}: {"/".join(gv)} «{text[:24]}»')
        key = ' '.join(text.split())
        if key in seen:
            problems.append(f'#{i}: استنساخ حرفي «{text[:24]}»')
        seen.add(key)
    if want and got != want:
        problems.append(f'توزيع النجوم {got} ≠ المواصفة {want}')
    quota = round(len(reviews) * spec.get('emoji_rate', 0))
    if emoji_n != quota:
        problems.append(f'إيموجي {emoji_n} ≠ الحصة {quota}')
    # الحصص العاطفية — تُعاد قراءتها من النصوص نفسها (لا من أعلام مخزّنة قابلة للتلفيق)
    ctx_n = sum(1 for r in reviews if has_context(r.get('text', '')))
    res_n = sum(1 for r in reviews if has_reservation(r.get('text', '')))
    ctx_q = round(len(reviews) * spec.get('context_rate', 0))
    res_q = round(len(reviews) * spec.get('reservation_rate', 0))
    if ctx_n < ctx_q:
        problems.append(f'سياق استخدام {ctx_n} < الحصة {ctx_q}')
    if res_n < res_q:
        problems.append(f'تحفّظ إيجابي {res_n} < الحصة {res_q}')
    return problems


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
    print(f"  [2] قانون 4 (فبركة كتقييم — مسح app.py+streamlit_app.py): {'مشبوه ⚠' if fb else 'نظيف'}")
    for h in fb:
        print(f"      ⚠ {h[0]} @ سطر {h[1]}")
    if fb:
        fails.append('fallback-as-review(Law4)')

    # [3] فروع غير master
    undoc = [b for b in g['branches'] if b != SANCTIONED_BRANCH]
    danger = [b for b in g['branches'] if b in DANGER_BRANCHES]
    print(f"  [3] فروع غير master: {undoc or 'لا شيء'}")
    if danger:
        print(f"      ☠ فرع خطر معروف (لا يُدمج في master): {danger}")

    # [4] لينت مخرجات التوليد الحيّة فقط: sample*.txt (يُستثنى SAMPLE_50.txt — وثيقة مرجعية مرقّمة)
    sample_files = sorted(p for p in ROOT.glob('sample*.txt') if p.name != 'SAMPLE_50.txt')
    if sample_files:
        bad = []
        for sp in sample_files:
            for i, ln in enumerate(sp.read_text(encoding='utf-8').splitlines(), 1):
                ln = ln.strip()
                if ln and lint_review(ln):
                    bad.append((sp.name, i, lint_review(ln), ln[:30]))
        print(f"  [4] لينت مخرجات sample*.txt ({len(sample_files)} ملف): "
              f"{'نظيف كليًّا' if not bad else str(len(bad)) + ' سطر مخالف'}")
        for b in bad[:8]:
            print(f"      ⚠ {b[0]}:{b[1]}: {b[2]}  «{b[3]}»")
        if bad:
            fails.append('output-redline')
    else:
        print('  [4] لينت مخرجات sample*.txt: (لا ملف — تخطّي؛ SAMPLE_50.txt مرجع مُستثنى)')

    # [5] العينة الذهبية — البصمة مقابل المواصفة
    golden = check_golden_sample()
    if golden is None:
        print('  [5] العينة الذهبية golden_sample.json: (لا ملف — تخطّي)')
    else:
        print(f"  [5] العينة الذهبية golden_sample.json: {'مطابقة للمواصفة 🏆' if not golden else str(len(golden)) + ' مخالفة'}")
        for pr in golden[:8]:
            print(f'      ⚠ {pr}')
        if golden:
            fails.append('golden-sample')

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
