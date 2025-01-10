import os
import pytest
from app import app as flask_app
from database import db

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Use an in-memory SQLite database for testing
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False
    })

    # Create the database and the database tables
    with flask_app.app_context():
        db.create_all()

    yield flask_app

    # Clean up after the test
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def init_database(app):
    """Initialize the database with some test data."""
    with app.app_context():
        db.create_all()
        # Add any initial test data here if needed
        db.session.commit()

    yield db  # this is where the testing happens

    with app.app_context():
        db.drop_all()