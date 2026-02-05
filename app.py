# Import necessary modules from SQLAlchemy:
import datetime
import os
from typing import List

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import Column, Numeric, Integer, String, ForeignKey, Table, func, select, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.exc import IntegrityError

# Create a Flask app and configure the database
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:hdr13@localhost/ecommerce_api",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Creating our Base Model
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy and Marshmallow
db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)

# Use Flask-SQLAlchemy's base class
Base = db.Model

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
    order_date: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    # Relationship to User
    user: Mapped['User'] = relationship(back_populates="orders")
    
    # Relationship to Products
    products: Mapped[List["Product"]] = relationship(secondary='order_product', back_populates="orders")
      
# Product Table
class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Relationship to Orders
    orders: Mapped[List["Order"]] = relationship(secondary='order_product', back_populates="products")

# Order_Product Association Table
class Order_Product(Base):
    __tablename__ = 'order_product'
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), primary_key=True)

# MARSHMALLOW SCHEMAS
# Import necessary modules from Marshmallow
from marshmallow import Schema, ValidationError, fields, validate

# User Schema
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_relationships = True
    
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    address = fields.Str(validate=validate.Length(max=200))
    email = fields.Email(required=True, validate=validate.Length(max=100))

# Order Schema
class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_relationships = True
        include_fk = True
 
    id = fields.Int(dump_only=True)
    order_date = fields.DateTime(dump_only=True)
    user_id = fields.Int(required=True)
    products = fields.Pluck("ProductSchema", "id", many=True, dump_only=True)
       
# Product Schema
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        include_relationships = True

    id = fields.Int(dump_only=True)
    product_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    price = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))

# Initialize Schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# IMPLEMENT CRUD ENDPOINTS
# User Endpoints

 # GET /users: Retrieve all users
@app.route('/users', methods=['GET'])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all() # Returns a list of User objects
    if not users:
        return jsonify({"message": "No users found."}), 404
    
    return users_schema.jsonify(users), 200

# GET /users/<user_id>: Retrieve a specific user by ID
@app.route('/users/<int:user_id>', methods=['GET']) 
def get_user(user_id):
    user = db.session.get(User, user_id) # Returns a User object or None
    
    if user is None:
        return jsonify({"message": "User not found"}), 404

    return user_schema.jsonify(user), 200

 # POST /users: Create a new user

