from textwrap import dedent
code = dedent('''
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')


app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = 'autokey-secret2026'


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}


db = SQLAlchemy(app)


print('BASE_DIR =', BASE_DIR)
print('TEMPLATES_DIR =', TEMPLATES_DIR)
print('templates exists =', os.path.exists(TEMPLATES_DIR))
print('myorders exists =', os.path.exists(os.path.join(TEMPLATES_DIR, 'myorders.html')))
print('admin_login exists =', os.path.exists(os.path.join(TEMPLATES_DIR, 'admin_login.html')))
print('login exists =', os.path.exists(os.path.join(TEMPLATES_DIR, 'login.html')))


PRICES = [
    {'service': 'Изготовление ключа', 'price': 'от 500 руб.', 'time': '30 мин'},
    {'service': 'Программирование чип-ключа', 'price': 'от 1000 руб.', 'time': '15 мин'},
    {'service': 'Аварийное вскрытие автомобиля', 'price': 'от 1500 руб.', 'time': '1-2 часа'},
    {'service': 'Ремонт замка зажигания', 'price': 'от 2000 руб.', 'time': '1 час'},
]


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='client')
    orders = db.relationship('Order', backref='user', lazy=True)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    car_model = db.Column(db.String(100), nullable=False)
    service = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='новая')
    created_at = db.Column(db.DateTime, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Доступ разрешён только администратору.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ['admin', 'manager']:
            flash('Доступ разрешён только персоналу.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует.')
            return render_template('register.html')
        user = User(username=username, password=generate_password_hash(password), role='client')
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно. Теперь войдите в аккаунт.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('admin_orders'))
            else:
                return redirect(url_for('my_orders'))
        flash('Неверный логин или пароль.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.')
    return redirect(url_for('index'))


@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.id.desc()).all()
    return render_template('myorders.html', orders=orders)


@app.route('/')
def index():
    reviews = Review.query.filter_by(is_published=True).order_by(Review.id.desc()).limit(6).all()
    return render_template('index.html', reviews=reviews)


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/prices')
def prices():
    return render_template('prices.html', prices=PRICES)


@app.route('/gallery')
def gallery():
    return render_template('gallery.html')


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        car_model = request.form['car_model'].strip()
        service = request.form['service'].strip()
        if not re.fullmatch(r'\+7[0-9]{10}', phone):
            flash('Введите номер телефона в формате +79991234567')
            return redirect(url_for('contact'))
        order = Order(name=name, phone=phone, car_model=car_model, service=service, user_id=session.get('user_id'))
        db.session.add(order)
        db.session.commit()
        flash('Заявка успешно отправлена.')
        return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        if not session.get('user_id'):
            flash('Чтобы оставить отзыв, сначала войдите в аккаунт.')
            return redirect(url_for('login'))
        author = request.form['author'].strip()
        text = request.form['text'].strip()
        rating = int(request.form['rating'])
        review = Review(author=author, text=text, rating=rating, is_published=True)
        db.session.add(review)
        db.session.commit()
        flash('Спасибо! Ваш отзыв опубликован.')
        return redirect(url_for('reviews'))
    reviews_list = Review.query.filter_by(is_published=True).order_by(Review.id.desc()).all()
    return render_template('reviews.html', reviews=reviews_list)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password) and user.role in ['admin', 'manager']:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('admin_dashboard'))
        flash('Доступ разрешён только персоналу.')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin')
@manager_required
def admin_dashboard():
    orders = Order.query.order_by(Order.id.desc()).all()
    total = Order.query.count()
    new = Order.query.filter_by(status='новая').count()
    done = Order.query.filter_by(status='выполнена').count()
    reviews_count = Review.query.count()
    return render_template('admin/dashboard.html', total=total, new=new, done=done, orders=orders, reviews_count=reviews_count)


@app.route('/admin/orders')
@manager_required
def admin_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/order/<int:id>/status', methods=['POST'])
@manager_required
def admin_order_status(id):
    order = Order.query.get_or_404(id)
    order.status = request.form['status']
    db.session.commit()
    return redirect(url_for('admin_orders'))


@app.route('/admin/order/<int:id>/delete', methods=['POST'])
@admin_required
def admin_order_delete(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('admin_orders'))


@app.route('/admin/prices', methods=['GET', 'POST'])
@manager_required
def admin_prices():
    global PRICES
    if request.method == 'POST':
        services = request.form.getlist('service')
        prices_list = request.form.getlist('price')
        times = request.form.getlist('time')
        count = min(len(services), len(prices_list), len(times), len(PRICES))
        for i in range(count):
            PRICES[i]['service'] = services[i]
            PRICES[i]['price'] = prices_list[i]
            PRICES[i]['time'] = times[i]
        flash('Прайс успешно обновлён.')
        return redirect(url_for('admin_prices'))
    return render_template('admin/prices.html', prices=PRICES)


@app.route('/admin/reviews')
@manager_required
def admin_reviews():
    reviews_list = Review.query.order_by(Review.id.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews_list)


@app.route('/admin/review/<int:id>/toggle', methods=['POST'])
@manager_required
def admin_review_toggle(id):
    review = Review.query.get_or_404(id)
    review.is_published = not review.is_published
    db.session.commit()
    return redirect(url_for('admin_reviews'))


@app.route('/admin/review/<int:id>/delete', methods=['POST'])
@admin_required
def admin_review_delete(id):
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for('admin_reviews'))


@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/user/<int:id>/role', methods=['POST'])
@admin_required
def admin_user_role(id):
    user = User.query.get_or_404(id)
    user.role = request.form['role']
    db.session.commit()
    flash('Роль пользователя обновлена.')
    return redirect(url_for('admin_users'))


def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin_user)
            db.session.commit()
            print('Создан админ: логин admin, пароль admin123')


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
''')
open('output/app_fixed.py','w',encoding='utf-8').write(code)
open('output/app_fixed.txt','w',encoding='utf-8').write(code)
print('saved')