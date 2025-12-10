#!/usr/bin/env python3
"""
DF Tales Flask Application
Web interface for Dwarf Fortress legends data.
"""

from pathlib import Path
from flask import Flask

from db import close_db, DATA_DIR, MASTER_DB_PATH
from helpers import (
    format_race, format_site_type, format_event_type,
    get_race_info, get_site_type_info, get_artifact_type_info,
    get_material_color, get_event_type_info, format_event_details,
    get_written_type_info
)
from routes.worlds import worlds_bp
from routes.pages import pages_bp
from routes.api import api_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = 'df-tales-secret-key'

    # Register teardown
    app.teardown_appcontext(close_db)

    # Register template filters
    app.jinja_env.filters['race_label'] = format_race
    app.jinja_env.filters['site_type_label'] = format_site_type
    app.jinja_env.filters['event_type_label'] = format_event_type

    # Register template globals
    app.jinja_env.globals['get_race_info'] = get_race_info
    app.jinja_env.globals['get_site_type_info'] = get_site_type_info
    app.jinja_env.globals['get_artifact_type_info'] = get_artifact_type_info
    app.jinja_env.globals['get_material_color'] = get_material_color
    app.jinja_env.globals['get_event_type_info'] = get_event_type_info
    app.jinja_env.globals['format_event_details'] = format_event_details
    app.jinja_env.globals['get_written_type_info'] = get_written_type_info

    # Register blueprints
    app.register_blueprint(worlds_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()


if __name__ == '__main__':
    print("=" * 50)
    print("DF Tales Server")
    print("=" * 50)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Master database: {MASTER_DB_PATH}")
    print("\nStarting server at http://localhost:5001")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5001, host='0.0.0.0')
