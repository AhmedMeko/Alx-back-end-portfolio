from flask import Flask, render_template, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import firebase_admin
from firebase_admin import credentials, firestore

# Fire base Config
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)

# Firestore
db = firestore.client()


# Creating The base (Before we Start
app = Flask(__name__)
app.config["SECRET_KEY"] = 'welcom to my own world'

# work with WTF
class FormName(FlaskForm):
    name = StringField('What is your name ?!', validators=[DataRequired()])
    submit = SubmitField('Submit')
# Creating The Frist Route and This is Home :)

@app.route('/')

def index():
    return render_template('home.html')

@app.route('/user/<name>')

def user(name):
    return render_template('user.html',user_name=name)

# Login and sign UP
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/regest')
def regest():
    return render_template('regestr.html')
@app.route('/name', methods=['GET', 'POST'])
def name():
    name = None
    form = FormName()
    if form.validate_on_submit():
        name = form.name.data
        form.name.data = ''
        
        # Store Data in databae
        doc_ref = db.collection('users').document()
        doc_ref.set({
            'name': name
        })
        
        flash("Welcome to my Site. Your name has been saved!")
    return render_template('name.html', name=name, form=form)



# Error handel page
# 404 page
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html')
# 500 intrnal server error
@app.errorhandler(500)
def not_found(e):
    return render_template('505.html')
@app.errorhandler(405)
def not_found(e):
    return render_template('405.html')