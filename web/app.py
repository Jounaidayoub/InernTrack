"""Simple Flask web frontend for the internships scraper."""
from flask import Flask
from web.routes import bp as main_bp
import os

app = Flask(__name__, static_folder="static", template_folder="templates")
app.register_blueprint(main_bp)


@app.route('/health')
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)
