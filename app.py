from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
import firebase_admin
from firebase_admin import credentials, firestore, auth
import datetime
import uuid

# Firebase Config
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)

# Firestore
db = firestore.client()

# Flask App Config
app = Flask(__name__)
app.config["SECRET_KEY"] = 'welcome_to_my_world'

# Blog Post Form
class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    submit = SubmitField('Post')

# Name Form Example
class FormName(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')

# Route to Create a Blog Post
@app.route('/create', methods=['GET', 'POST'])
def create_post():
    form = BlogPostForm()

    if form.validate_on_submit():  # التحقق من صحة النموذج
        # استخراج البيانات من النموذج
        title = form.title.data
        content = form.content.data
        author = form.author.data
        date_time = datetime.datetime.now()  # تاريخ ووقت الإنشاء
        slug = title.lower().replace(" ", "-")  # إنشاء slug من العنوان

        # إنشاء معرف فريد للبوست
        post_id = str(uuid.uuid4())

        # تجهيز البيانات للتخزين
        blog_data = {
            'id': post_id,
            'title': title,
            'content': content,
            'author': author,
            'date_time': date_time.isoformat(),  # تحويل التاريخ إلى نص
            'slug': slug
        }

        # حفظ البيانات في Firestore
        db.collection('blog_posts').document(post_id).set(blog_data)

        # عرض رسالة نجاح وإعادة التوجيه إلى صفحة الهوم
        flash('Your post has been created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('create.html', form=form)

# Route to Show All Blog Posts
@app.route('/')
def index():
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
        return redirect(url_for('home'))

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.get_user_by_email(email)
            session['user_id'] = user.uid
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('login.html')

# User Signup
@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = auth.create_user(email=email, password=password)
            user_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'uid': user.uid,
                'created_at': firestore.SERVER_TIMESTAMP,
            }
            db.collection('users').document(user.uid).set(user_data)
            flash('User registered successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    # تأكد من الإشارة إلى اسم الملف الصحيح هنا
    return render_template('sign_up.html')
# Admin Route to View All Users
@app.route('/admin')
def accounts():
    users_ref = db.collection('users')
    users = [user.to_dict() for user in users_ref.stream()]
    return render_template('admin.html', users=users)

# Name Example Route
@app.route('/name', methods=['GET', 'POST'])
def name():
    name = None
    form = FormName()
    if form.validate_on_submit():
        name = form.name.data
        db.collection('users').document().set({'name': name})
        flash('Your name has been saved!', 'success')
    return render_template('name.html', name=name, form=form)

# Error Handlers
@app.errorhandler(404)
def not_found_404(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def not_found_500(e):
    return render_template('500.html'), 500

@app.errorhandler(405)
def not_found_405(e):
    return render_template('405.html'), 405

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
