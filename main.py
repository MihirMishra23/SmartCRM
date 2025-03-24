from backend.app import create_app
from backend.app.models.base import db
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
