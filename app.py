from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import datetime

# Initialize the Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "welcome_to_my_world"
app.config["UPLOAD_FOLDER"] = "static/uploads/"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

# Ensure upload folder exists
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

# Initialize Firebase
try:
    cred = credentials.Certificate("key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firestore initialized successfully!")
except Exception as e:
    print("Error initializing Firestore:", e)
# Helper function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

# Helper function to make user an admin
def make_user_admin(user_id):
    user_ref = db.collection("users").document(user_id)
    user_ref.update({
        "is_admin": True
    })
    print(f"User {user_id} has been made an admin.")

# Example: make a specific user an admin
make_user_admin("RKXsBcjMMla1itb56blcqvqjCr12")

# Route for home page
@app.route("/")
def home():
    user_id = session.get("user_id")
    current_user = None
    if user_id:
        # Get user details from Firestore
        user_ref = db.collection("users").document(user_id)
        current_user = user_ref.get().to_dict()

    # Fetch all blog posts from Firestore, ordered by date
    posts_ref = db.collection("blog_posts")
    posts = posts_ref.order_by("date_time", direction=firestore.Query.DESCENDING).stream()
    blog_posts = [post.to_dict() for post in posts]
    
    # Render the homepage template and pass blog posts and current user info
    return render_template("home.html", blog_posts=blog_posts, current_user=current_user)

# Route for viewing a specific blog post
@app.route("/post/<id>")
def view_post(id):
    post_ref = db.collection("blog_posts").document(id)
    post = post_ref.get()
    if post.exists:
        return render_template("edit_post.html", post=post.to_dict())
    else:
        flash("Post not found.", "danger")
        return redirect(url_for("home"))
# Route for creating a new blog post
@app.route("/create", methods=["GET", "POST"])
def create_post():
    user_id = session.get("user_id")
    
    if not user_id:
        flash("You must be logged in to create a post.", "danger")
        return redirect(url_for("login"))

    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()
    
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        image_url = None
        
        if not title or not content:
            flash("Title and Content are required.", "danger")
            return redirect(url_for("create_post"))
        
        # Save the image if provided
        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_url = url_for("static", filename=f"uploads/{filename}")
        
        # Prepare post data
        post_data = {
            "title": title,
            "content": content,
            "image_url": image_url,
            "date_time": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "user_name": f"{user['first_name']} {user['last_name']}"
        }
        
        # Add post to Firestore
        db.collection("blog_posts").add(post_data)
        flash("Post created successfully!", "success")
        
        return redirect(url_for("home"))
    
    return render_template("create_post.html")

# Route for deleting a specific blog post
@app.route("/delete/<id>", methods=["POST"])
def delete_post(id):
    post_ref = db.collection("blog_posts").document(id)
    post = post_ref.get()
    
    if post.exists:
        # Delete the post if it exists
        post_ref.delete()
        flash("Post deleted successfully!", "success")
    else:
        flash("Post not found.", "danger")
    return redirect(url_for("home"))

# Route for login page
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

# Route for logging out
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))

# Route for user registration
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

# Route for admin dashboard
@app.route("/admin")
def admin():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to access the admin page.", "danger")
        return redirect(url_for("login"))

    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()
    print("Current User:", user)  # Debugging

    if not user or not user.get("is_admin", False):
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    users_ref = db.collection("users")
    users = users_ref.stream()
    users_data = [user.to_dict() for user in users]
    print("Users Data:", users_data)  # Debugging

    return render_template("admin.html", users=users_data)

# Route for adding a new user (admin access only)
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
        # Create new user
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

# Route for user profile page
@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your profile.", "danger")
        return redirect(url_for("login"))

    user_ref = db.collection("users").document(user_id)
    user = user_ref.get().to_dict()

    if request.method == "POST":
        # Handling profile update form submission
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        password = request.form["password"]
        age = request.form["age"]
        
        updated_data = {
            "first_name": first_name,
            "last_name": last_name,
            "password": password,  # Updating password
            "age": age,
        }

        # Save profile picture if uploaded
        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                profile_picture_url = url_for("static", filename=f"uploads/{filename}")
                updated_data["profile_picture"] = profile_picture_url

        # Update user data in Firestore
        user_ref.update(updated_data)
        
        # Update password in Firebase
        if password:
            try:
                user = auth.update_user(user_id, password=password)
                flash("Profile updated successfully!", "success")
            except Exception as e:
                flash(f"Error updating password: {str(e)}", "danger")

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
