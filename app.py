from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import datetime
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "welcome_to_my_world"
app.config["UPLOAD_FOLDER"] = "static/uploads/"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def make_user_admin(user_id):
    user_ref = db.collection("users").document(user_id)
    user_ref.update({
        "is_admin": True
    })
    print(f"User {user_id} has been made an admin.")
    
make_user_admin("9RrhSqtMazZ7W9Ddmm8UA2rJ7Qx1")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

@app.route("/")
def home():
    posts_ref = db.collection("blog_posts")
    posts = posts_ref.order_by("date_time", direction=firestore.Query.DESCENDING).stream()
    blog_posts = [post.to_dict() for post in posts]
    return render_template("home.html", blog_posts=blog_posts)

@app.route("/post/<id>")
def view_post(id):
    post_ref = db.collection("blog_posts").document(id)
    post = post_ref.get()
    if post.exists:
        return render_template("view_post.html", post=post.to_dict())
    else:
        flash("Post not found.", "danger")
        return redirect(url_for("home"))

@app.route("/create", methods=["GET", "POST"])
@app.route("/edit/<id>", methods=["GET", "POST"])
def create_or_edit_post(id=None):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to create or edit a post.", "danger")
        return redirect(url_for("login"))

    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    is_admin = user.get("is_admin", False)

    if id:
        post_ref = db.collection("blog_posts").document(id)
        post = post_ref.get()
        if post.exists:
            post_data = post.to_dict()
            if post_data["user_id"] != user_id and not is_admin:
                flash("You do not have permission to edit this post.", "danger")
                return redirect(url_for("home"))
        else:
            flash("Post not found.", "danger")
            return redirect(url_for("home"))
    else:
        post_data = None

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        image_url = None

        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_url = url_for("static", filename=f"uploads/{filename}")
            else:
                flash("Invalid image format. Supported formats are png, jpg, jpeg, gif.", "danger")
                return redirect(request.url)

        if not title or not content:
            flash("Title and content are required.", "danger")
            return redirect(request.url)

        post_id = str(uuid.uuid4()) if not id else id
        post_data = {
            "id": post_id,
            "title": title,
            "content": content,
            "image_url": image_url,
            "date_time": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "user_name": user["first_name"] + " " + user["last_name"]
        }

        if id:
            post_ref.update(post_data)
            flash("Post updated successfully!", "success")
        else:
            db.collection("blog_posts").document(post_id).set(post_data)
            flash("Post created successfully!", "success")

        return redirect(url_for("home"))

    return render_template("create_or_edit_post.html", post=post_data)

@app.route("/delete/<id>", methods=["POST"])
def delete_post(id):
    post_ref = db.collection("blog_posts").document(id)
    post = post_ref.get()
    if post.exists:
        post_ref.delete()
        flash("Post deleted successfully!", "success")
    else:
        flash("Post not found.", "danger")
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            user = auth.get_user_by_email(email)
            session["user_id"] = user.uid
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        except Exception as e:
            flash("Login failed. Please check your credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        try:
            user = auth.create_user(email=email, password=password)
            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "created_at": datetime.datetime.now().isoformat(),
            }
            db.collection("users").document(user.uid).set(user_data)
            flash("User registered successfully!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Registration failed. Please try again.", "danger")
    return render_template("sign_up.html")

@app.route("/admin")
def admin():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to access the admin page.", "danger")
        return redirect(url_for("login"))
    
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if not user or not user.get("is_admin", False):
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    users_ref = db.collection("users")
    users = users_ref.stream()
    users_data = [user.to_dict() for user in users]

    return render_template("admin.html", users=users_data)

@app.route("/add_user", methods=["POST"])
def add_user():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to add a user.", "danger")
        return redirect(url_for("login"))
    
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if not user or not user.get("is_admin", False):
        flash("You do not have permission to add users.", "danger")
        return redirect(url_for("home"))
    
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    try:
        new_user = auth.create_user(email=email, password=password)
        user_data = {
            "name": name,
            "email": email,
            "uid": new_user.uid,
            "password": password
        }
        db.collection("users").document(new_user.uid).set(user_data)

        flash("User added successfully!", "success")
    except Exception as e:
        flash("Error adding user: " + str(e), "danger")

    return redirect(url_for("admin"))

@app.route("/edit_user/<uid>", methods=["GET", "POST"])
def edit_user(uid):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to edit a user.", "danger")
        return redirect(url_for("login"))
    
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if not user or not user.get("is_admin", False):
        flash("You do not have permission to edit users.", "danger")
        return redirect(url_for("home"))
    
    user_ref = db.collection("users").document(uid)
    user_to_edit = user_ref.get().to_dict()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        
        updated_data = {
            "name": name,
            "email": email,
            "uid": uid
        }

        user_ref.update(updated_data)
        flash("User updated successfully!", "success")
        return redirect(url_for("admin"))

    return render_template("edit_user.html", user=user_to_edit)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your profile.", "danger")
        return redirect(url_for("login"))

    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if request.method == "POST":
        # استلام البيانات من النموذج
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        password = request.form["password"]
        age = request.form["age"]
        
        updated_data = {
            "first_name": first_name,
            "last_name": last_name,
            "password": password,  # هنا يتم تحديث كلمة المرور
            "age": age,
        }

        # إضافة صورة البروفايل إذا تم تحميلها
        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                profile_picture_url = url_for("static", filename=f"uploads/{filename}")
                updated_data["profile_picture"] = profile_picture_url

        # تحديث البيانات في Firestore
        user_ref.update(updated_data)
        
        # تحديث كلمة المرور في Firebase
        if password:
            try:
                user = auth.update_user(user_id, password=password)
                flash("Profile updated successfully!", "success")
            except Exception as e:
                flash(f"Error updating password: {str(e)}", "danger")

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)
