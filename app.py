# Import necessary modules from SQLAlchemy:
import datetime
from typing import List

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric, create_engine, Integer, String, ForeignKey, Boolean, func, select
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Create a Flask app and configure the database
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:hdr13@localhost/ecommerce_api"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Create a Flask-SQLAlchemy db instance
db = SQLAlchemy(app)

# Define a declarative base
class Base(DeclarativeBase):
    pass

# DATABASE MODELS
# User Table
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    
    # Relationship to Orders
    orders: Mapped[List["Order"]] = relationship(back_populates="user")

# Order Table
class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_date: Mapped[datetime.datetime] = mapped_column(func.now())
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    # Relationship to User
    user: Mapped['User'] = relationship(back_populates="orders")
    
    # Relationship to Products
    products: Mapped[List["Product"]] = relationship(secondary='order_products', back_populates="orders")
      
# Product Table
class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Relationship to Orders
    orders: Mapped[List["Order"]] = relationship(back_populates="products")
    
# Order_Product Association Table
class Order_Product(Base):
    __tablename__ = 'order_products'
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), primary_key=True)
    
# MARSHMALLOW SCHEMAS
# Import necessary modules from Marshmallow
from marshmallow import Schema, ValidationError, fields

# User Schema
class users_schema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    address = fields.Str()
    email = fields.Email(required=True)
    orders = fields.Nested('orders_schema', many=True, exclude=('user',))
    
# Order Schema
class orders_schema(Schema):
    id = fields.Int(dump_only=True)
    order_date = fields.DateTime(dump_only=True)
    user_id = fields.Int(required=True)
    products = fields.Nested('products_schema', many=True, exclude=('orders',))
    
# Product Schema
class product_schema(Schema):
    id = fields.Int(dump_only=True)
    product_name = fields.Str(required=True)
    price = fields.Float(required=True)
    orders = fields.Nested('orders_schema', many=True, exclude=('products',))
    
# Creating a runner function
if __name__ == '__main__': # Ensures this block runs only when the script is executed directly
    with app.app_context():  # Create an application context
        Base.metadata.create_all(db.engine)  # Create all tables in the database
        # Base.metadata.drop_all(db.engine)  # Uncomment to drop all tables in the database
    app.run(debug=True)  # Start the Flask development server with debug mode enabled

# IMPLEMENT CRUD ENDPOINTS
# User Endpoints

 # GET /users: Retrieve all users
@app.route('/users', methods=['GET'])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()
    if not users:
        return jsonify({"message": "No users found"}), 400
    
    return users_schema.jsonify(users), 200

# GET /users/<user_id>: Retrieve a specific user by ID
@app.route('/users/<int:user_id>', methods=['GET']) 
def get_user(user_id):
    query = select(User).where(User.id == user_id)
    user = db.session.execute(query).scalar_one_or_none()
    
    if user is None:
        return jsonify({"message": "User not found"}), 400

    return users_schema.jsonify(user), 200

 # POST /users: Create a new user
