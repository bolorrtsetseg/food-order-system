import os
import tempfile
import unittest
from pathlib import Path
from werkzeug.security import generate_password_hash
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app, connect, init_db


class Lab5Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=os.path.join(self.tmp.name, 'test.db'), SECRET_KEY='test-only-key')
        init_db()
        with connect() as db:
            db.execute('INSERT INTO users(username,password_hash) VALUES (?,?)', ('student', generate_password_hash('password123')))
        self.client = app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def token(self):
        with self.client.session_transaction() as s:
            s['_csrf'] = 'test-token'
        return 'test-token'

    def post(self, url, data):
        return self.client.post(url, data={**data, 'csrf_token': self.token()}, follow_redirects=True)

    def login(self):
        return self.post('/login', {'username': 'student', 'password': 'password123'})

    def test_TC01_valid_login(self):
        r = self.login()
        self.assertIn('Амжилттай нэвтэрлээ'.encode(), r.data)
        with self.client.session_transaction() as s:
            self.assertIn('user_id', s)

    def test_TC02_add_food(self):
        self.login()
        r = self.post('/cart/add/1', {'quantity': '2'})
        self.assertIn('32,000'.encode(), r.data)
        with self.client.session_transaction() as s:
            self.assertEqual(s['cart']['1'], 2)

    def test_TC03_unknown_food(self):
        self.login()
        r = self.post('/cart/add/99999', {'quantity': '1'})
        self.assertIn('Хоол олдсонгүй'.encode(), r.data)

    def test_TC04_login_required(self):
        r = self.post('/cart/add/1', {'quantity': '1'})
        self.assertIn('Нэвтрэх'.encode(), r.data)
        with self.client.session_transaction() as s:
            self.assertNotIn('cart', s)

    def test_TC05_zero_quantity(self):
        self.login()
        r = self.post('/cart/add/1', {'quantity': '0'})
        self.assertIn('1–20'.encode(), r.data)
        with self.client.session_transaction() as s:
            self.assertNotIn('cart', s)

    def test_TC06_letters_quantity(self):
        self.login()
        r = self.post('/cart/add/1', {'quantity': 'abc'})
        self.assertIn('Тоо ширхэг буруу'.encode(), r.data)
        with self.client.session_transaction() as s:
            self.assertNotIn('cart', s)

    def test_checkout_and_private_orders(self):
        self.login()
        self.post('/cart/add/1', {'quantity': '2'})
        r = self.post('/checkout', {'customer': 'Test User', 'phone': '99112233', 'address': 'Ulaanbaatar Bayanzurkh'})
        self.assertIn('Захиалга амжилттай'.encode(), r.data)
        with connect() as db:
            order = db.execute('SELECT * FROM orders').fetchone()
            self.assertEqual(order['total'], 32000)
            self.assertEqual(order['user_id'], 1)
        self.post('/logout', {})
        with connect() as db:
            db.execute('INSERT INTO users(username,password_hash) VALUES (?,?)', ('another', generate_password_hash('password123')))
        self.post('/login', {'username': 'another', 'password': 'password123'})
        self.assertEqual(self.client.get('/orders/1').status_code, 404)

    def test_csrf_rejected(self):
        self.login()
        r = self.client.post('/cart/add/1', data={'quantity': '1'})
        self.assertEqual(r.status_code, 400)


if __name__ == '__main__':
    unittest.main()
