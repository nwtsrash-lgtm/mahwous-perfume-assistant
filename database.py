"""
مدير قاعدة البيانات - نظام أتمتة العطور السعودية
Database Manager - Saudi Perfume Automation System

يدير جميع عمليات قاعدة البيانات باستخدام SQLite
Manages all database operations using SQLite
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


class Database:
    """
    مدير قاعدة بيانات العطور
    Handles all CRUD operations for personas, products, orders, and reviews.
    """

    def __init__(self, db_path='perfume_bot.db'):
        """
        تهيئة مدير قاعدة البيانات
        :param db_path: مسار ملف قاعدة البيانات
        """
        self.db_path = db_path
        # إنشاء الجداول عند التهيئة
        self.init_db()

    @contextmanager
    def _get_connection(self):
        """
        Context manager للاتصال بقاعدة البيانات
        يضمن إغلاق الاتصال حتى في حالة حدوث خطأ
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # إرجاع النتائج كقواميس
            conn.execute("PRAGMA foreign_keys = ON")  # تفعيل مفاتيح الربط الأجنبية
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            print(f"[خطأ في قاعدة البيانات] {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_db(self):
        """
        إنشاء الجداول إذا لم تكن موجودة
        Creates all tables if they don't exist.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # جدول الشخصيات الوهمية
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS personas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        gender TEXT NOT NULL CHECK(gender IN ('male', 'female')),
                        email TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول المنتجات
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        store_name TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        price REAL,
                        url TEXT,
                        image_url TEXT,
                        category TEXT,
                        trend_rank INTEGER,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول الطلبات
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        persona_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_cart', 'checkout', 'delivered', 'reviewed')),
                        FOREIGN KEY (persona_id) REFERENCES personas(id),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                """)

                # جدول التقييمات
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        review_text TEXT NOT NULL,
                        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id)
                    )
                """)

                print("[✓] تم تهيئة قاعدة البيانات بنجاح")

        except sqlite3.Error as e:
            print(f"[✗] فشل في تهيئة قاعدة البيانات: {e}")

    # ─────────────────────────────────────────────
    #  عمليات الشخصيات - Persona Operations
    # ─────────────────────────────────────────────

    def add_persona(self, name, gender, email=''):
        """
        إضافة شخصية جديدة
        :param name: اسم الشخصية
        :param gender: الجنس ('male' أو 'female')
        :param email: الإيميل المؤقت
        :return: معرّف الشخصية الجديدة أو None في حالة الخطأ
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO personas (name, gender, email) VALUES (?, ?, ?)",
                    (name, gender, email)
                )
                persona_id = cursor.lastrowid
                print(f"[+] تمت إضافة الشخصية: {name} (ID: {persona_id})")
                return persona_id
        except sqlite3.Error as e:
            print(f"[✗] فشل في إضافة الشخصية: {e}")
            return None

    def get_personas(self):
        """
        جلب جميع الشخصيات
        :return: قائمة بقواميس الشخصيات
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM personas ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[✗] فشل في جلب الشخصيات: {e}")
            return []

    # ─────────────────────────────────────────────
    #  عمليات المنتجات - Product Operations
    # ─────────────────────────────────────────────

    def add_product(self, store_name, product_name, price=None, url=None,
                    image_url=None, category=None, trend_rank=None):
        """
        إضافة منتج جديد
        :return: معرّف المنتج الجديد أو None في حالة الخطأ
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO products 
                       (store_name, product_name, price, url, image_url, category, trend_rank)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (store_name, product_name, price, url, image_url, category, trend_rank)
                )
                product_id = cursor.lastrowid
                print(f"[+] تمت إضافة المنتج: {product_name} (ID: {product_id})")
                return product_id
        except sqlite3.Error as e:
            print(f"[✗] فشل في إضافة المنتج: {e}")
            return None

    def get_products(self, store_name=None):
        """
        جلب المنتجات مع إمكانية التصفية حسب المتجر
        :param store_name: اسم المتجر (اختياري) للتصفية
        :return: قائمة بقواميس المنتجات
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if store_name:
                    cursor.execute(
                        "SELECT * FROM products WHERE store_name = ? ORDER BY trend_rank ASC, scraped_at DESC",
                        (store_name,)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM products ORDER BY trend_rank ASC, scraped_at DESC"
                    )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[✗] فشل في جلب المنتجات: {e}")
            return []

    # ─────────────────────────────────────────────
    #  عمليات الطلبات - Order Operations
    # ─────────────────────────────────────────────

    def add_order(self, persona_id, product_id):
        """
        إنشاء طلب جديد
        :param persona_id: معرّف الشخصية
        :param product_id: معرّف المنتج
        :return: معرّف الطلب الجديد أو None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO orders (persona_id, product_id) VALUES (?, ?)",
                    (persona_id, product_id)
                )
                order_id = cursor.lastrowid
                print(f"[+] تم إنشاء الطلب: (ID: {order_id})")
                return order_id
        except sqlite3.Error as e:
            print(f"[✗] فشل في إنشاء الطلب: {e}")
            return None

    def update_order_status(self, order_id, status):
        """
        تحديث حالة الطلب
        :param order_id: معرّف الطلب
        :param status: الحالة الجديدة (pending/in_cart/checkout/delivered/reviewed)
        """
        valid_statuses = ('pending', 'in_cart', 'checkout', 'delivered', 'reviewed')
        if status not in valid_statuses:
            print(f"[✗] حالة غير صالحة: {status}. الحالات المسموحة: {valid_statuses}")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE orders SET status = ? WHERE id = ?",
                    (status, order_id)
                )
                if cursor.rowcount == 0:
                    print(f"[✗] لم يتم العثور على الطلب: {order_id}")
                    return False
                print(f"[✓] تم تحديث حالة الطلب {order_id} إلى: {status}")
                return True
        except sqlite3.Error as e:
            print(f"[✗] فشل في تحديث حالة الطلب: {e}")
            return False

    def get_orders(self):
        """
        جلب جميع الطلبات مع أسماء الشخصيات والمنتجات
        :return: قائمة بقواميس الطلبات (مع JOIN)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        o.id,
                        o.persona_id,
                        p.name AS persona_name,
                        p.email AS persona_email,
                        o.product_id,
                        pr.product_name,
                        pr.store_name,
                        pr.price,
                        o.order_date,
                        o.status
                    FROM orders o
                    JOIN personas p ON o.persona_id = p.id
                    JOIN products pr ON o.product_id = pr.id
                    ORDER BY o.order_date DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[✗] فشل في جلب الطلبات: {e}")
            return []

    # ─────────────────────────────────────────────
    #  عمليات التقييمات - Review Operations
    # ─────────────────────────────────────────────

    def add_review(self, order_id, review_text, rating):
        """
        إضافة تقييم لطلب معين
        :param order_id: معرّف الطلب
        :param review_text: نص التقييم
        :param rating: التقييم (1-5)
        :return: معرّف التقييم الجديد أو None
        """
        if not (1 <= rating <= 5):
            print(f"[✗] التقييم يجب أن يكون بين 1 و 5، القيمة المدخلة: {rating}")
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO reviews (order_id, review_text, rating) VALUES (?, ?, ?)",
                    (order_id, review_text, rating)
                )
                review_id = cursor.lastrowid
                # تحديث حالة الطلب إلى "تمت المراجعة"
                cursor.execute(
                    "UPDATE orders SET status = 'reviewed' WHERE id = ?",
                    (order_id,)
                )
                print(f"[+] تمت إضافة التقييم: (ID: {review_id})")
                return review_id
        except sqlite3.Error as e:
            print(f"[✗] فشل في إضافة التقييم: {e}")
            return None

    def get_reviews(self, order_id=None):
        """
        جلب التقييمات مع إمكانية التصفية حسب الطلب
        :param order_id: معرّف الطلب (اختياري)
        :return: قائمة بقواميس التقييمات
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if order_id:
                    cursor.execute(
                        """SELECT r.*, o.product_id, p.product_name
                           FROM reviews r
                           JOIN orders o ON r.order_id = o.id
                           JOIN products p ON o.product_id = p.id
                           WHERE r.order_id = ?
                           ORDER BY r.generated_at DESC""",
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        """SELECT r.*, o.product_id, p.product_name
                           FROM reviews r
                           JOIN orders o ON r.order_id = o.id
                           JOIN products p ON o.product_id = p.id
                           ORDER BY r.generated_at DESC"""
                    )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[✗] فشل في جلب التقييمات: {e}")
            return []

    # ─────────────────────────────────────────────
    #  الإحصائيات - Statistics
    # ─────────────────────────────────────────────

    def get_stats(self):
        """
        جلب إحصائيات عامة عن قاعدة البيانات
        :return: قاموس بالإحصائيات
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # عدد الشخصيات
                cursor.execute("SELECT COUNT(*) FROM personas")
                stats['total_personas'] = cursor.fetchone()[0]

                # عدد المنتجات
                cursor.execute("SELECT COUNT(*) FROM products")
                stats['total_products'] = cursor.fetchone()[0]

                # عدد الطلبات حسب الحالة
                cursor.execute("SELECT COUNT(*) FROM orders")
                stats['total_orders'] = cursor.fetchone()[0]

                cursor.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
                stats['orders_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}

                # عدد التقييمات
                cursor.execute("SELECT COUNT(*) FROM reviews")
                stats['total_reviews'] = cursor.fetchone()[0]

                # متوسط التقييم
                cursor.execute("SELECT AVG(rating) FROM reviews")
                avg = cursor.fetchone()[0]
                stats['average_rating'] = round(avg, 2) if avg else 0.0

                # عدد المتاجر الفريدة
                cursor.execute("SELECT COUNT(DISTINCT store_name) FROM products")
                stats['unique_stores'] = cursor.fetchone()[0]

                print(f"[📊] الإحصائيات: {stats['total_personas']} شخصية، "
                      f"{stats['total_products']} منتج، "
                      f"{stats['total_orders']} طلب، "
                      f"{stats['total_reviews']} تقييم")

                return stats

        except sqlite3.Error as e:
            print(f"[✗] فشل في جلب الإحصائيات: {e}")
            return {
                'total_personas': 0,
                'total_products': 0,
                'total_orders': 0,
                'orders_by_status': {},
                'total_reviews': 0,
                'average_rating': 0.0,
                'unique_stores': 0
            }


# ─────────────────────────────────────────────
#  اختبار سريع - Quick Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    db = Database("test_perfume_bot.db")

    # اختبار إضافة شخصية
    pid = db.add_persona("محمد", "male")
    # اختبار إضافة منتج
    prod_id = db.add_product("خبير العطور", "عود كمبودي", 250.0,
                              "https://example.com/product/1", None, "oud", 1)
    # اختبار إنشاء طلب
    if pid and prod_id:
        oid = db.add_order(pid, prod_id)
        if oid:
            db.update_order_status(oid, "delivered")
            db.add_review(oid, "عطر ممتاز وريحته فخمة!", 5)

    # عرض الإحصائيات
    stats = db.get_stats()
    print(f"\nالإحصائيات: {stats}")

    # تنظيف ملف الاختبار
    if os.path.exists("test_perfume_bot.db"):
        os.remove("test_perfume_bot.db")
        print("[✓] تم حذف ملف الاختبار")