@app.route('/users', methods=['POST'])
def create_user():
    try:
        user_data = users_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_user = User(name=user_data['name'], address=user_data.get('address'), email=user_data['email'])
    db.session.add(new_user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating user", "error": str(e)}), 500    
    
    return users_schema.jsonify(new_user), 200

# PUT /users/<user_id>: Update an existing user
@app.route('/users/<int:user_id>', methods=['PUT']) 
def update_user(user_id):
    query = select(User).where(User.id == user_id)
    user = db.session.execute(query).scalar_one_or_none()
    if user is None:
        return jsonify({"message": "user not found"}), 400
    
    try:
        user_data = users_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    user.name = user_data['name']
    user.address = user_data.get('address')
    user.email = user_data['email']
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating user", "error": str(e)}), 500
    return users_schema.jsonify(user), 200
    
# DELETE /users/<user_id>: Delete a user
@app.route('/users/<int:id>', methods=['DELETE']) 
def delete_user(id):
    query = select(User).where(User.id == id)
    user = db.session.execute(query).scalar_one_or_none()
    if user is None:
        return jsonify({"message": "User not found"}), 400
    db.session.delete(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting user", "error": str(e)}), 500
    
    return jsonify({"message": "User deleted successfully"}), 200

# Product Endpoints

# GET /products: Retrieve all products
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()
    
    if not products:
        return jsonify({"message": "No products found"}), 400
    
    return product_schema.jsonify(products), 200

# GET /products/<id>: Retrieve a product by ID
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    query = select(Product).where(Product.id == id)
    product = db.session.execute(query).scalar_one_or_none()
    
    if product is None:
        return jsonify({"message": "Product not found"}), 400
    
    return product_schema.jsonify(product), 200

# POST /products: Create a new product
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_product = Product(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating product", "error": str(e)}), 500
    return product_schema.jsonify(new_product), 200
          
# PUT /products/<id>: Update a product by ID
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    query = select(Product).where(Product.id == id)
    product = db.session.execute(query).scalar_one_or_none()
    if product is None:
        return jsonify({"message": "Product not found"}), 400
    
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating product", "error": str(e)}), 500 
    
    return product_schema.jsonify(product), 200

# DELETE /products/<id>: Delete a product by ID
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    query = select(Product).where(Product.id == id)
    product = db.session.execute(query).scalar_one_or_none()
    if product is None:
        return jsonify({"message": "Product not found"}), 400
    db.session.delete(product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting product", "error": str(e)}), 500
    
    return jsonify({"message": "Product deleted successfully"}), 200

# Order Endpoints

# POST /orders: Create a new order (requires user ID and order date)
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        order_data = orders_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_order = Order(user_id=order_data['user_id'], order_date=datetime.datetime.now())
    db.session.add(new_order)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating order", "error": str(e)}), 500
    
    return orders_schema.jsonify(new_order), 200

# PUT /orders/<order_id>/add_product/<product_id>: Add a product to an order (prevent duplicates)
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id, product_id):
   order_query = select(Order).where(Order.id == order_id)
   order = db.session.execute(order_query).scalar_one_or_none()
   
   if order is None:
       return jsonify({"message": "Order not found"}), 400
   
   product_query = select(Product).where(Product.id == product_id)
   product = db.session.execute(product_query).scalar_one_or_none()
   
   if product is None:
       return jsonify({"message": "Product not found"}), 400
   
   new_order_product = Order_Product(order_id=order_id, product_id=product_id)
   db.session.add(new_order_product)
   
   try:
       db.session.commit()
   except IntegrityError:
       db.session.rollback()
       return jsonify({"message": "Product already in order"}), 400
   except Exception as e:
       db.session.rollback()
       return jsonify({"message": "Error adding product to order", "error": str(e)}), 500
   
   return orders_schema.jsonify(order), 200

# DELETE /orders/<order_id>/remove_product/<product_id>: Remove a product from an order
@app.route("/orders/<int:order_id>/remove_product/<int:product_id>", methods=['DELETE'])
def remove_product_from_order(order_id, product_id):
    order_product_query = select(Order_Product).where(
        Order_Product.order_id == order_id,
        Order_Product.product_id == product_id
    )
    
    order_product = db.session.execute(order_product_query).scalar_one_or_none()
    if order_product is None:
        return jsonify({"message": "Product not found in order"}), 400
    
    db.session.delete(order_product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error removing product from order", "error": str(e)}), 500

    return jsonify({"message": "Product removed from order successfully"}), 200

# GET /orders/user/<user_id>: Get all orders for a user
@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    query = select(Order).where(Order.user_id == user_id)
    orders = db.session.execute(query).scalars().all()
    
    if not orders:
        return jsonify({"message": "No orders found for this user"}), 400
    
    return orders_schema.jsonify(orders), 200

# GET /orders/<order_id>/products: Get all products for an order
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_by_order(order_id):
    query = select(Order).where(Order.id == order_id)
    order = db.session.execute(query).scalar_one_or_none()
    if order is None:
        return jsonify({"message": "Order not found"}), 400
    
    products = order.products
    if not products:
        return jsonify({"message": "No products found for this order"}), 400
    
    return product_schema.jsonify(products), 200