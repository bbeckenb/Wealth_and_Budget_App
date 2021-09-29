from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# best practice to create function to establish connection and only call it once
def connect_db(app):
    db.app = app
    db.init_app(app)
    db.create_all()
