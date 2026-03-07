from dotenv import load_dotenv
from flask import Flask
from app.infraestructure.database import init_db
from app.presentacion.webhook import webhook_bp

load_dotenv()

app = Flask(__name__, template_folder="templates")

init_db(app)

app.register_blueprint(webhook_bp)

if __name__ == "__main__":
    with app.app_context():
        from app.infraestructure.database import db
        db.create_all()

    app.run(host="0.0.0.0", port=80, debug=True)
