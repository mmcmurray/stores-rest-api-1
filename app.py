import os

from flask import Flask, render_template
from flask_restful import Api
from flask_jwt import JWT

from security import authenticate, identity
from resources.user import UserRegister
from resources.item import Item, ItemList
from resources.store import Store, StoreList

## Objects and definitions.
app = Flask(__name__)

app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True # Required for JTW to send proper response codes... 

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 's00p3rs3cr3tk3y'
api = Api(app)

jwt = JWT(app, authenticate, identity)  # /auth

## Routes and API resources.
@app.route('/')
def home():
    OC_POD_NAME = os.environ.get('OC_POD_NAME','foo')
    return render_template('index.html', oc_pod_name=OC_POD_NAME)

api.add_resource(Store, '/store/<string:name>')
api.add_resource(Item, '/item/<string:name>')
api.add_resource(ItemList, '/items')
api.add_resource(StoreList, '/stores')

api.add_resource(UserRegister, '/register')

if __name__ == '__main__':
    from db import db
    db.init_app(app)

    if app.config['DEBUG']:
        @app.before_first_request
        def create_tables():
            db.create_all()

    app.run(port=5000)