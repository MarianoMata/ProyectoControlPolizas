"""Punto de entrada de la aplicación Flask.

Crea la app Flask, configura carpetas de plantillas y estáticos,
y registra el Blueprint de rutas de pólizas.
"""

import os

from flask import Flask

from controllers.polizas_controller import bp

app = Flask(
    __name__,
    template_folder="views",
    static_folder="public/static",
    static_url_path="/static",
)

app.register_blueprint(bp)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=puerto)
