"""
World management routes for DF Tales.
Handles world switching, uploading, deletion, and map management.
"""

import subprocess
import sys
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from PIL import Image

from db import (
    get_master_db, get_current_world, get_all_worlds,
    get_db, get_stats, get_world_info, DATA_DIR, BASE_DIR
)

worlds_bp = Blueprint('worlds', __name__)


def save_world_map(world_id, map_file):
    """Save world map image, converting BMP to PNG if needed."""
    try:
        # Read image
        img = Image.open(map_file)

        # Save as PNG in worlds directory
        map_path = DATA_DIR / 'worlds' / f'{world_id}_map.png'
        img.save(map_path, 'PNG')

        # Update has_map flag
        db = get_master_db()
        db.execute("UPDATE worlds SET has_map = 1 WHERE id = ?", (world_id,))
        db.commit()

        return True
    except Exception as e:
        print(f"Error saving map: {e}")
        return False


@worlds_bp.route('/')
def index():
    """Dashboard page."""
    current_world = get_current_world()
    all_worlds = get_all_worlds()
    world = get_world_info()
    stats = get_stats()

    return render_template('index.html',
                         world=world,
                         stats=stats,
                         current_world=current_world,
                         all_worlds=all_worlds)


@worlds_bp.route('/switch-world/<world_id>', methods=['POST'])
def switch_world(world_id):
    """Switch to a different world."""
    db = get_master_db()
    cursor = db.cursor()

    # Verify world exists
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('worlds.index'))

    # Switch current world
    cursor.execute("UPDATE worlds SET is_current = 0 WHERE is_current = 1")
    cursor.execute("UPDATE worlds SET is_current = 1 WHERE id = ?", (world_id,))
    db.commit()

    flash(f"Switched to world: {world['name']}", 'success')
    return redirect(url_for('worlds.index'))


@worlds_bp.route('/delete-world/<world_id>', methods=['POST'])
def delete_world(world_id):
    """Delete a world and its database."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('worlds.index'))

    # Delete database file and WAL journal files
    db_path = Path(world['db_path'])
    if db_path.exists():
        db_path.unlink()
    # Clean up WAL journal files
    wal_path = db_path.with_suffix('.db-wal')
    shm_path = db_path.with_suffix('.db-shm')
    if wal_path.exists():
        wal_path.unlink()
    if shm_path.exists():
        shm_path.unlink()
    # Clean up map file if exists
    map_path = db_path.with_name(f'{world_id}_map.png')
    if map_path.exists():
        map_path.unlink()

    # Remove from master database
    cursor.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
    db.commit()

    flash(f"Deleted world: {world['name']}", 'success')
    return redirect(url_for('worlds.index'))


@worlds_bp.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and run import."""
    # Check for legends file (required)
    if 'legends' not in request.files or request.files['legends'].filename == '':
        flash('legends.xml file is required', 'error')
        return redirect(url_for('worlds.index'))

    legends_file = request.files['legends']
    plus_file = request.files.get('legends_plus')
    map_file = request.files.get('world_map')

    # Create uploads directory
    upload_dir = DATA_DIR / 'uploads'
    upload_dir.mkdir(exist_ok=True)

    # Save uploaded files
    legends_path = upload_dir / 'legends.xml'
    legends_file.save(legends_path)

    plus_path = None
    if plus_file and plus_file.filename:
        plus_path = upload_dir / 'legends_plus.xml'
        plus_file.save(plus_path)

    # Run import with file paths
    try:
        cmd = [sys.executable, str(BASE_DIR / 'build.py'), str(legends_path)]
        if plus_path:
            cmd.append(str(plus_path))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            flash('Import completed successfully!', 'success')

            # If map file provided, save it for the newly created world
            if map_file and map_file.filename:
                # Get the world that was just created (most recent)
                world = get_current_world()
                if world:
                    if save_world_map(world['id'], map_file):
                        flash('World map uploaded!', 'success')
                    else:
                        flash('Failed to save world map', 'error')
        else:
            flash(f'Import failed: {result.stderr}', 'error')

        # Store output for display
        current_app.config['LAST_BUILD_OUTPUT'] = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        flash('Import timed out after 10 minutes', 'error')
    except Exception as e:
        flash(f'Error running import: {str(e)}', 'error')
    finally:
        # Cleanup uploaded files
        if legends_path.exists():
            legends_path.unlink()
        if plus_path and plus_path.exists():
            plus_path.unlink()

    return redirect(url_for('worlds.index'))


@worlds_bp.route('/merge-plus/<world_id>', methods=['POST'])
def merge_plus(world_id):
    """Merge legends_plus.xml into an existing world."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('worlds.index'))

    if world['has_plus']:
        flash('This world already has legends_plus data', 'error')
        return redirect(url_for('worlds.index'))

    # Check for legends_plus file
    if 'legends_plus' not in request.files or request.files['legends_plus'].filename == '':
        flash('legends_plus.xml file is required', 'error')
        return redirect(url_for('worlds.index'))

    plus_file = request.files['legends_plus']

    # Create uploads directory
    upload_dir = DATA_DIR / 'uploads'
    upload_dir.mkdir(exist_ok=True)

    # Save uploaded file
    plus_path = upload_dir / 'legends_plus.xml'
    plus_file.save(plus_path)

    # Run merge with file path
    try:
        cmd = [
            sys.executable, str(BASE_DIR / 'build.py'),
            '--merge', world_id, world['db_path'], str(plus_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            flash('Legends+ data merged successfully!', 'success')
        else:
            flash(f'Merge failed: {result.stderr}', 'error')

        # Store output for display
        current_app.config['LAST_BUILD_OUTPUT'] = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        flash('Merge timed out after 10 minutes', 'error')
    except Exception as e:
        flash(f'Error running merge: {str(e)}', 'error')
    finally:
        # Cleanup uploaded file
        if plus_path.exists():
            plus_path.unlink()

    return redirect(url_for('worlds.index'))


@worlds_bp.route('/upload-map/<world_id>', methods=['POST'])
def upload_map(world_id):
    """Upload world map image for an existing world."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('worlds.index'))

    # Check for map file
    if 'world_map' not in request.files or request.files['world_map'].filename == '':
        flash('Map file is required', 'error')
        return redirect(url_for('worlds.index'))

    map_file = request.files['world_map']

    if save_world_map(world_id, map_file):
        flash('World map uploaded successfully!', 'success')
    else:
        flash('Failed to save world map', 'error')

    return redirect(url_for('worlds.index'))


@worlds_bp.route('/world-map-image/<world_id>')
def world_map_image(world_id):
    """Serve the world map image (terrain or uploaded)."""
    # Prefer generated terrain map
    terrain_path = DATA_DIR / 'worlds' / f'{world_id}_terrain.png'
    if terrain_path.exists():
        return send_file(terrain_path, mimetype='image/png')
    # Fall back to uploaded map
    map_path = DATA_DIR / 'worlds' / f'{world_id}_map.png'
    if map_path.exists():
        return send_file(map_path, mimetype='image/png')
    else:
        return '', 404


@worlds_bp.route('/build-output')
def build_output():
    """Show last build output."""
    output = current_app.config.get('LAST_BUILD_OUTPUT', 'No build output available.')
    return render_template('output.html', output=output)
