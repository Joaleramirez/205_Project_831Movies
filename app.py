from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from pprint import pprint
from dotenv import load_dotenv
#from flask_bootstrap import Bootstrap5
import random

load_dotenv()

app = Flask(__name__)
#bootstrap = Bootstrap5(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'change_this_to_a_random_secret_key'
app.config['SESSION_PERMANENT'] = False  # Sessions expire when the browser closes
db = SQLAlchemy(app)

APIKEY = os.getenv('TMDB_API_KEY')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    poster_path = db.Column(db.String(200), nullable=False)
    overview = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('movies', lazy=True))


@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    # Redirect to login if not logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id  # Store user ID in session
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully, please login.')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.')
    return render_template('register.html')

import requests

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user:
        page = request.args.get('page', 1, type=int)
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={APIKEY}&language=en-US&page={page}"
        response = requests.get(url)

        if response.status_code == 200:
            movies = response.json().get('results', [])
            total_pages = response.json().get('total_pages', 1)
            if not movies:
                flash("No movies found.")
            return render_template('home.html', username=user.username, movies=movies, current_page=page, total_pages=total_pages)
        else:
            flash("Failed to fetch movies from API.")
            return render_template('home.html', username=user.username, movies=[])
    else:
        flash("User not found, please log in again.")
        return redirect(url_for('logout'))
    
@app.route('/add_to_list', methods=['POST'])
def add_to_list():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    
    user_id = session['user_id']
    movie_id = request.form['movie_id']
    title = request.form['title']
    poster_path = request.form['poster_path']
    overview = request.form.get('overview')

    # Check if the movie is already in the user's list
    existing_movie = Movie.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    if existing_movie:
        return jsonify({"success": False, "message": "Movie already in list"}), 400

    new_movie = Movie(user_id=user_id, movie_id=movie_id, title=title, poster_path=poster_path, overview=overview)
    db.session.add(new_movie)
    db.session.commit()

    return jsonify({"success": True, "message": "Movie added to list"}), 200

@app.route('/delete_from_list', methods=['POST'])
def delete_from_list():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    movie_id = request.form['movie_id']
    user_id = session['user_id']
    
    movie = Movie.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    if movie:
        db.session.delete(movie)
        db.session.commit()
        return jsonify({"success": True, "message": "Movie deleted from list"}), 200
    else:
        return jsonify({"success": False, "message": "Movie not found in list"}), 404

import requests
from flask import request, jsonify

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_term = request.form['title']
        api_key = '8c5606f4'
        url = f'http://www.omdbapi.com/?apikey={api_key}&s={search_term}'
        
        response = requests.get(url)
        response.raise_for_status()
        movie_data = response.json()
        if movie_data["Response"] == "True":
            movies = movie_data["Search"]
            return render_template('search.html', movies=movies)
        else:
                return render_template('search.html', movies=None)
    else:
        return render_template('search.html', movies=None)


@app.route('/searchInfo', methods=['GET'])
def search_info():
    return render_template('searchInfo.html', movieData=None)  



@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user:
        return render_template('profile.html', username=user.username)
    else:
        flash("User not found, please log in again.")
        return redirect(url_for('logout'))
    

@app.route('/mylist')
def mylist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user:
        movies = Movie.query.filter_by(user_id=user.id).all()
        return render_template('mylist.html', movies=movies)
    else:
        flash("User not found, please log in again.")
        return redirect(url_for('logout'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Clear session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
