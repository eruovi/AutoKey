from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = 'autokey-secret2026'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app)

PRICES = [
    {'service': 'Изготовление ключа', 'price': 'от 500 руб.', 'time': '30 мин'},
    {'service': 'Программирование чип-ключа', 'price': 'от 1000 руб.', 'time': '15 мин'},
    {'service': 'Аварийное вскрытие автомобиля', 'price': 'от 1500 руб.', 'time': '1-2 часа'},
    {'service': 'Ремонт замка зажигания', 'price': 'от 2000 руб.', 'time': '1 час'},
]

CAR_BRANDS = {
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Land Cruiser', 'Prius'],
    'Volkswagen': ['Polo', 'Passat', 'Golf', 'Tiguan', 'Touareg'],
    'BMW': ['3 Series', '5 Series', 'X3', 'X5', 'X6'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLC', 'GLE'],
    'LADA': ['Granta', 'Vesta', 'Niva', 'Largus', 'XRAY'],
    'Kia': ['Rio', 'Ceed', 'Sportage', 'Sorento', 'Cerato'],
    'Hyundai': ['Solaris', 'Elantra', 'Creta', 'Tucson', 'Santa Fe'],
    'Renault': ['Logan', 'Duster', 'Sandero', 'Megane', 'Kaptur'],
    'Nissan': ['Almera', 'Qashqai', 'X-Trail', 'Teana', 'Juke'],
    'Ford': ['Focus', 'Mondeo', 'Kuga', 'Fiesta', 'Explorer'],
    'Skoda': ['Rapid', 'Octavia', 'Superb', 'Kodiaq', 'Yeti'],
    'Audi': ['A4', 'A6', 'Q3', 'Q5', 'Q7']
}


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='client')
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    consent_accepted = db.Column(db.Boolean, default=False)
    consent_at = db.Column(db.DateTime, nullable=True)

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


