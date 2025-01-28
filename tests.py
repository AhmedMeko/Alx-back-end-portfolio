import pytest
from flask import Flask, session, url_for
from app import app, db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome" in response.data

def test_login(client):
    response = client.post("/login", data={
        "email": "test@example.com",
        "password": "password123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Login successful" in response.data

def test_register(client):
    response = client.post("/register", data={
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "password123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"User registered successfully" in response.data

def test_create_post(client):
    client.post("/login", data={
        "email": "test@example.com",
        "password": "password123"
    }, follow_redirects=True)

    response = client.post("/create", data={
        "title": "Test Post",
        "content": "This is a test post."
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Post created successfully" in response.data

def test_delete_post(client):
    client.post("/login", data={
        "email": "test@example.com",
        "password": "password123"
    }, follow_redirects=True)

    client.post("/create", data={
        "title": "Test Post",
        "content": "This is a test post."
    }, follow_redirects=True)

    response = client.post("/delete/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Post deleted successfully" in response.data

def test_admin_access_denied(client):
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    assert b"You do not have permission" in response.data

def test_admin_access_granted(client):
    client.post("/login", data={
        "email": "admin@example.com",
        "password": "admin123"
    }, follow_redirects=True)

    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data