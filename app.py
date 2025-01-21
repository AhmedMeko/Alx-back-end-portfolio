from flask import Flask, render_template

# Creating The base (Before we Start
app = Flask(__name__)

# Creating The Frist Route and This is Home :)

@app.route('/')

def index():
    return render_template('home.html')

# Login and sign UP
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/regest')
def regest():
    return render_template('regest.html')



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