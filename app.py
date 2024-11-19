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

# Playlist
playlist = []

@app.route('/')
def index():
    """Root route."""
    return jsonify({"message": "Welcome to the Shared Playlist App!"})

@app.route('/upload', methods=['POST'])
def upload():
    """Handle MP3 file uploads."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.mimetype != 'audio/mpeg':
        return jsonify({"error": "Only MP3 files are allowed"}), 400

    try:
        # Upload to Wasabi
        wasabi_client.upload_fileobj(
            file, WASABI_BUCKET, file.filename, ExtraArgs={"ContentType": file.mimetype}
        )
        file_url = f"https://{WASABI_BUCKET}.s3.eu-central-1.wasabisys.com/{file.filename}"

        # Add to playlist
        track = {"id": len(playlist) + 1, "title": file.filename, "url": file_url}
        playlist.append(track)

        # Notify clients
        socketio.emit('playlist_updated', playlist)
        return jsonify({"message": "Track uploaded successfully", "track": track}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/playlist', methods=['GET'])
def get_playlist():
    """Return the current playlist."""
    return jsonify(playlist)

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print("Client connected")
    socketio.emit('playlist_updated', playlist)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)