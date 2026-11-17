import os
import re
import secrets
import sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'local-development-only-change-me'), DATABASE=str(BASE / 'food.db'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def connect():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS foods (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, description TEXT NOT NULL, available INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, customer TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Шинэ', created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, food_id INTEGER NOT NULL, quantity INTEGER NOT NULL, price INTEGER NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(food_id) REFERENCES foods(id));
        ''')
        if db.execute('SELECT COUNT(*) FROM foods').fetchone()[0] == 0:
            db.executemany('INSERT INTO foods(name,price,description) VALUES (?,?,?)', [
                ('Үхрийн махтай бургер', 16000, 'Шинэхэн ногоо, соустай'),
                ('Пепперони пицца', 28000, 'Бяслаг, пепперони'),
                ('Тахианы сет', 22000, 'Шарсан тахиа, төмс'),
                ('Цезарь салат', 14000, 'Тахиа, салат навч')])


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Эхлээд нэвтэрнэ үү.', 'warning')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped


def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(24)
    return session['_csrf']


@app.context_processor
def inject_csrf():
    return {'csrf_token': csrf_token}


@app.before_request
def csrf_protect():
    if request.method == 'POST':
        supplied = request.form.get('csrf_token', '')
        if not secrets.compare_digest(supplied, session.get('_csrf', '')) or not supplied:
            abort(400, description='Хүсэлт баталгаажаагүй байна.')


@app.get('/')
def home():
    with connect() as db:
        foods = db.execute('SELECT * FROM foods WHERE available=1').fetchall()
    return render_template('index.html', foods=foods)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not (3 <= len(username) <= 40) or not re.fullmatch(r'[A-Za-z0-9_]+', username) or len(password) < 8:
            flash('Нэр 3–40 латин үсэг/тоо, нууц үг 8-аас дээш тэмдэгт байна.', 'danger')
        else:
            try:
                with connect() as db:
                    db.execute('INSERT INTO users(username,password_hash) VALUES (?,?)', (username, generate_password_hash(password)))
                flash('Бүртгэл амжилттай. Нэвтэрнэ үү.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Энэ хэрэглэгчийн нэр бүртгэлтэй байна.', 'danger')
    return render_template('auth.html', mode='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE username=?', (request.form.get('username', '').strip(),)).fetchone()
        if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Амжилттай нэвтэрлээ.', 'success')
            return redirect(url_for('home'))
        flash('Нэвтрэх нэр эсвэл нууц үг буруу байна.', 'danger')
    return render_template('auth.html', mode='login')


@app.post('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('home'))


def basket():
    raw = session.get('cart', {})
    with connect() as db:
        foods = {str(f['id']): f for f in db.execute('SELECT * FROM foods WHERE available=1')}
    items = []
    for key, qty in raw.items():
        if key in foods and type(qty) is int and 1 <= qty <= 20:
            items.append({'food': foods[key], 'quantity': qty, 'subtotal': qty * foods[key]['price']})
    return items, sum(item['subtotal'] for item in items)


@app.post('/cart/add/<int:food_id>')
@login_required
def add_cart(food_id):
    with connect() as db:
        food = db.execute('SELECT * FROM foods WHERE id=? AND available=1', (food_id,)).fetchone()
    if not food:
        flash('Хоол олдсонгүй!', 'danger')
        return redirect(url_for('home'))
    try:
        quantity = int(request.form.get('quantity', ''))
    except (TypeError, ValueError):
        flash('Тоо ширхэг буруу байна!', 'danger')
        return redirect(url_for('home'))
    if not 1 <= quantity <= 20:
        flash('Тоо ширхэг 1–20 хооронд байна.', 'danger')
        return redirect(url_for('home'))
    cart_data = session.get('cart', {})
    key = str(food_id)
    if cart_data.get(key, 0) + quantity > 20:
        flash('Нэг хоолноос хамгийн ихдээ 20 ширхэг захиална.', 'danger')
        return redirect(url_for('cart'))
    cart_data[key] = cart_data.get(key, 0) + quantity
    session['cart'] = cart_data
    flash('Хоол сагсанд нэмэгдлээ!', 'success')
    return redirect(url_for('cart'))


@app.get('/cart')
@login_required
def cart():
    items, total = basket()
    return render_template('cart.html', items=items, total=total)


@app.post('/checkout')
@login_required
def checkout():
    items, total = basket()
    customer = request.form.get('customer', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    if not items or not (2 <= len(customer) <= 100) or not re.fullmatch(r'\d{8}', phone) or not (5 <= len(address) <= 200):
        flash('Сагс болон нэр, 8 оронтой утас, хүргэлтийн хаягаа шалгана уу.', 'danger')
        return redirect(url_for('cart'))
    with connect() as db:
        cursor = db.execute('INSERT INTO orders(user_id,customer,phone,address,total) VALUES (?,?,?,?,?)', (session['user_id'], customer, phone, address, total))
        order_id = cursor.lastrowid
        db.executemany('INSERT INTO order_items(order_id,food_id,quantity,price) VALUES (?,?,?,?)', [(order_id, item['food']['id'], item['quantity'], item['food']['price']) for item in items])
    session.pop('cart', None)
    return redirect(url_for('order_detail', order_id=order_id))


@app.get('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    with connect() as db:
        order = db.execute('SELECT * FROM orders WHERE id=? AND user_id=?', (order_id, session['user_id'])).fetchone()
        if order is None:
            abort(404)
        items = db.execute('SELECT f.name, oi.quantity, oi.price FROM order_items oi JOIN foods f ON f.id=oi.food_id WHERE oi.order_id=?', (order_id,)).fetchall()
    return render_template('success.html', order=order, items=items)


@app.get('/orders')
@login_required
def orders():
    with connect() as db:
        rows = db.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC', (session['user_id'],)).fetchall()
    return render_template('orders.html', orders=rows)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
