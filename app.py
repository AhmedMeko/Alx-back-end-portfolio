from flask import Flask, render_template, request, flash, redirect, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
import firebase_admin
from firebase_admin import credentials, firestore, auth
import datetime
import uuid

# Firebase Configuration
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)

# Firestore Client
db = firestore.client()

# Flask App Configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = 'welcome_to_my_world'

# Blog Post Form Class
class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    submit = SubmitField('Post')

# Route to Create a Blog Post
@app.route('/create', methods=['GET', 'POST'])
def create_post():
    form = BlogPostForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        user_id = session['user_id']  # Get the user ID from the session
        date_time = datetime.datetime.now()
        slug = title.lower().replace(" ", "-")
        post_id = str(uuid.uuid4())

        # Get the user data from Firestore to fetch the username
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get()

        if user_data.exists:
            username = user_data.to_dict().get('first_name') + ' ' + user_data.to_dict().get('last_name')
        else:
            username = "Unknown"

        blog_data = {
            'id': post_id,
            'title': title,
            'content': content,
            'author': username,  # Store the username here
            'user_id': user_id,  # Store the user ID to reference later
            'date_time': date_time.isoformat(),
            'slug': slug
        }

        # Save the new blog post in Firestore
        db.collection('blog_posts').document(post_id).set(blog_data)
        flash('Your post has been created successfully!', 'success')
        return redirect('/')

    return render_template('create.html', form=form)

# Show Post

# Home Page Route to Show All Blog Posts
@app.route('/')
def home():
    posts_ref = db.collection('blog_posts')
    posts = posts_ref.order_by('date_time', direction=firestore.Query.DESCENDING).stream()

    blog_posts = [post.to_dict() for post in posts]
    return render_template('home.html', blog_posts=blog_posts)

# Route to View a Single Post
@app.route('/post/<slug>')
def view_post(slug):
    post_ref = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
    post_data = next((post.to_dict() for post in post_ref), None)

    if post_data:
        return render_template('view_post.html', post=post_data)
    else:
        flash('Post not found!', 'danger')
        return redirect('/')
# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.get_user_by_email(email)
            session['user_id'] = user.uid
            session['role'] = user.custom_claims.get('role', 'user')  # Default role is 'user'
            flash('Login successful!', 'success')
            return redirect('/')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('login.html')

# User Signup with Role Assignment
@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = auth.create_user(email=email, password=password)
            auth.set_custom_user_claims(user.uid, {'role': 'user'})  # or 'admin'

            user_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'uid': user.uid,
                'created_at': firestore.SERVER_TIMESTAMP,
                'role': 'user',  # Default role
            }
            db.collection('users').document(user.uid).set(user_data)
            flash('User registered successfully!', 'success')
            return redirect('/login')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('sign_up.html')

# User Profile Route
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('You must be logged in to access the profile!', 'danger')
        return redirect('/login')

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get()

    if user_data.exists:
        user_data = user_data.to_dict()
        return render_template('profile.html', user=user_data)
    else:
        flash('User data not found!', 'danger')
        return redirect('/')

# Admin Route to Manage Users (accessible only by admin)
@app.route('/admin')
def accounts():
    if 'role' not in session or session['role'] != 'admin':
        flash('You do not have permission to access this page!', 'danger')
        return redirect('/')

    users_ref = db.collection('users')
    users = [user.to_dict() for user in users_ref.stream()]
    return render_template('admin.html', users=users)

# Error Handlers for Different HTTP Errors
@app.errorhandler(404)
def not_found_404(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def not_found_500(e):
    return render_template('500.html'), 500

# Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)
