from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO
from flask_cors import CORS
from io import BytesIO

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"])  # Allow all origins for simplicity
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory playlist and current track info
playlist = []
current_track = None
current_stream = None


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    """Handle MP3 file upload and add it to the playlist."""
    global current_stream

    # Check if a file is in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate the file type
    if file.mimetype != 'audio/mpeg':
        return jsonify({"error": "Only MP3 files are allowed"}), 400

    try:
        # Add the track to the playlist
        track = {
            "id": len(playlist) + 1,
            "title": file.filename,
            "stream": BytesIO(file.read())
        }
        playlist.append(track)

        # Notify all clients about the updated playlist
        socketio.emit('playlist_updated', playlist)
        return jsonify({"message": "Track added to playlist", "track": track}), 201
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({"error": "Failed to upload file"}), 500


@app.route('/playlist', methods=['GET'])
def get_playlist():
    """Return the current playlist."""
    return jsonify(playlist)


@app.route('/stream', methods=['GET'])
def stream():
    """Stream the current track."""
    global current_track

    if not current_track:
        return jsonify({"error": "No track is currently playing"}), 404

    try:
        current_track["stream"].seek(0)  # Reset the stream pointer
        return Response(
            current_track["stream"].read(), mimetype='audio/mpeg'
        )
    except Exception as e:
        print(f"Error streaming file: {e}")
        return jsonify({"error": "Failed to stream the file"}), 500


@socketio.on('play_next')
def play_next():
    """Skip to the next track in the playlist."""
    global current_track, current_stream

    if playlist:
        # Set the next track as the current track
        current_track = playlist.pop(0)

        # Notify all clients about the change
        socketio.emit('track_changed', current_track)
        print(f"Now playing: {current_track['title']}")
    else:
        current_track = None
        socketio.emit('track_changed', None)
        print("No more tracks in the playlist.")


@socketio.on('connect')
def handle_connect():
    """Handle new client connections."""
    print("A client connected.")
    # Send the current playlist and track to the new client
    socketio.emit('playlist_updated', playlist)
    if current_track:
        socketio.emit('track_changed', current_track)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
