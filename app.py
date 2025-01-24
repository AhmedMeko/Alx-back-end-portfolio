from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth

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
#####################################################3
# Login and sign UP
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # هنا يجب التحقق من المستخدم
            user = auth.get_user_by_email(email)  # احصل على بيانات المستخدم باستخدام البريد الإلكتروني
            
            # لا يوجد دعم مباشر للتحقق من كلمة المرور عبر API من Firebase Python SDK
            # لكن في تطبيقات الويب، يتم استخدام Firebase SDK للمتصفح للتحقق من كلمة المرور
            # وبالتالي يجب استخدام Firebase SDK في الواجهة الأمامية للتحقق من كلمة المرور

            # إذا تم التحقق بنجاح من بيانات المستخدم
            session['user_id'] = user.uid  # تخزين معرف المستخدم في الجلسة
            flash('Login successful!', 'success')
            return redirect(url_for('profile'))  # توجيه إلى صفحة الملف الشخصي أو الصفحة الرئيسية للمستخدم

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('login.html')


@app.route('/profile')
def profile():
    return render_template('profile.html')



@app.route('/regest', methods=['GET', 'POST'])
def signup():
            if request.method == 'POST':
                first_name = request.form.get('first_name')
                last_name = request.form.get('last_name')
                email = request.form.get('email')
                password = request.form.get('password')

                try:
                    # إنشاء مستخدم جديد في Firebase Authentication
                    user = auth.create_user(email=email, password=password)
                    
                    # حفظ بيانات المستخدم في Firestore
                    user_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'uid': user.uid,
                        'created_at': firestore.SERVER_TIMESTAMP,
                    }
                    db.collection('users').document(user.uid).set(user_data)
                    flash("User registered successfully!", "success")
                    return redirect(url_for('index'))
                except Exception as e:
                    flash(f"Error: {str(e)}", "danger")
    
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
@app.route('/admin')
def accounts():
    # قراءة جميع المستخدمين من Firestore
    users_ref = db.collection('users')
    users = users_ref.stream()

    # تحويل البيانات إلى قائمة
    user_list = []
    for user in users:
        user_data = user.to_dict()
        user_list.append(user_data)

    return render_template('admin.html', users=user_list)



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