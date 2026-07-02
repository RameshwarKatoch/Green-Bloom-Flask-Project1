from flask import Flask, render_template, redirect, url_for, flash, request 
from flask_sqlalchemy import SQLAlchemy
import datetime 
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user 
import os
import razorpay # Make sure to run: pip install razorpay

from dotenv import load_dotenv
from groq import Groq
load_dotenv()
# --- 1. Initialize App --- 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'thisisasecretkey') 

# --- 2. Database Configuration ---
db_user = 'root'
db_password = ''
db_name = 'green_bloom'
db_host = '127.0.0.1'
db_port = '3307' 
local_db_uri = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', local_db_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 3. Initialize Libraries ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 4. RAZORPAY CONFIGURATION (Moved to Top) ---
# Replace these with your actual keys from Razorpay Dashboard
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID') 
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 5. Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False) 
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=10)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False, default='Cash on Delivery')
    
    # Payment Tracking Columns
    status = db.Column(db.String(20), nullable=False, default='Pending') 
    payment_id = db.Column(db.String(100), nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_item = db.Column(db.Numeric(10, 2), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')


# --- Admin Panel Setup ---
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from markupsafe import Markup

class SecureModelView(ModelView):
    # Professional admin settings
    page_size = 50
    can_export = True
    can_view_details = True
    create_modal = True
    edit_modal = True
    details_modal = True

    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == 'admin'
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class UserModelView(SecureModelView):
    column_list = ('id', 'username')
    column_searchable_list = ('username',)
    column_default_sort = ('id', True)
    column_labels = {'id': 'User ID', 'username': 'Username'}

class ProductModelView(SecureModelView):
    column_list = ('id', 'image_url', 'name', 'category', 'price', 'quantity')
    column_searchable_list = ('name', 'category', 'description')
    column_filters = ('category', 'price', 'quantity')
    column_editable_list = ('price', 'category', 'quantity')
    column_labels = {'id': 'Product ID', 'name': 'Product Name', 'image_url': 'Image', 'category': 'Category', 'price': 'Price (₹)', 'quantity': 'Stock Quantity'}
    
    def _list_thumbnail(view, context, model, name):
        if not model.image_url:
            return ''
        return Markup(f'<img src="{model.image_url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">')
    
    def _format_price(view, context, model, name):
        return f"₹{model.price}"
        
    column_formatters = {
        'image_url': _list_thumbnail,
        'price': _format_price
    }

class OrderModelView(SecureModelView):
    column_list = ('id', 'order_date', 'full_name', 'phone', 'total_price', 'status', 'payment_method')
    column_searchable_list = ('full_name', 'phone', 'city', 'payment_id')
    column_filters = ('status', 'payment_method', 'order_date', 'city')
    column_editable_list = ('status',)
    column_labels = {
        'id': 'Order ID', 'order_date': 'Date', 'full_name': 'Customer Name',
        'phone': 'Phone', 'total_price': 'Total Amount', 'status': 'Status', 'payment_method': 'Payment'
    }
    
    def _format_price(view, context, model, name):
        return f"₹{model.total_price}"
        
    def _format_status(view, context, model, name):
        if model.status == 'Pending':
            return Markup(f'<span class="status-badge status-warning">{model.status}</span>')
        elif model.status in ['Confirmed', 'Paid']:
            return Markup(f'<span class="status-badge status-success">{model.status}</span>')
        return Markup(f'<span class="status-badge status-secondary">{model.status}</span>')
        
    column_formatters = {
        'total_price': _format_price,
        'status': _format_status
    }
    column_default_sort = ('order_date', True)

class OrderItemModelView(SecureModelView):
    column_list = ('id', 'order', 'product', 'quantity', 'price_per_item')
    column_labels = {'id': 'Item ID', 'order': 'Order', 'product': 'Product', 'quantity': 'Qty', 'price_per_item': 'Price'}
    
    def _format_price(view, context, model, name):
        return f"₹{model.price_per_item}"
        
    column_formatters = {
        'price_per_item': _format_price
    }

class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not self.is_accessible():
            return self.inaccessible_callback('')
        
        # Calculate stats for the dashboard
        total_users = User.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(db.func.sum(Order.total_price)).scalar() or 0
        total_products = Product.query.count()
        
        recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()

        return self.render('admin/custom_index.html', 
                           total_users=total_users, 
                           total_orders=total_orders, 
                           total_revenue=total_revenue,
                           total_products=total_products,
                           recent_orders=recent_orders)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == 'admin'
    def inaccessible_callback(self, name, **kwargs):
        flash("You do not have permission to view the admin page.", "danger")
        return redirect(url_for('login'))

admin = Admin(app, name='Green Bloom Admin', index_view=SecureAdminIndexView())
admin.add_link(MenuLink(name='Back to Site', category='', url='/'))
admin.add_link(MenuLink(name='Logout', category='', url='/logout'))

admin.add_view(UserModelView(User, db.session, name="Users", endpoint="user_admin"))
admin.add_view(ProductModelView(Product, db.session, name="Products", endpoint="product_admin"))
admin.add_view(OrderModelView(Order, db.session, name="Orders", endpoint="order_admin"))
admin.add_view(OrderItemModelView(OrderItem, db.session, name="Order Items", endpoint="orderitem_admin"))


# --- 6. Forms ---
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=80)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=80)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

