# -*- coding: utf-8 -*-
"""طبقة قاعدة البيانات SQLite لمنظومة جمهور حي — Audience Matrix DB Layer
6 جداول: vocabulary_bank, persona_registry, review_history, context_usage, pattern_usage, schedule_queue
"""
import sys
import os
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).parent


class AudienceDB:
    """قاعدة بيانات منظومة جمهور حي"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = str(BASE_DIR / 'audience.db')
        self.db_path = db_path
        self._conn = None
        self.init_tables()
    
    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute('PRAGMA journal_mode=WAL')
            self._conn.execute('PRAGMA foreign_keys=ON')
        return self._conn
    
    def init_tables(self):
        conn = self._get_conn()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS vocabulary_bank (
                word TEXT PRIMARY KEY,
                total_count INTEGER DEFAULT 0,
                last_20_count INTEGER DEFAULT 0,
                last_used_at TEXT,
                is_burned INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS persona_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                archetype TEXT NOT NULL,
                dialect TEXT NOT NULL,
                writing_fingerprint TEXT DEFAULT '{}',
                products_reviewed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER REFERENCES persona_registry(id),
                product_name TEXT,
                review_text TEXT NOT NULL,
                review_type TEXT DEFAULT 'product' CHECK(review_type IN ('product','store')),
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                pattern_used TEXT,
                archetype TEXT,
                dialect TEXT,
                word_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS context_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_type TEXT NOT NULL,
                context_text TEXT NOT NULL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS pattern_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_structure TEXT NOT NULL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS schedule_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER REFERENCES review_history(id),
                scheduled_at TEXT NOT NULL,
                published INTEGER DEFAULT 0,
                published_at TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_review_created ON review_history(created_at);
            CREATE INDEX IF NOT EXISTS idx_review_persona ON review_history(persona_id);
            CREATE INDEX IF NOT EXISTS idx_review_type ON review_history(review_type);
            CREATE INDEX IF NOT EXISTS idx_context_type ON context_usage(context_type);
            CREATE INDEX IF NOT EXISTS idx_schedule_published ON schedule_queue(published);
        ''')
        conn.commit()
    
    # === Vocabulary Bank ===
    def check_vocabulary(self, word, window=20):
        """هل يمكن استخدام الكلمة؟ (أقل من 15% في النافذة)"""
        conn = self._get_conn()
        row = conn.execute('SELECT last_20_count FROM vocabulary_bank WHERE word=?', (word,)).fetchone()
        if row is None:
            return True
        max_allowed = int(window * 0.15)  # 15% = 3 in 20
        return row['last_20_count'] < max_allowed
    
    def update_vocabulary(self, words):
        """تحديث عداد الكلمات بعد توليد تقييم"""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        for word in words:
            conn.execute('''
                INSERT INTO vocabulary_bank (word, total_count, last_20_count, last_used_at)
                VALUES (?, 1, 1, ?)
                ON CONFLICT(word) DO UPDATE SET
                    total_count = total_count + 1,
                    last_20_count = last_20_count + 1,
                    last_used_at = ?
            ''', (word, now, now))
        conn.commit()
    
    def get_burned_words(self, window=20):
        """الكلمات المحترقة (تجاوزت 15%)"""
        conn = self._get_conn()
        max_allowed = int(window * 0.15)
        rows = conn.execute(
            'SELECT word FROM vocabulary_bank WHERE last_20_count >= ?', (max_allowed,)
        ).fetchall()
        return [r['word'] for r in rows]
    
    def reset_vocabulary_window(self):
        """إعادة تعيين النافذة المتحركة"""
        conn = self._get_conn()
        conn.execute('UPDATE vocabulary_bank SET last_20_count = 0')
        conn.commit()
    
    # === Persona Registry ===
    def register_persona(self, name, gender, archetype, dialect, fingerprint=None):
        conn = self._get_conn()
        fp_json = json.dumps(fingerprint or {}, ensure_ascii=False)
        cur = conn.execute(
            'INSERT INTO persona_registry (name, gender, archetype, dialect, writing_fingerprint) VALUES (?,?,?,?,?)',
            (name, gender, archetype, dialect, fp_json)
        )
        conn.commit()
        return cur.lastrowid
    
    def get_persona(self, persona_id):
        conn = self._get_conn()
        row = conn.execute('SELECT * FROM persona_registry WHERE id=?', (persona_id,)).fetchone()
        return dict(row) if row else None
    
    def get_persona_review_count(self, persona_id):
        conn = self._get_conn()
        row = conn.execute('SELECT products_reviewed FROM persona_registry WHERE id=?', (persona_id,)).fetchone()
        return row['products_reviewed'] if row else 0
    
    def increment_persona_reviews(self, persona_id):
        conn = self._get_conn()
        conn.execute('UPDATE persona_registry SET products_reviewed = products_reviewed + 1 WHERE id=?', (persona_id,))
        conn.commit()
    
    # === Review History ===
    def save_review(self, persona_id, product_name, text, review_type, rating, pattern, archetype, dialect):
        conn = self._get_conn()
        word_count = len(text.split())
        cur = conn.execute(
            '''INSERT INTO review_history 
               (persona_id, product_name, review_text, review_type, rating, pattern_used, archetype, dialect, word_count)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (persona_id, product_name, text, review_type, rating, pattern, archetype, dialect, word_count)
        )
        conn.commit()
        return cur.lastrowid
    
    def get_recent_reviews(self, limit=20):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT * FROM review_history ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    
    def get_persona_reviews(self, persona_id):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT * FROM review_history WHERE persona_id=? ORDER BY id DESC', (persona_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    
    def get_review_stats(self):
        conn = self._get_conn()
        total = conn.execute('SELECT COUNT(*) as c FROM review_history').fetchone()['c']
        if total == 0:
            return {'total': 0, 'rating_distribution': {}, 'avg_word_count': 0}
        avg_wc = conn.execute('SELECT AVG(word_count) as a FROM review_history').fetchone()['a']
        dist = {}
        for rating in range(1, 6):
            count = conn.execute('SELECT COUNT(*) as c FROM review_history WHERE rating=?', (rating,)).fetchone()['c']
            dist[rating] = round(count / total * 100, 1)
        return {'total': total, 'rating_distribution': dist, 'avg_word_count': round(avg_wc, 1)}
    
    # === Context Usage ===
    def use_context(self, context_type, context_text=''):
        conn = self._get_conn()
        conn.execute('INSERT INTO context_usage (context_type, context_text) VALUES (?,?)', (context_type, context_text))
        conn.commit()
    
    def is_context_recent(self, context_type, lookback=15):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT context_type FROM context_usage ORDER BY id DESC LIMIT ?', (lookback,)
        ).fetchall()
        return context_type in [r['context_type'] for r in rows]
    
    def get_available_contexts(self, all_contexts, lookback=15):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT context_type FROM context_usage ORDER BY id DESC LIMIT ?', (lookback,)
        ).fetchall()
        recent = {r['context_type'] for r in rows}
        return [c for c in all_contexts if c not in recent]
    
    # === Pattern Usage ===
    def use_pattern(self, pattern_structure):
        conn = self._get_conn()
        conn.execute('INSERT INTO pattern_usage (pattern_structure) VALUES (?)', (pattern_structure,))
        conn.commit()
    
    def is_pattern_recent(self, pattern_structure, lookback=10):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT pattern_structure FROM pattern_usage ORDER BY id DESC LIMIT ?', (lookback,)
        ).fetchall()
        return pattern_structure in [r['pattern_structure'] for r in rows]
    
    # === Schedule Queue ===
    def schedule_review(self, review_id, scheduled_at):
        conn = self._get_conn()
        conn.execute(
            'INSERT INTO schedule_queue (review_id, scheduled_at) VALUES (?,?)',
            (review_id, scheduled_at.isoformat() if hasattr(scheduled_at, 'isoformat') else str(scheduled_at))
        )
        conn.commit()
    
    def get_pending_reviews(self):
        conn = self._get_conn()
        rows = conn.execute(
            'SELECT * FROM schedule_queue WHERE published=0 ORDER BY scheduled_at'
        ).fetchall()
        return [dict(r) for r in rows]
    
    def mark_published(self, review_id):
        conn = self._get_conn()
        conn.execute(
            'UPDATE schedule_queue SET published=1, published_at=? WHERE review_id=?',
            (datetime.now().isoformat(), review_id)
        )
        conn.commit()
    
    def get_schedule_stats(self):
        conn = self._get_conn()
        total = conn.execute('SELECT COUNT(*) as c FROM schedule_queue').fetchone()['c']
        pending = conn.execute('SELECT COUNT(*) as c FROM schedule_queue WHERE published=0').fetchone()['c']
        published = conn.execute('SELECT COUNT(*) as c FROM schedule_queue WHERE published=1').fetchone()['c']
        return {'total': total, 'pending': pending, 'published': published}
    
    # === Utility ===
    def get_full_stats(self):
        return {
            'reviews': self.get_review_stats(),
            'schedule': self.get_schedule_stats(),
            'burned_words': self.get_burned_words(),
            'personas': self._get_conn().execute('SELECT COUNT(*) as c FROM persona_registry').fetchone()['c'],
        }
    
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


if __name__ == '__main__':
    print('=== Audience Matrix DB Test ===')
    db = AudienceDB(':memory:')
    pid = db.register_persona('أحمد', 'male', 'متحمس', 'najdi', {'emoji': '🔥'})
    rid = db.save_review(pid, 'عطر تجريبي', 'ممتاز والله', 'product', 5, 'ultra_short', 'متحمس', 'najdi')
    db.update_vocabulary(['ممتاز', 'والله'])
    stats = db.get_full_stats()
    print(f'✅ DB Stats: {json.dumps(stats, ensure_ascii=False, indent=2)}')
    db.close()
    print('✅ All DB tests passed!')
