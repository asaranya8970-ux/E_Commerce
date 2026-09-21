import os
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
app.permanent_session_lifetime = timedelta(days=7)
CORS(app, supports_credentials=True)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'ecommerce_db'),
}


def get_db(with_database=True):
    config = DB_CONFIG.copy()
    if not with_database:
        config.pop('database')
    return mysql.connector.connect(**config)


def query(sql, params=(), fetch=False, many=False, commit=False):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        if commit:
            conn.commit()
        return rows, cur.lastrowid
    finally:
        cur.close(); conn.close()


def init_db():
    conn = get_db(with_database=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
    cur.close(); conn.close()
    conn = get_db(); cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(150) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        description TEXT,
        price DECIMAL(10,2) NOT NULL,
        image_url VARCHAR(500),
        category VARCHAR(80) DEFAULT 'General',
        stock INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        total DECIMAL(10,2) NOT NULL,
        status ENUM('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED') DEFAULT 'PLACED',
        shipping_address VARCHAR(500) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
    )''')
    cur.execute('SELECT COUNT(*) FROM products')
    if cur.fetchone()[0] == 0:
        products = [
            ('Wireless Headphones','Bluetooth over-ear headphones with clear sound.',59.99,'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80','Electronics',25),
            ('Smart Watch','Fitness tracking, notifications and heart-rate monitoring.',89.99,'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80','Wearables',18),
            ('Running Shoes','Lightweight everyday running shoes with cushioned sole.',74.50,'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80','Fashion',30),
            ('Backpack','Water-resistant laptop backpack for college and work.',44.99,'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=800&q=80','Bags',22),
            ('Coffee Maker','Compact drip coffee maker for home and office.',69.00,'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80','Home',12),
            ('Desk Lamp','LED study lamp with adjustable brightness.',29.99,'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80','Home',40),
        ]
        cur.executemany('INSERT INTO products(name,description,price,image_url,category,stock) VALUES (%s,%s,%s,%s,%s,%s)', products)
    cur.execute("SELECT id FROM users WHERE email='admin@shop.com'")
    if not cur.fetchone():
        cur.execute('INSERT INTO users(name,email,password_hash,role) VALUES (%s,%s,%s,%s)', ('Admin','admin@shop.com',generate_password_hash('admin123'),'ADMIN'))
    conn.commit(); cur.close(); conn.close()


def current_user():
    uid = session.get('user_id')
    if not uid: return None
    rows, _ = query('SELECT id,name,email,role FROM users WHERE id=%s', (uid,), True)
    return rows[0] if rows else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return jsonify({'success':False,'message':'Login required'}),401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u=current_user()
        if not u: return jsonify({'success':False,'message':'Login required'}),401
        if u['role']!='ADMIN': return jsonify({'success':False,'message':'Admin access required'}),403
        return fn(*args, **kwargs)
    return wrapper


@app.route('/')
def index(): return render_template('index.html')

@app.get('/api/auth/me')
def me(): return jsonify({'success':True,'user':current_user()})

@app.post('/api/auth/register')
def register():
    d=request.get_json() or {}; name=d.get('name','').strip(); email=d.get('email','').strip().lower(); password=d.get('password','')
    if not name or not email or len(password)<6: return jsonify({'success':False,'message':'Name, email and password (6+ characters) are required'}),400
    try:
        _, uid=query('INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)',(name,email,generate_password_hash(password)),commit=True)
        session.permanent=True; session['user_id']=uid
        return jsonify({'success':True,'user':current_user()})
    except Error as e:
        if getattr(e,'errno',None)==1062: return jsonify({'success':False,'message':'Email already registered'}),409
        return jsonify({'success':False,'message':'Registration failed'}),500

@app.post('/api/auth/login')
def login():
    d=request.get_json() or {}; email=d.get('email','').strip().lower(); password=d.get('password','')
    rows,_=query('SELECT * FROM users WHERE email=%s',(email,),True)
    if not rows or not check_password_hash(rows[0]['password_hash'],password): return jsonify({'success':False,'message':'Invalid email or password'}),401
    session.permanent=True; session['user_id']=rows[0]['id']; return jsonify({'success':True,'user':current_user()})

@app.post('/api/auth/logout')
def logout(): session.clear(); return jsonify({'success':True})

@app.get('/api/products')
def products():
    rows,_=query('SELECT * FROM products ORDER BY id DESC',fetch=True)
    return jsonify({'success':True,'products':rows})

@app.post('/api/products')
@admin_required
def add_product():
    d=request.get_json() or {}
    required=['name','description','price','image_url','category','stock']
    if any(d.get(k) in (None,'') for k in required): return jsonify({'success':False,'message':'All product fields are required'}),400
    _,pid=query('INSERT INTO products(name,description,price,image_url,category,stock) VALUES(%s,%s,%s,%s,%s,%s)',(d['name'],d['description'],float(d['price']),d['image_url'],d['category'],int(d['stock'])),commit=True)
    return jsonify({'success':True,'id':pid}),201

@app.put('/api/products/<int:pid>')
@admin_required
def edit_product(pid):
    d=request.get_json() or {}
    query('UPDATE products SET name=%s,description=%s,price=%s,image_url=%s,category=%s,stock=%s WHERE id=%s',(d['name'],d['description'],float(d['price']),d['image_url'],d['category'],int(d['stock']),pid),commit=True)
    return jsonify({'success':True})

@app.delete('/api/products/<int:pid>')
@admin_required
def delete_product(pid):
    try:
        query('DELETE FROM products WHERE id=%s',(pid,),commit=True); return jsonify({'success':True})
    except Error: return jsonify({'success':False,'message':'Product cannot be deleted because it is used in an order'}),409

@app.post('/api/orders')
@login_required
def create_order():
    u=current_user(); d=request.get_json() or {}; items=d.get('items',[]); address=d.get('shipping_address','').strip()
    if not items or not address: return jsonify({'success':False,'message':'Cart and shipping address are required'}),400
    conn=get_db(); cur=conn.cursor(dictionary=True)
    try:
        total=0; clean=[]
        for item in items:
            cur.execute('SELECT id,name,price,stock FROM products WHERE id=%s FOR UPDATE',(int(item['product_id']),)); p=cur.fetchone()
            qty=int(item['quantity'])
            if not p or qty<1 or p['stock']<qty: raise ValueError(f"Insufficient stock for {p['name'] if p else 'product'}")
            total += float(p['price'])*qty; clean.append((p,qty))
        cur.execute('INSERT INTO orders(user_id,total,status,shipping_address) VALUES(%s,%s,%s,%s)',(u['id'],total,'PLACED',address)); oid=cur.lastrowid
        for p,qty in clean:
            cur.execute('INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(%s,%s,%s,%s)',(oid,p['id'],qty,p['price']))
            cur.execute('UPDATE products SET stock=stock-%s WHERE id=%s',(qty,p['id']))
        conn.commit(); return jsonify({'success':True,'order_id':oid,'total':round(total,2)})
    except ValueError as e: conn.rollback(); return jsonify({'success':False,'message':str(e)}),400
    except Error: conn.rollback(); return jsonify({'success':False,'message':'Could not place order'}),500
    finally: cur.close(); conn.close()

@app.get('/api/orders')
@login_required
def my_orders():
    u=current_user(); orders,_=query('SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC',(u['id'],),True)
    for o in orders:
        items,_=query('SELECT oi.*,p.name,p.image_url FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=%s',(o['id'],),True); o['items']=items
    return jsonify({'success':True,'orders':orders})

@app.get('/api/admin/orders')
@admin_required
def all_orders():
    orders,_=query('SELECT o.*,u.name AS user_name,u.email FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC',fetch=True)
    return jsonify({'success':True,'orders':orders})

@app.put('/api/admin/orders/<int:oid>')
@admin_required
def update_order(oid):
    status=(request.get_json() or {}).get('status','')
    allowed={'PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED'}
    if status not in allowed: return jsonify({'success':False,'message':'Invalid status'}),400
    query('UPDATE orders SET status=%s WHERE id=%s',(status,oid),commit=True); return jsonify({'success':True})

@app.get('/api/admin/stats')
@admin_required
def stats():
    a,_=query('SELECT COUNT(*) c FROM products',fetch=True); b,_=query('SELECT COUNT(*) c FROM users WHERE role="USER"',fetch=True); c,_=query('SELECT COUNT(*) c FROM orders',fetch=True); d,_=query('SELECT COALESCE(SUM(total),0) total FROM orders WHERE status<>"CANCELLED"',fetch=True)
    return jsonify({'success':True,'stats':{'products':a[0]['c'],'users':b[0]['c'],'orders':c[0]['c'],'revenue':float(d[0]['total'])}})

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'): return jsonify({'success':False,'message':'API route not found'}),404
    return render_template('index.html')

if __name__=='__main__':
    try: init_db()
    except Exception as e: print('Database setup error:',e)
    app.run(debug=True, host='127.0.0.1', port=5000)