# --- 7. Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/shop/indoor')
def indoor_plants():
    all_indoor_products = Product.query.filter_by(category='indoor').all()
    return render_template('indoor-plants.html', products=all_indoor_products)

@app.route('/shop/outdoor')
def outdoor_plants():
    all_outdoor_products = Product.query.filter_by(category='outdoor').all()
    return render_template('outdoor-plants.html', products=all_outdoor_products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product-detail.html', product=product)

@app.route('/search')
def search():
    query = request.args.get('query')
    if not query:
        return render_template('search-results.html', products=[], query="")
    search_term = f"%{query}%"
    results = Product.query.filter(
        Product.name.ilike(search_term) | 
        Product.description.ilike(search_term)
    ).all()
    return render_template('search-results.html', products=results, query=query)

@app.route('/autocomplete')
def autocomplete():
    query = request.args.get('q', '').strip()
    if not query:
        return {"suggestions": []}
    
    search_term = f"%{query}%"
    results = Product.query.filter(Product.name.ilike(search_term)).limit(5).all()
    suggestions = [{"name": p.name, "id": p.id} for p in results]
    return {"suggestions": suggestions}

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit(): 
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user) 
            return redirect(url_for('home')) 
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login')) 
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required 
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- Cart Routes ---
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        new_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(new_item)
    db.session.commit()
    
    # If called from chatbot (AJAX), return JSON instead of redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=current_user.id).scalar() or 0
        return {"success": True, "message": f"{product.name} added to cart!", "cart_count": int(cart_count)}
    
    flash(f'{product.name} has been added to your cart!', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = 0
    if cart_items:
        total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item_to_remove = CartItem.query.get_or_404(item_id)
    if item_to_remove.user_id != current_user.id:
        flash('This is not your item!', 'danger')
        return redirect(url_for('cart'))
    db.session.delete(item_to_remove)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/decrease_quantity/<int:item_id>', methods=['POST'])
@login_required
def decrease_quantity(item_id):
    item_to_decrease = CartItem.query.get_or_404(item_id)
    if item_to_decrease.user_id != current_user.id:
        return redirect(url_for('cart'))
    if item_to_decrease.quantity > 1:
        item_to_decrease.quantity -= 1
    else:
        db.session.delete(item_to_decrease)
    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/increase_quantity/<int:item_id>', methods=['POST'])
@login_required
def increase_quantity(item_id):
    item_to_increase = CartItem.query.get_or_404(item_id)
    if item_to_increase.user_id != current_user.id:
        return redirect(url_for('cart'))
    item_to_increase.quantity += 1
    db.session.commit()
    return redirect(url_for('cart'))

# --- Checkout & Payment Routes ---
@app.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "danger")
        return redirect(url_for('cart'))
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "danger")
        return redirect(url_for('cart'))

    # 1. Get Form Data
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    city = request.form.get('city')
    state = request.form.get('state')
    zip_code = request.form.get('zip_code')
    payment_method = request.form.get('payment_method')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    # 2. Create Order in DB (Status = Pending)
    new_order = Order(
        total_price=total_price, 
        user_id=current_user.id,
        full_name=full_name, phone=phone, address=address, city=city, state=state, zip_code=zip_code,
        payment_method=payment_method,
        status='Pending'
    )
    db.session.add(new_order)
    db.session.commit() 

    # 3. Move items to OrderItems
    for item in cart_items:
        order_item = OrderItem(
            quantity=item.quantity, price_per_item=item.product.price,
            order_id=new_order.id, product_id=item.product_id
        )
        db.session.add(order_item)
        db.session.delete(item)
    db.session.commit()
    
    # --- PAYMENT LOGIC ---
    if payment_method == 'COD':
        new_order.status = 'Confirmed'
        db.session.commit()
        return redirect(url_for('order_complete', order_id=new_order.id))
    
    else:
        # Online Payment Logic
        amount_in_paisa = int(total_price * 100)
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paisa,
            "currency": "INR",
            "receipt": str(new_order.id),
            "payment_capture": "1"
        })
        
        return render_template('pay.html', 
                               order=new_order, 
                               razorpay_order_id=razorpay_order['id'],
                               razorpay_key_id=RAZORPAY_KEY_ID,
                               amount=amount_in_paisa)

