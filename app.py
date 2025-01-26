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

# Function to assign "admin" role to a user
def set_user_to_admin(user_uid):
    try:
        auth.set_custom_user_claims(user_uid, {'role': 'admin'})
        print(f"User {user_uid} has been set as admin.")
    except Exception as e:
        print(f"Error setting user {user_uid} as admin: {str(e)}")

# Set a specific user as admin
user_uid = '9RrhSqtMazZ7W9Ddmm8UA2rJ7Qx1'
set_user_to_admin(user_uid)

# Route to create a blog post
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

        # Get user data from Firestore
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
            'author': username,
            'user_id': user_id,
            'date_time': date_time.isoformat(),
            'slug': slug
        }

        # Save the blog post in Firestore
        db.collection('blog_posts').document(post_id).set(blog_data)
        flash('Your post has been created successfully!', 'success')
        return redirect('/')

    return render_template('create.html', form=form)

# Route to display the home page with all blog posts
@app.route('/')
def home():
    posts_ref = db.collection('blog_posts')
    posts = posts_ref.order_by('date_time', direction=firestore.Query.DESCENDING).stream()

    blog_posts = [post.to_dict() for post in posts]
    return render_template('home.html', blog_posts=blog_posts)

# Route to view a single post
@app.route('/post/<slug>')
def view_post(slug):
    post_ref = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
    post_data = next((post.to_dict() for post in post_ref), None)

    if post_data:
        return render_template('view_post.html', post=post_data)
    else:
        flash('Post not found!', 'danger')
        return redirect('/')

# Route to delete a blog post
@app.route('/delete/<slug>', methods=['GET', 'POST'])
def delete_post(slug):
    post_ref = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
    post_data = next((post.to_dict() for post in post_ref), None)

    if post_data:
        # Check if the user is the author of the post
        if post_data['user_id'] != session['user_id']:
            flash('You are not authorized to delete this post.', 'danger')
            return redirect('/')

        # Delete the post from Firestore
        db.collection('blog_posts').document(post_data['id']).delete()
        flash('Post deleted successfully!', 'success')
        return redirect('/')
    else:
        flash('Post not found!', 'danger')
        return redirect('/')

# Route to edit a blog post
@app.route('/edit/<slug>', methods=['GET', 'POST'])
def edit_post(slug):
    post_ref = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
    post_data = next((post.to_dict() for post in post_ref), None)

    if post_data:
        # Check if the user is the author of the post
        if post_data['user_id'] != session['user_id']:
            flash('You are not authorized to edit this post.', 'danger')
            return redirect('/')

        form = EditPostForm()

        if form.validate_on_submit():
            # Update the post data
            post_ref = db.collection('blog_posts').document(post_data['id'])
            post_ref.update({
                'title': form.title.data,
                'content': form.content.data,
                'date_time': datetime.datetime.now().isoformat(),
            })
            flash('Post updated successfully!', 'success')
            return redirect(f'/post/{post_data["slug"]}')

        form.title.data = post_data['title']
        form.content.data = post_data['content']

        return render_template('edit_post.html', form=form, post=post_data)
    else:
        flash('Post not found!', 'danger')
        return redirect('/')

# Route for user login
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

# Route for user signup with role assignment
@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = auth.create_user(email=email, password=password)
            auth.set_custom_user_claims(user.uid, {'role': 'user'})  # Default role

            user_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'uid': user.uid,
                'created_at': firestore.SERVER_TIMESTAMP,
                'role': 'user',
            }
            db.collection('users').document(user.uid).set(user_data)
            flash('User registered successfully!', 'success')
            return redirect('/login')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('sign_up.html')

# Route for user logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have logged out successfully.', 'success')
    return redirect('/')

# Route for user profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('You must be logged in to access the profile!', 'danger')
        return redirect('/login')

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get()

    if user_data.exists:
        user_data = user_data.to_dict()

        if request.method == 'POST':
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            password = request.form['password']
            
            # Update the user data in Firestore
            user_ref.update({
                'first_name': first_name,
                'last_name': last_name,
                'email': email
            })

            # If password is provided, update it in Firebase Authentication
            if password:
                try:
                    auth.update_user(user_id, password=password)
                    flash('Password updated successfully!', 'success')
                except Exception as e:
                    flash(f'Error updating password: {str(e)}', 'danger')

            flash('Profile updated successfully!', 'success')
            return redirect('/profile')

        return render_template('profile.html', user=user_data)
    else:
        flash('User data not found!', 'danger')
        return redirect('/')
# Route for admin to manage users
@app.route('/admin')
def accounts():
    if 'role' not in session or session['role'] != 'admin':
        flash('You do not have permission to access this page!', 'danger')
        return redirect('/')  # توجيه المستخدم إلى الصفحة الرئيسية إذا لم يكن لديه صلاحيات

    users_ref = db.collection('users')
    users = [user.to_dict() for user in users_ref.stream()]
    return render_template('admin.html', users=users)

# Route to edit user details
@app.route('/edit_user/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
    user_ref = db.collection('users').document(uid)
    user_data = user_ref.get().to_dict()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        age = request.form['age']
        phone = request.form['phone']

        user_ref.update({
            'name': name,
            'email': email,
            'age': age,
            'phone': phone
        })

        flash('User updated successfully!', 'success')
        return redirect('/admin')

    return render_template('edit_user.html', user=user_data)

# Error Handlers
@app.errorhandler(404)
def not_found_404(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def not_found_500(e):
    return render_template('500.html'), 500

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)