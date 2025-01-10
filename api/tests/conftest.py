import os
import pytest
from app import app as flask_app
from database import db
import tempfile

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to use as a database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create the app with test config
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False
    })

    # Create the database and the database tables
    with flask_app.app_context():
        db.create_all()

    yield flask_app

    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

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
