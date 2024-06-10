import prettytable as prettytable
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db: SQLAlchemy = SQLAlchemy(app)


class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    country = db.Column(db.String)
    age = db.Column(db.Integer)


db.create_all()

user = Users(
    id=1,
    name="Андрей",
    country="Россия",
    age=10)

users = (user, )

with db.session.begin():
    db.session.add_all(users)

session = db.session()
cursor = session.execute(f"SELECT * from {Users.__tablename__}").cursor
mytable = prettytable.from_db_cursor(cursor)
mytable.max_width = 30

if __name__ == '__main__':
    print(mytable)
