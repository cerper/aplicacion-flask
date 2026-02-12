import os
from flask import Flask, jsonify, render_template, request,redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_required, current_user,login_user,logout_user
from datetime import datetime
from sqlalchemy_utils import database_exists, create_database


app = Flask(__name__)
app.secret_key = "0"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:0@localhost:3306/tienda_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# File upload configuration
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif',"jfif"}
# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Nombre de la función de tu ruta de login

@login_manager.user_loader
def load_user(user_id,):
    return Usuario.query.get(int(user_id))


@app.context_processor
def inject_current_year():
    return { 'current_year': datetime.utcnow().year }
  
# --- MODELOS DE LA BASE DE DATOS ---

class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedidos.id', ondelete='CASCADE'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id',ondelete='CASCADE'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False) # Precio al momento de la compra
    producto=db.relationship('Producto', backref='detalles_pedidos', lazy=True)
    
class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_pedido = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(50), nullable=False, default='pendiente')
   
    # Relación para acceder a los productos desde el pedido
    items = db.relationship('DetallePedido', backref='pedidos', lazy=True, cascade="all, delete-orphan")
    usuario = db.relationship('Usuario', backref=db.backref('pedidos', lazy=True))

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contraseña = db.Column(db.String(120), nullable=False)
    productos = db.relationship('Producto', backref='propietario', lazy=True)
   

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    imagen_url = db.Column(db.String(255), nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

# --- RUTAS DE LA APLICACIÓN (CRUD) ---

def allowed_file(filename):
    """Return True if filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# RUTA:  (Página principal)
@app.route('/',methods=['GET'])
def index():
    # Pasamos las tareas a la plantilla HTML
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)



# RUTA: LOGIN (Iniciar sesión de usuario)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        contraseña = request.form.get("contraseña")
        usuario = Usuario.query.filter_by(email=email, contraseña=contraseña).first()
        if usuario:
            login_user(usuario)
            flash(f'¡Bienvenido! Has {usuario.nombre} iniciado sesión exitosamente.', 'success')
            return redirect(url_for('index'))
        else:
            return "Credenciales inválidas", 401
    return render_template("login.html")

# RUTA: LOGOUT (Cerrar sesión de usuario)
@app.route('/logout',)
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('index'))

# RUTA: REGISTER (Registrar nuevo usuario)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        contraseña = request.form.get('contraseña')
        nuevo_usuario = Usuario(nombre=nombre, email=email, contraseña=contraseña)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# RUTA: CREATE (Añadir nuevo producto)
@app.route('/add', methods=["GET",'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        producto = request.form.get('producto')
        cantidad = int(request.form.get('cantidad'))
        precio = float(request.form.get('precio'))
        uploaded_file = request.files.get('imagen') 
        print(f"Archivos recibidos: {request.files}")
        usuario_actual = current_user.id
        # Guardar el archivo en el sistema de archivos y obtener la URL
        if uploaded_file and allowed_file(uploaded_file.filename):
            print(f"Nombre del archivo: {uploaded_file.filename}") 
            filename = secure_filename(uploaded_file.filename) 
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagen_url = url_for('static', filename=f'uploads/{filename}')
        else:
            imagen_url = None 
        db.session.add(Producto(
            nombre=producto, 
            cantidad=cantidad, 
            precio=precio, 
            imagen_url=imagen_url,
            id_usuario=usuario_actual  
        ))
        db.session.commit()
        return redirect(url_for('index'))
      
    else:
        return render_template('register_product.html')

# RUTA: DELETE (Eliminar producto)
@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_product(id):
    producto = Producto.query.get_or_404(id)
    if producto.id_usuario != current_user.id:
        flash("Producto no encontrado o no autorizado.", "failure")
        return redirect(url_for('index'))
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for('index'))

# RUTA: UPDATE (Modificar producto)
@app.route("/modificar/<int:id>", methods=["POST","GET"])
@login_required
def modificar_producto(id):
    producto=Producto.query.get_or_404(id)
    if producto.id_usuario != current_user.id:
        flash("No tienes permiso para editar este producto.", "danger")
        return redirect(url_for('index'))
    if request.method=="POST":
        producto.nombre=request.form.get("nombre")
        producto.cantidad=int(request.form.get("cantidad"))
        producto.precio=float(request.form.get("precio"))
        uploaded_file = request.files.get('imagen')
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagen_url = url_for('static', filename=f'uploads/{filename}')
            producto.imagen_url=imagen_url
        
        db.session.commit()
        flash("Producto actualizado con éxito.", "success")
        return redirect(url_for('index'))
        
    else:
        return render_template("modificar.html", producto=producto)
    
#ruta para buscar productos por nombre
@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "POST":
        query = request.form.get("busqueda","")
        results = Producto.query.filter(Producto.nombre.contains(query)).all()
        return render_template("search.html", results=results)
    else:
        return render_template("search.html", results=[])
    
#ruta para buscar ordenes por id_usuario
@app.route("/orders", methods=["GET"])
@login_required
def search_order():
    
    orders = Pedido.query.filter_by(id_usuario=current_user.id).all()
    return render_template("ordenes.html", orders=orders)
    
#ruta para agregar un nuevo pedido
@app.route("/add_pedido", methods=["GET","POST"])
@login_required
def add_pedido():
    producto_id = request.form.get('producto_id')
    if not producto_id:
        flash("No se seleccionó ningún producto.", "danger")
        return redirect(url_for('index'))

    producto = Producto.query.get_or_404(producto_id)
    if request.method == "POST":
        nuevo_pedido=Pedido(
            id_usuario= current_user.id,
            fecha_pedido=datetime.utcnow(),
            estado="pendiente",
        )

        detalle = DetallePedido(
            id_producto=producto.id,
            cantidad=1,
            precio_unitario=producto.precio
        )

        nuevo_pedido.items.append(detalle)

        db.session.add(nuevo_pedido)
        db.session.commit()
        
        flash(f"Pedido de {producto.nombre} realizado con éxito.", "success")
        return redirect(url_for("search_order"))


@app.route('/add_order', methods=['GET','POST'])
@login_required
def agregando_orden():
    # GET: Mostrar productos para agregar a la orden indicada
    if request.method == 'GET':
        order_id = request.args.get('order_id')
        if not order_id:
            flash('Orden no especificada.', 'danger')
            return redirect(url_for('search_order'))
        pedido = Pedido.query.get_or_404(order_id)
        if pedido.id_usuario != current_user.id:
            flash('No autorizado para editar esta orden.', 'danger')
            return redirect(url_for('index'))
        productos = Producto.query.all()
        return render_template('add_order.html', pedido=pedido, productos=productos)
    # POST: Añadir el producto seleccionado a la orden
    order_id = request.form.get('order_id')
    product_id = request.form.get('product_id')
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except (TypeError, ValueError):
        cantidad = 1

    if not order_id or not product_id:
        flash('Faltan datos para agregar el producto.', 'danger')
        return redirect(url_for('index'))

    pedido = Pedido.query.get_or_404(order_id)
    if pedido.id_usuario != current_user.id:
        flash('No autorizado para editar esta orden.', 'danger')
        return redirect(url_for('index'))

    producto = Producto.query.get_or_404(product_id)
    detalle = DetallePedido(
        id_producto=producto.id,
        cantidad=cantidad,
        precio_unitario=producto.precio
    )
    pedido.items.append(detalle)
    db.session.add(pedido)
    db.session.commit()
    flash(f'Producto {producto.nombre} agregado a la orden #{pedido.id}.', 'success')
    return redirect(url_for('search_order'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    pedido = Pedido.query.get_or_404(id)
    # Sólo permitir que el propietario elimine su pedido
    if pedido.id_usuario != current_user.id:
        flash('No autorizado para eliminar esta orden.', 'danger')
        return redirect(url_for('ordenes'))
    try:
        db.session.delete(pedido)
        db.session.commit()
        flash('Orden eliminada con éxito.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la orden: {e}', 'danger')
    return redirect(url_for('index'))

        


if __name__ == '__main__':
    # Ejecutamos la aplicación
    if not database_exists(app.config['SQLALCHEMY_DATABASE_URI']):
        create_database(app.config['SQLALCHEMY_DATABASE_URI'])
        print("Base de datos creada.")
    
    with app.app_context():
        db.create_all() # Crea las tablas si no existen
        
    
    
    app.run(debug=True)