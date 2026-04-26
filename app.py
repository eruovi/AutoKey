from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.getenv('SECRET_KEY', 'autokey-secret2026')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app)
serializer = URLSafeTimedSerializer(app.secret_key)

PRICES = [
    {'service': 'Изготовление ключа', 'price': 'от 500 руб.', 'time': '30 мин'},
    {'service': 'Программирование чип-ключа', 'price': 'от 1000 руб.', 'time': '15 мин'},
    {'service': 'Аварийное вскрытие автомобиля', 'price': 'от 1500 руб.', 'time': '1-2 часа'},
    {'service': 'Ремонт замка зажигания', 'price': 'от 2000 руб.', 'time': '1 час'},
]

CAR_BRANDS = {
    'Acura': ['CL', 'CSX', 'ILX', 'Integra', 'MDX', 'NSX', 'RDX', 'RL', 'RLX', 'RSX', 'TL', 'TLX', 'TSX', 'ZDX'],
    'Alfa Romeo': ['147', '156', '159', '166', 'Brera', 'Giulia', 'Giulietta', 'GT', 'MiTo', 'Spider', 'Stelvio', 'Tonale'],
    'Audi': ['100', '80', 'A1', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'Allroad', 'Q2', 'Q3', 'Q5', 'Q7', 'Q8', 'RS3', 'RS4', 'RS5', 'RS6', 'S3', 'S4', 'S5', 'S6', 'TT'],
    'BMW': ['1 Series', '2 Series', '3 Series', '4 Series', '5 Series', '6 Series', '7 Series', '8 Series', 'i3', 'i4', 'i8', 'iX', 'M2', 'M3', 'M4', 'M5', 'M8', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'Z4'],
    'BYD': ['Atto 3', 'Dolphin', 'F3', 'Han', 'Qin', 'Seal', 'Song', 'Tang', 'Yuan'],
    'Cadillac': ['ATS', 'BLS', 'CT4', 'CT5', 'CT6', 'CTS', 'DeVille', 'Escalade', 'Seville', 'SRX', 'XT4', 'XT5', 'XT6', 'XTS'],
    'Changan': ['Alsvin', 'CS35', 'CS55', 'CS75', 'Eado', 'Raeton', 'UNI-K', 'UNI-T', 'UNI-V'],
    'Chery': ['Amulet', 'Arrizo 5', 'Arrizo 8', 'Bonus', 'Fora', 'IndiS', 'Kimo', 'M11', 'QQ', 'Tiggo 2', 'Tiggo 4', 'Tiggo 7 Pro', 'Tiggo 8 Pro'],
    'Chevrolet': ['Aveo', 'Camaro', 'Captiva', 'Cobalt', 'Cruze', 'Epica', 'Equinox', 'Evanda', 'Impala', 'Lacetti', 'Lanos', 'Malibu', 'Niva', 'Orlando', 'Rezzo', 'Spark', 'Tahoe', 'Tracker', 'TrailBlazer'],
    'Chrysler': ['200', '300C', 'Crossfire', 'Pacifica', 'PT Cruiser', 'Sebring', 'Town & Country', 'Voyager'],
    'Citroen': ['Berlingo', 'C-Crosser', 'C-Elysee', 'C1', 'C2', 'C3', 'C3 Aircross', 'C4', 'C4 Picasso', 'C5', 'C5 Aircross', 'C6', 'DS3', 'DS4', 'DS5', 'Jumper', 'Jumpy', 'SpaceTourer'],
    'Daewoo': ['Espero', 'Gentra', 'Lanos', 'Leganza', 'Matiz', 'Nexia', 'Nubira'],
    'Daihatsu': ['Copen', 'Cuore', 'Materia', 'Mira', 'Move', 'Sirion', 'Terios', 'YRV'],
    'Dodge': ['Avenger', 'Caliber', 'Caravan', 'Challenger', 'Charger', 'Dakota', 'Durango', 'Grand Caravan', 'Journey', 'Nitro', 'RAM', 'Viper'],
    'Exeed': ['LX', 'TXL', 'VX'],
    'FAW': ['Bestune B70', 'Bestune T77', 'V5', 'X40', 'X80'],
    'Fiat': ['500', '500L', 'Albea', 'Brava', 'Bravo', 'Doblo', 'Ducato', 'Freemont', 'Grande Punto', 'Linea', 'Panda', 'Punto', 'Stilo', 'Tipo'],
    'Ford': ['C-Max', 'EcoSport', 'Edge', 'Escape', 'Escort', 'Explorer', 'Fiesta', 'Focus', 'Fusion', 'Galaxy', 'Kuga', 'Mondeo', 'Mustang', 'Ranger', 'S-Max', 'Tourneo', 'Transit'],
    'Geely': ['Atlas', 'Coolray', 'Emgrand', 'Emgrand EC7', 'GS', 'Monjaro', 'Okavango', 'Preface', 'Tugella', 'Vision', 'X7'],
    'Genesis': ['G70', 'G80', 'G90', 'GV70', 'GV80'],
    'GMC': ['Acadia', 'Envoy', 'Savana', 'Sierra', 'Terrain', 'Yukon'],
    'Great Wall': ['Deer', 'Hover H3', 'Hover H5', 'Poer', 'Wingle'],
    'Haval': ['Dargo', 'F7', 'F7x', 'H2', 'H5', 'H6', 'H9', 'Jolion', 'M6'],
    'Honda': ['Accord', 'Airwave', 'City', 'Civic', 'CR-V', 'CR-Z', 'Crosstour', 'Fit', 'HR-V', 'Insight', 'Jazz', 'Legend', 'Odyssey', 'Pilot', 'Prelude', 'Ridgeline', 'Stepwgn', 'Stream'],
    'Hyundai': ['Accent', 'Creta', 'Elantra', 'Galloper', 'Genesis', 'Getz', 'Grand Santa Fe', 'H-1', 'ix35', 'Kona', 'Matrix', 'Palisade', 'Santa Fe', 'Solaris', 'Sonata', 'Starex', 'Terracan', 'Tucson', 'Veloster'],
    'Infiniti': ['EX', 'FX', 'G', 'JX', 'M', 'Q30', 'Q50', 'Q60', 'Q70', 'QX30', 'QX50', 'QX56', 'QX60', 'QX70', 'QX80'],
    'Isuzu': ['D-Max', 'MU-X', 'Rodeo', 'Trooper'],
    'JAC': ['J7', 'JS4', 'JS6', 'S3', 'S5', 'T6'],
    'Jaguar': ['E-Pace', 'F-Pace', 'F-Type', 'S-Type', 'XE', 'XF', 'XJ', 'XK'],
    'Jeep': ['Cherokee', 'Commander', 'Compass', 'Grand Cherokee', 'Liberty', 'Patriot', 'Renegade', 'Wrangler'],
    'Jetour': ['Dashing', 'X70', 'X90'],
    'Kia': ['Carens', 'Carnival', 'Ceed', 'Cerato', 'K5', 'K7', 'Mohave', 'Optima', 'Picanto', 'Rio', 'Seltos', 'Sorento', 'Soul', 'Sportage', 'Stinger'],
    'LADA': ['2101', '2104', '2105', '2106', '2107', '2110', '2111', '2112', '2114', '2115', '4x4', 'Granta', 'Kalina', 'Largus', 'Niva', 'Priora', 'Samara', 'Vesta', 'XRAY'],
    'Land Rover': ['Defender', 'Discovery', 'Discovery Sport', 'Freelander', 'Range Rover', 'Range Rover Evoque', 'Range Rover Sport', 'Range Rover Velar'],
    'Lexus': ['CT', 'ES', 'GS', 'GX', 'HS', 'IS', 'LC', 'LS', 'LX', 'NX', 'RC', 'RX', 'SC', 'UX'],
    'Lifan': ['Breez', 'Cebrium', 'Murman', 'Myway', 'Smily', 'Solano', 'X50', 'X60', 'X70'],
    'Lincoln': ['Aviator', 'Continental', 'Corsair', 'MKC', 'MKS', 'MKT', 'MKX', 'MKZ', 'Navigator'],
    'Mazda': ['2', '3', '5', '6', '626', 'BT-50', 'CX-3', 'CX-30', 'CX-5', 'CX-7', 'CX-9', 'Demio', 'MPV', 'MX-5', 'Premacy', 'Tribute'],
    'Mercedes-Benz': ['A-Class', 'B-Class', 'C-Class', 'CLA', 'CLC', 'CLK', 'CLS', 'E-Class', 'G-Class', 'GLA', 'GLB', 'GLC', 'GLE', 'GLK', 'GLS', 'M-Class', 'S-Class', 'SL', 'Sprinter', 'V-Class', 'Viano'],
    'Mini': ['Clubman', 'Cooper', 'Countryman', 'Coupe', 'Paceman', 'Roadster'],
    'Mitsubishi': ['ASX', 'Carisma', 'Colt', 'Eclipse Cross', 'Galant', 'Grandis', 'L200', 'Lancer', 'Montero', 'Outlander', 'Pajero', 'Pajero Sport', 'Space Star'],
    'Nissan': ['Almera', 'Armada', 'Juke', 'Leaf', 'Murano', 'Navara', 'Note', 'Pathfinder', 'Patrol', 'Primera', 'Qashqai', 'Sentra', 'Teana', 'Terrano', 'Tiida', 'X-Trail'],
    'Omoda': ['C5', 'S5'],
    'Opel': ['Antara', 'Astra', 'Combo', 'Corsa', 'Crossland', 'Frontera', 'Insignia', 'Meriva', 'Mokka', 'Omega', 'Signum', 'Vectra', 'Vivaro', 'Zafira'],
    'Peugeot': ['107', '206', '207', '208', '3008', '301', '307', '308', '4007', '4008', '406', '407', '408', '5008', 'Partner', 'Traveller'],
    'Porsche': ['718 Boxster', '718 Cayman', '911', 'Cayenne', 'Macan', 'Panamera', 'Taycan'],
    'Ravon': ['Gentra', 'Matiz', 'Nexia R3', 'R2', 'R4'],
    'Renault': ['Arkana', 'Captur', 'Clio', 'Duster', 'Fluence', 'Kangoo', 'Kaptur', 'Koleos', 'Laguna', 'Logan', 'Megane', 'Sandero', 'Scenic', 'Symbol', 'Talisman'],
    'SEAT': ['Alhambra', 'Altea', 'Cordoba', 'Ibiza', 'Leon', 'Toledo'],
    'Skoda': ['Fabia', 'Kamiq', 'Karoq', 'Kodiaq', 'Octavia', 'Rapid', 'Roomster', 'Suberb', 'Superb', 'Yeti'],
    'Smart': ['ForFour', 'ForTwo', 'Roadster'],
    'SsangYong': ['Actyon', 'Korando', 'Kyron', 'Musso', 'Rexton', 'Tivoli'],
    'Subaru': ['Forester', 'Impreza', 'Legacy', 'Levorg', 'Outback', 'Tribeca', 'WRX', 'XV'],
    'Suzuki': ['Alto', 'Baleno', 'Grand Vitara', 'Ignis', 'Jimny', 'Liana', 'SX4', 'Swift', 'Vitara', 'Wagon R'],
    'Tesla': ['Model 3', 'Model S', 'Model X', 'Model Y'],
    'Toyota': ['Alphard', 'Auris', 'Avensis', 'Camry', 'Corolla', 'Fortuner', 'Highlander', 'Hilux', 'Land Cruiser', 'Land Cruiser Prado', 'Prius', 'RAV4', 'Vitz', 'Yaris'],
    'Volkswagen': ['Amarok', 'Caddy', 'Caravelle', 'Golf', 'Jetta', 'Multivan', 'Passat', 'Polo', 'Sharan', 'Taos', 'Teramont', 'Tiguan', 'Touareg', 'Transporter'],
    'Volvo': ['C30', 'C40', 'S40', 'S60', 'S80', 'S90', 'V40', 'V60', 'V70', 'V90', 'XC40', 'XC60', 'XC70', 'XC90'],
    'Voyah': ['Dream', 'Free'],
    'Zeekr': ['001', 'X']
}


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='client')
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
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
        print('EMAIL CONFIG ERROR: missing MAIL_* variables or recipient')
        return False

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
        print(f'EMAIL SENT TO: {to_email}')
        return True
    except Exception as e:
        print('Ошибка отправки email:', e)
        return False


