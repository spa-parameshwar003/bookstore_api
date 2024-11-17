from flask import Flask, request, jsonify
import requests
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import *
import os
from dotenv import load_dotenv
from sqlalchemy import inspect
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookstore.db'  # SQLite for simplicity
app.config['JWT_SECRET_KEY'] = 'books-store-secret-key123123123'  # Secret key for JWT
# Create tables
db.init_app(app)
jwt = JWTManager(app)

def table_exists(table_name):
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

with app.app_context():
    if table_exists('user'):
        print("DB already exist")
    else:
        db.create_all()

@app.route('/google-auth', methods=['POST'])
def google_auth():
    data = request.json
    print("data ", data)
    server_auth_code = data.get('serverAuthCode')
    username = data.get('username')
    email = data.get('email')

    if not server_auth_code:
        return jsonify({"error": "Missing serverAuthCode"}), 400

    # Exchange serverAuthCode for access token
    token_url = "https://oauth2.googleapis.com/token"
    client_id = os.getenv("client_id")
    client_secret = os.getenv("client_secret")
    # redirect_uri = "com.googleusercontent.apps.417085677090-b6ss8at7pk4am0e8ljfge25jd5ja3go4.apps.googleusercontent.com"
    payload = {
        "code": server_auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        # "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=payload)
    token_info = response.json()

    print("token info ", token_info)
    
    

    if "access_token" in token_info:
        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if not user:
            # If user doesn't exist, create a new one
            user = User(email=email, name=username)
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=email)
        return jsonify({"token": access_token}), 200
        # return jsonify({"token": token_info["access_token"]})
    else:
        return jsonify({"error": "Failed to exchange token", "details": token_info}), 400


# Admin - Add Book
@app.route('/admin/book', methods=['POST'])
@jwt_required()
def add_book():
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user).first()
    
    # Check if user is an admin
    if not user.is_admin:
        return jsonify({"msg": "Only admins can add books"}), 403

    data = request.get_json()
    title = data.get('title')
    author = data.get('author')
    price = data.get('price')
    semester = data.get('semester')
    description = data.get('description')
    available_stock = data.get('available_stock')

    # Create a new book
    book = Book(title=title, author=author, price=price, semester=semester,
                description=description, available_stock=available_stock)

    db.session.add(book)
    db.session.commit()

    return jsonify({"msg": "Book added successfully"}), 201

# User - Get Books
@app.route('/books', methods=['GET'])
def get_books():
    semester = request.args.get('semester', type=int)
    books = Book.query.filter_by(semester=semester).all() if semester else Book.query.all()

    books_list = [{"title": book.title, "author": book.author, "price": book.price,
                   "semester": book.semester, "available_stock": book.available_stock}
                  for book in books]
    
    return jsonify(books_list), 200

# Admin - Delete Book
@app.route('/admin/book/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user).first()
    
    # Check if user is an admin
    if not user.is_admin:
        return jsonify({"msg": "Only admins can delete books"}), 403

    book = Book.query.get(book_id)
    if not book:
        return jsonify({"msg": "Book not found"}), 404
    
    db.session.delete(book)
    db.session.commit()
    
    return jsonify({"msg": "Book deleted successfully"}), 200

@app.route('/buy', methods=['POST'])
@jwt_required()
def buy_book():
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user).first()

    data = request.get_json()
    book_id = data.get('book_id')
    quantity = data.get('quantity')

    book = Book.query.get(book_id)
    if not book:
        return jsonify({"msg": "Book not found"}), 404
    
    if book.available_stock < quantity:
        return jsonify({"msg": "Not enough stock available"}), 400

    # Decrease the stock of the book
    book.available_stock -= quantity
    db.session.commit()

    return jsonify({"msg": f"Purchased {quantity} copies of {book.title}"}), 200


if __name__ == '__main__':
    app.run(debug=False)