def send_email(to_email, subject, html_message):
    smtp_host = os.getenv('MAIL_SERVER')
    smtp_port = int(os.getenv('MAIL_PORT', 587))
    smtp_user = os.getenv('MAIL_USERNAME')
    smtp_password = os.getenv('MAIL_PASSWORD')
    from_email = os.getenv('MAIL_FROM', smtp_user)

    if not smtp_host or not smtp_user or not smtp_password or not to_email:
        return

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_message, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print('Ошибка отправки email:', e)


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
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip().lower()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        consent = request.form.get('consent')

        if not consent:
            flash('Нужно подтвердить согласие на обработку персональных данных.')
            return render_template('register.html')

        if not re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Введите корректный email.')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует.')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.')
            return render_template('register.html')

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=generate_password_hash(password),
            role='client',
            consent_accepted=True,
            consent_at=db.func.now()
        )
        db.session.add(user)
        db.session.commit()

        send_email(
            email,
            'Регистрация в AutoKey',
            f'''
            <h2>Здравствуйте, {first_name} {last_name}!</h2>
            <p>Вы успешно зарегистрировались на сайте AutoKey.</p>
            <p>Ваш логин: <b>{username}</b></p>
            <p>Теперь вы можете входить в личный кабинет и отслеживать свои заявки.</p>
            '''
        )

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
            session['first_name'] = user.first_name or ''
            session['last_name'] = user.last_name or ''
            session['email'] = user.email or ''

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('admin_orders'))
            else:
                return redirect(url_for('my_orders'))

        flash('Неверный логин или пароль.')

    return render_template('login.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.role not in ['admin', 'manager']:
                flash('Доступ разрешён только персоналу.')
                return render_template('admin_login.html')

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['first_name'] = user.first_name or ''
            session['last_name'] = user.last_name or ''
            session['email'] = user.email or ''

            if user.role == 'manager':
                return redirect(url_for('admin_orders'))

            return redirect(url_for('admin_dashboard'))

        flash('Неверный логин или пароль.')

    return render_template('admin_login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.')
    return redirect(url_for('index'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Вы вышли из панели персонала.')
    return redirect(url_for('admin_login'))


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


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    current_user = None
    if session.get('user_id'):
        current_user = User.query.get(session['user_id'])

    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        phone = request.form['phone'].strip()
        brand = request.form['brand'].strip()
        car_model = request.form['car_model'].strip()
        service = request.form['service'].strip()

        full_name = f'{first_name} {last_name}'.strip()

        valid_models = CAR_BRANDS.get(brand, [])
        if car_model not in valid_models:
            flash('Выберите реальную модель автомобиля из списка.')
            return render_template('contact.html', user=current_user, car_brands=CAR_BRANDS)

        if not re.fullmatch(r'\+7[0-9]{10}', phone):
            flash('Введите номер телефона в формате +79991234567')
            return render_template('contact.html', user=current_user, car_brands=CAR_BRANDS)

        order = Order(
            name=full_name,
            phone=phone,
            car_model=f'{brand} {car_model}',
            service=service,
            user_id=session.get('user_id')
        )
        db.session.add(order)
        db.session.commit()

        if current_user and current_user.email:
            send_email(
                current_user.email,
                'Ваша заявка принята',
                f'''
                <h2>Здравствуйте, {full_name}!</h2>
                <p>Ваша заявка успешно создана.</p>
                <p><b>Автомобиль:</b> {brand} {car_model}</p>
                <p><b>Услуга:</b> {service}</p>
                <p><b>Статус:</b> новая</p>
                '''
            )

        flash('Заявка успешно отправлена.')
        return redirect(url_for('contact'))

    return render_template('contact.html', user=current_user, car_brands=CAR_BRANDS)


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        if not session.get('user_id'):
            flash('Чтобы оставить отзыв, сначала войдите в аккаунт.')
            return redirect(url_for('login'))

        author = request.form['author'].strip()
        text = request.form['text'].strip()
        rating = int(request.form['rating'])

        review = Review(
            author=author,
            text=text,
            rating=rating,
            is_published=True
        )
        db.session.add(review)
        db.session.commit()
        flash('Спасибо! Ваш отзыв опубликован.')
        return redirect(url_for('reviews'))

    reviews_list = Review.query.filter_by(is_published=True).order_by(Review.id.desc()).all()
    return render_template('reviews.html', reviews=reviews_list)


@app.route('/admin')
@manager_required
def admin_dashboard():
    orders = Order.query.order_by(Order.id.desc()).all()
    total = Order.query.count()
    new = Order.query.filter_by(status='новая').count()
    done = Order.query.filter_by(status='выполнена').count()
    reviews_count = Review.query.count()

    return render_template(
        'admin/dashboard.html',
        total=total,
        new=new,
        done=done,
        orders=orders,
        reviews_count=reviews_count
    )


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

    if order.user_id:
        user = User.query.get(order.user_id)
        if user and user.email:
            send_email(
                user.email,
                'Изменён статус заявки',
                f'''
                <h2>Здравствуйте, {user.first_name or user.username}!</h2>
                <p>Статус вашей заявки изменён.</p>
                <p><b>Заявка:</b> #{order.id}</p>
                <p><b>Услуга:</b> {order.service}</p>
                <p><b>Автомобиль:</b> {order.car_model}</p>
                <p><b>Новый статус:</b> {order.status}</p>
                '''
            )

    flash('Статус заявки обновлён.')
    return redirect(url_for('admin_orders'))


@app.route('/admin/order/<int:id>/delete', methods=['POST'])
@admin_required
def admin_order_delete(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash('Заявка удалена.')
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
    flash('Отзыв удалён.')
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


def add_missing_columns():
    with db.engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()]

        if 'first_name' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR(100)"))
        if 'last_name' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_name VARCHAR(100)"))
        if 'email' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(150)"))
        if 'consent_accepted' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN consent_accepted BOOLEAN DEFAULT 0"))
        if 'consent_at' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN consent_at DATETIME"))
        conn.commit()


with app.app_context():
    db.create_all()
    add_missing_columns()

    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin',
            first_name='Главный',
            last_name='Администратор',
            email='admin@example.com',
            consent_accepted=True
        )
        db.session.add(admin_user)
        db.session.commit()

    if not User.query.filter_by(username='manager').first():
        manager_user = User(
            username='manager',
            password=generate_password_hash('manager123'),
            role='manager',
            first_name='Менеджер',
            last_name='AutoKey',
            email='manager@example.com',
            consent_accepted=True
        )
        db.session.add(manager_user)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)