@app.route('/payment_success', methods=['POST'])
@login_required
def payment_success():
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        order = Order.query.filter_by(user_id=current_user.id, status='Pending').order_by(Order.id.desc()).first()
        
        if order:
            order.status = 'Paid'
            order.payment_id = razorpay_payment_id
            db.session.commit()
            return redirect(url_for('order_complete', order_id=order.id))
            
    except razorpay.errors.SignatureVerificationError:
        flash("Payment verification failed!", "danger")
        return redirect(url_for('cart'))
        
    return redirect(url_for('home'))

@app.route('/order_complete/<int:order_id>')
@login_required
def order_complete(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("You do not have permission to view this order.", "danger")
        return redirect(url_for('home'))
    return render_template('order_complete.html', order=order)

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        cart_count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=current_user.id).scalar() or 0
    else:
        cart_count = 0
    return dict(cart_count=cart_count)

import re

# --- Chatbot Route (Database-Aware Agent) ---
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        return {"reply": "Sorry, I am currently offline. (Missing Groq API Key)", "products": []}
    
    # Fetch entire inventory to give the AI context
    all_products = Product.query.all()
    
    inventory_context = "\n\nOUR INVENTORY:\n"
    for p in all_products:
        inventory_context += f"ID: {p.id} | Name: {p.name} | Price: ₹{p.price} | Category: {p.category} | In Stock: {p.quantity}\n"

    system_prompt = (
        "You are an expert plant advisor for 'Green Bloom', an online shop selling indoor and outdoor plants, and flower bouquets. "
        "The shop offers same-day delivery, Cash on Delivery, and online payments via Razorpay. "
        "Below is our CURRENT INVENTORY. Use ONLY these products to make personalized recommendations based on the user's needs. "
        "CRITICAL INSTRUCTION: Whenever you recommend a specific plant from the list, you MUST include its ID wrapped in brackets like this: [PROD:id]. "
        "For example, if you recommend Monstera Deliciosa (ID: 4), you must write: 'I recommend the Monstera Deliciosa [PROD:4].' "
        "You can recommend multiple plants by including multiple tags. Keep your tone polite and concise (2-3 sentences max)."
        f"{inventory_context}"
    )

    try:
        client = Groq(api_key=groq_api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.1-8b-instant",
            max_tokens=250,
        )
        reply = chat_completion.choices[0].message.content
        
        # Parse output for [PROD:id] tags
        extracted_ids = re.findall(r'\[PROD:\s*(\d+)\]', reply, flags=re.IGNORECASE)
        unique_ids = list(dict.fromkeys(extracted_ids)) # deduplicate
        
        product_data = []
        for pid in unique_ids:
            try:
                p = Product.query.get(int(pid))
                if p:
                    product_data.append({
                        "id": p.id,
                        "name": p.name,
                        "price": float(p.price),
                        "image_url": p.image_url or "",
                        "category": p.category or "General",
                        "quantity": p.quantity
                    })
            except Exception:
                pass
                
        # Clean the tags from the user-facing text
        clean_reply = re.sub(r'\[PROD:\s*\d+\]', '', reply, flags=re.IGNORECASE).strip()
        
        return {"reply": clean_reply, "products": product_data}
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return {"reply": "I'm having a little trouble connecting right now. Please try again!", "products": []}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)