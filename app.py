import boto3
from botocore.exceptions import NoCredentialsError
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Wasabi Configuration
WASABI_BUCKET = 'soundsync'  # Replace with your bucket name
WASABI_ENDPOINT = 'https://s3.eu-central-1.wasabisys.com'  # Replace with your Wasabi region
WASABI_ACCESS_KEY = 'OFN24PDMFN7DO7TWS6V2'  # Replace with your access key
WASABI_SECRET_KEY = 'SKAYVT6NMDPX5EASPTFECNFVJGSDUA23MDMHQQXKSEDDVIPPDER76HCCRT6BHVGR'  # Replace with your secret key

# Wasabi Client
wasabi_client = boto3.client(
    's3',
    aws_access_key_id=WASABI_ACCESS_KEY,
    aws_secret_access_key=WASABI_SECRET_KEY,
    endpoint_url=WASABI_ENDPOINT
)

# Shared Playlist
playlist = []
current_track = None  # Stores the currently playing track


@app.route('/upload', methods=['POST'])
def upload():
    """Handle MP3 file upload to Wasabi and add it to the playlist."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate file type
    if file.mimetype != 'audio/mpeg':
        return jsonify({"error": "Only MP3 files are allowed"}), 400

    try:
        # Upload file to Wasabi
        wasabi_client.upload_fileobj(
            file,
            WASABI_BUCKET,
            file.filename,
            ExtraArgs={"ContentType": file.mimetype}
        )

        # Generate public URL
        file_url = f"https://{WASABI_BUCKET}.s3.us-east-1.wasabisys.com/{file.filename}"

        # Add track to the playlist
        track = {"id": len(playlist) + 1, "title": file.filename, "url": file_url}
        playlist.append(track)

        # Notify all connected clients about the updated playlist
        socketio.emit('playlist_updated', playlist)
        return jsonify({"message": "Track uploaded successfully", "track": track}), 201
    except NoCredentialsError:
        return jsonify({"error": "Invalid Wasabi credentials"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/playlist', methods=['GET'])
def get_playlist():
    """Return the current playlist."""
    return jsonify(playlist)


@socketio.on('play_next')
def play_next():
    """Skip to the next track in the playlist."""
    global current_track

    if playlist:
        # Set the next track as the current track
        current_track = playlist.pop(0)

        # Notify all clients about the track change
        socketio.emit('track_changed', current_track)
        print(f"Now playing: {current_track['title']}")
    else:
        current_track = None
        socketio.emit('track_changed', None)
        print("No more tracks in the playlist.")


@socketio.on('connect')
def handle_connect():
    """Handle a new WebSocket connection."""
    print("A client connected.")
    # Send the current playlist and track to the new client
    socketio.emit('playlist_updated', playlist)
    if current_track:
        socketio.emit('track_changed', current_track)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