@app.route('/users', methods=['POST'])
def create_user():
    try:
        user_data = user_schema.load(request.json) # Validate and deserialize input & returns a User instance.
    except ValidationError as err:
        return jsonify(err.messages), 422
    
    new_user = User(
        name=user_data['name'],
        address=user_data['address'],
        email=user_data['email']
    )
    
    db.session.add(new_user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating user.", "error": str(e)}), 500    
    
    return user_schema.jsonify(new_user), 201

# PUT /users/<user_id>: Update an existing user
@app.route('/users/<int:user_id>', methods=['PUT']) 
def update_user(user_id):
    user = db.session.get(User, user_id) # Returns a User object or None
    
    if user is None:
        return jsonify({"message": "Invalid user id."}), 404
    
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422
    
    user.name = user_data['name']
    user.address = user_data['address']
    user.email = user_data['email']
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating user.", "error": str(e)}), 500
    
    return user_schema.jsonify(user), 200
    
# DELETE /users/<user_id>: Delete a user
@app.route('/users/<int:user_id>', methods=['DELETE']) 
def delete_user(user_id):
    user = db.session.get(User, user_id) # Returns a User object or None
    
    if user is None:
        return jsonify({"message": "User not found."}), 404
    
    db.session.delete(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting user.", "error": str(e)}), 500
    
    return jsonify({"message": f"User deleted successfully {user_id}."}), 200

# Product Endpoints

# GET /products: Retrieve all products
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all() # Returns a list of Product objects
    
    if not products:
        return jsonify({"message": "No products found."}), 404
    
    return products_schema.jsonify(products), 200

# GET /products/<id>: Retrieve a product by ID
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = db.session.get(Product, id) # Returns a Product object or None
    
    if product is None:
        return jsonify({"message": "Product not found."}), 404
    
    return product_schema.jsonify(product), 200

# POST /products: Create a new product
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422
    
    new_product = Product(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating product.", "error": str(e)}), 500
    return product_schema.jsonify(new_product), 201
          
# PUT /products/<id>: Update a product by ID
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = db.session.get(Product, id) # Returns a Product object or None
    if product is None:
        return jsonify({"message": "Product not found."}), 404
    
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating product.", "error": str(e)}), 500 
    
    return product_schema.jsonify(product), 200

# DELETE /products/<id>: Delete a product by ID
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Product, id) # Returns a Product object or None
    
    if product is None:
        return jsonify({"message": "Product not found."}), 404
    
    db.session.delete(product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting product.", "error": str(e)}), 500
    
    return jsonify({"message": "Product deleted successfully."}), 200

# Order Endpoints

# POST /orders: Create a new order (requires user ID and order date)
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422
    
    try:
        user = db.session.get(User, order_data['user_id']) # Returns a User object or None
        if user is None:
            return jsonify({"message": "User not found."}), 404
    except Exception as e:
        return jsonify({"message": "Error retrieving user.", "error": str(e)}), 500
    
    new_order = Order(user_id=order_data['user_id']) # order_date is auto-set to current timestamp
                                                       # , order_date=order_data['order_date']
    
    db.session.add(new_order)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating order.", "error": str(e)}), 500
    
    return order_schema.jsonify(new_order), 201

# PUT /orders/<order_id>/add_product/<product_id>: Add a product to an order (prevent duplicates)
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id, product_id):
   order = db.session.get(Order, order_id) # Returns an Order object or None
   
   if order is None:
       return jsonify({"message": "Order not found."}), 404
   
   product = db.session.get(Product, product_id) # Returns a Product object or None
   
   if product is None:
       return jsonify({"message": "Product not found."}), 404
   
   new_order_product = Order_Product(order_id=order_id, product_id=product_id)
   
   db.session.add(new_order_product)
   try:
       db.session.commit()
   except IntegrityError:
       db.session.rollback()
       return jsonify({"message": "Product already in order."}), 409
   except Exception as e:
       db.session.rollback()
       return jsonify({"message": "Error adding product to order.", "error": str(e)}), 500
   
   return order_schema.jsonify(order), 201

# DELETE /orders/<order_id>/remove_product/<product_id>: Remove a product from an order
@app.route("/orders/<int:order_id>/remove_product/<int:product_id>", methods=['DELETE'])
def remove_product_from_order(order_id, product_id):
    order_product_query = select(Order_Product).where(
        Order_Product.order_id == order_id,
        Order_Product.product_id == product_id
    )
    
    order_product = db.session.execute(order_product_query).scalar_one_or_none() # Returns an Order_Product object or None
    if order_product is None:
        return jsonify({"message": "Product not found in order."}), 404
    
    db.session.delete(order_product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error removing product from order.", "error": str(e)}), 500

    return jsonify({"message": "Product removed from order successfully."}), 200

# GET /orders/user/<user_id>: Get all orders for a user
@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    orders = db.session.get(User, user_id).orders # Returns a list of Order objects
    
    if not orders:
        return jsonify({"message": "No orders found for this user."}), 404
    
    return orders_schema.jsonify(orders), 200

# GET /orders/<order_id>/products: Get all products for an order
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_by_order(order_id):
    order = db.session.get(Order, order_id) # Returns an Order object or None
    
    if  order is None:
        return jsonify({"message": "Order not found."}), 404
    
    products = order.products # Returns a list of Product objects
    if not products:
        return jsonify({"message": "No products found for this order."}), 404
    
    return products_schema.jsonify(products), 200

# Creating a runner function
if __name__ == '__main__': # Ensures this block runs only when the script is executed directly
    with app.app_context():  # Create an application context
        db.create_all()  # Create all tables in the database
        app.run(debug=True)  # Start the Flask development server with debug mode enabled
        # Base.metadata.drop_all(db.engine)  # Uncomment to drop all tables in the database
