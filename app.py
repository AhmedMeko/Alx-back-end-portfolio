from flask import Flask, render_template

# Creating The base (Before we Start
app = Flask(__name__)

# Creating The Frist Route and This is Home :)

@app.route('/')

def index():
    return render_template("home.html")




# Error handel page
# 404 page
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html')