def generate_reset_token(email):
    return serializer.dumps(email, salt='password-reset-salt')


def verify_reset_token(token, max_age=3600):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('password2', '').strip()
        consent = request.form.get('policy')

        if not full_name:
            flash('Введите ФИО.')
            return render_template('register.html')

        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        if not username or len(username) < 3:
            flash('Логин должен быть не короче 3 символов.')
            return render_template('register.html')

        if not re.fullmatch(r'[A-Za-zA-Яа-яЁё0-9_.-]+', username):
            flash('Логин содержит недопустимые символы.')
            return render_template('register.html')

        if email and not re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Введите корректный email.')
            return render_template('register.html')

        if phone:
            clean_phone = re.sub(r'\D', '', phone)
            if clean_phone.startswith('8'):
                clean_phone = '7' + clean_phone[1:]
            if clean_phone.startswith('7') and len(clean_phone) == 11:
                phone = '+' + clean_phone
            if not re.fullmatch(r'\+7[0-9]{10}', phone):
                flash('Введите телефон в формате +79991234567.')
                return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен быть не короче 6 символов.')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают.')
            return render_template('register.html')

        if not consent:
            flash('Нужно подтвердить согласие на обработку персональных данных.')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует.')
            return render_template('register.html')

        if email and User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.')
            return render_template('register.html')

        if phone and User.query.filter_by(phone=phone).first():
            flash('Пользователь с таким телефоном уже существует.')
            return render_template('register.html')

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email if email else None,
            phone=phone if phone else None,
            username=username,
            password=generate_password_hash(password),
            role='client',
            consent_accepted=True,
            consent_at=db.func.now()
        )
        db.session.add(user)
        db.session.commit()

        if email:
            send_email(
                email,
                'Регистрация в AutoKey',
                f'''
                <h2>Здравствуйте, {first_name} {last_name}!</h2>
                <p>Вы успешно зарегистрировались на сайте AutoKey.</p>
                <p><b>Логин:</b> {username}</p>
                <p><b>Телефон:</b> {phone if phone else 'не указан'}</p>
                <p>Теперь вы можете входить в личный кабинет и отслеживать заявки.</p>
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
            session['phone'] = user.phone or ''

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('admin_orders'))
            else:
                return redirect(url_for('my_orders'))

        flash('Неверный логин или пароль.')

    return render_template('login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_reset_token(user.email)
            reset_link = url_for('reset_password', token=token, _external=True)

            send_email(
                user.email,
                'Сброс пароля AutoKey',
                f'''
                <h2>Сброс пароля</h2>
                <p>Вы запросили восстановление пароля.</p>
                <p>Нажмите на ссылку ниже:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>Ссылка действует 1 час.</p>
                '''
            )

        flash('Если такой email есть в системе, ссылка для сброса уже отправлена.')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)

    if not email:
        flash('Ссылка недействительна или срок её действия истёк.')
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Пользователь не найден.')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if len(password) < 6:
            flash('Пароль должен быть не короче 6 символов.')
            return render_template('reset_password.html', token=token)

        if password != confirm_password:
            flash('Пароли не совпадают.')
            return render_template('reset_password.html', token=token)

        user.password = generate_password_hash(password)
        db.session.commit()

        flash('Пароль успешно обновлён. Теперь войдите.')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


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
            session['phone'] = user.phone or ''

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

        if not re.fullmatch(r'\+7[0-9]{10}', phone):
            flash('Введите номер телефона строго в формате +79991234567')
            return render_template('contact.html', user=current_user, car_brands=CAR_BRANDS)

        valid_models = CAR_BRANDS.get(brand, [])
        if car_model not in valid_models:
            flash('Выберите модель автомобиля только из списка.')
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
        text_review = request.form['text'].strip()
        rating = int(request.form['rating'])

        review = Review(author=author, text=text_review, rating=rating, is_published=True)
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
        if 'phone' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
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
            phone='+79990000001',
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
            phone='+79990000002',
            consent_accepted=True
        )
        db.session.add(manager_user)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)