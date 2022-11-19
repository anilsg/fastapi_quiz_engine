"""
Unit tests can be run with pytest.
Tests currently rely on local Redis running in the environment.
These tests require test users and data to be loaded in the Redis.
TODO:
- Mock Redis to eliminate dependency on Redis test data
- Probably best to implement class-based tests
- More tests and coverage needed
"""
import os
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)
alpha = {"Authorization": os.environ["TEST_ACCESS_TOKEN_ALPHA"]}
gamma = {"Authorization": os.environ["TEST_ACCESS_TOKEN_GAMMA"]}


def test_intro():
    """Test unauthenticated basic intro response."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"introduction": "Quizzes on <b>FastAPI</b>"}


def test_token():
    """Test access token generation."""
    response = client.post(
        url="/token",
        headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={"username": "gamma@delta.com", "password": "secret"},
    )
    assert response.ok
    response = response.json()
    assert "access_token" in response
    assert "token_type" in response


def test_users_me():
    """Test user details are returned for user."""
    response = client.get(url="/api/v1/users/me", headers=alpha)
    assert response.ok
    response = response.json()
    assert response["email"] == "alpha@example.com"


def test_user_questions():
    """Test questions created by user are returned."""
    response = client.get(url="/api/v1/questions", headers=gamma)
    assert response.ok
    response = response.json()
    response = [r["text"] for r in response]
    assert "How long is a piece of string?" in response
    assert "What units is temperature measured in?" in response
    assert "Is the moon a star?" in response


def test_delete_published_questions():
    """Test user can't delete published questions."""
    response = client.delete(url="/api/v1/questions/FBi4Tb95oWTnJbqxvD3qbX-B7cKWmR6ZNqnosFC2nwVK5", headers=gamma)
    assert not response.ok
    assert response.status_code == 403
    response = response.json()
    assert response["detail"] == "Cannot delete Questions in use"


def test_solution_scoring():
    """Test quiz submission is scored correctly."""
    json = {
        "quiz": "FBi4Tb95oWTnJbqxvD3qbX-iQUkk5o2gU6oehnKTiFcNQ",
        "answers": [
            [False, False, False],
            [True, True, True, False, False],
            [False, True],
        ]
    }
    response = client.post(url="/api/v1/solutions", json=json, headers=gamma)
    assert response.ok
    response = response.json()
    assert response["scores"] == [0, 16, 100]
    assert response["score"] == 38


def test_repeat_quiz():
    """Test quiz submission cannot be repeated."""
    json = {
        "quiz": "FBi4Tb95oWTnJbqxvD3qbX-iQUkk5o2gU6oehnKTiFcNQ",
        "answers": [
            [False, False, False],
            [True, True, True, False, False],
            [False, True],
        ]
    }
    response = client.post(url="/api/v1/solutions", json=json, headers=alpha)
    assert not response.ok
    assert response.status_code == 403
    response = response.json()
    assert response["detail"] == "Cannot repeat Quiz"
