from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-secret-key")  # Use environment variable for security
app.config["UPLOAD_FOLDER"] = "static/uploads/"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # Limit file uploads to 16MB

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize Firebase
try:
    cred = credentials.Certificate("key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firestore initialized successfully!")
except Exception as e:
    print("Error initializing Firestore:", e)


# Helper Functions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for("login"))

        user_ref = db.collection("users").document(user_id)
        user = user_ref.get().to_dict()
        if not user or not user.get("is_admin", False):
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route("/")
def home():
    user_id = session.get("user_id")
    current_user = None
    if user_id:
        user_ref = db.collection("users").document(user_id)
        current_user = user_ref.get().to_dict()

    posts_ref = db.collection("blog_posts")
    posts = posts_ref.order_by("date_time", direction=firestore.Query.DESCENDING).stream()

    blog_posts = [{"id": post.id, **post.to_dict()} for post in posts]
    return render_template("home.html", blog_posts=blog_posts, current_user=current_user)


@app.route("/post/<id>")
def view_post(id):
    post_ref = db.collection("blog_posts").document(id)
    post = post_ref.get()
    if post.exists:
        return render_template("view_post.html", post=post.to_dict(), post_id=id)
    else:
        flash("Post not found.", "danger")
        return redirect(url_for("home"))


@app.route("/create", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        image_url = None

        if not title or not content:
            flash("Title and Content are required.", "danger")
            return redirect(url_for("create_post"))

        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_url = url_for("static", filename=f"uploads/{filename}")

        post_data = {
            "title": title,
            "content": content,
            "image_url": image_url,
            "date_time": datetime.now().isoformat(),
            "user_id": session["user_id"],
            "user_name": db.collection("users").document(session["user_id"]).get().to_dict().get("name", "Anonymous")
        }

        db.collection("blog_posts").add(post_data)
        flash("Post created successfully!", "success")
        return redirect(url_for("home"))

    return render_template("create_post.html")


@app.route("/delete/<id>", methods=["POST"])
@login_required
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
                "created_at": datetime.now().isoformat(),
                "is_admin": False
            }
            db.collection("users").document(user.uid).set(user_data)
            flash("User registered successfully!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Registration failed. Please try again.", "danger")
    return render_template("sign_up.html")


@app.route("/admin")
@admin_required
def admin():
    users_ref = db.collection("users")
    users = users_ref.stream()
    users_data = [user.to_dict() for user in users]
    return render_template("admin.html", users=users_data)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if request.method == "POST":
        updated_data = {
            "first_name": request.form["first_name"],
            "last_name": request.form["last_name"],
            "age": request.form["age"]
        }

        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                updated_data["profile_picture"] = url_for("static", filename=f"uploads/{filename}")

        user_ref.update(updated_data)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


# Run the app
if __name__ == "__main__":
    app.run(debug=True)