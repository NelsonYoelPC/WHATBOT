# generemos el archivo __init__.py para inicializar la aplicación Flask y registrar los blueprints
from flask import Flask
from .infraestructure.database import init_db

def create_app():
    app = Flask(__name__, template_folder="templates")
    init_db(app)
    return app