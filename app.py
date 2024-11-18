from flask import Flask, request, send_file, jsonify
from flask_socketio import SocketIO
from io import BytesIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Temporary storage for the current MP3 file
current_audio = None

@app.route('/')
def index():
    # Serve the frontend HTML file
    return send_file('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    global current_audio
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.mimetype != 'audio/mpeg':
        return jsonify({"error": "Only MP3 files are allowed"}), 400

    # Save the file in memory
    current_audio = BytesIO(file.read())
    current_audio.seek(0)

    # Notify all connected clients about the new track
    socketio.emit('new_track')
    return jsonify({"message": "MP3 is streaming now"}), 200

@app.route('/stream', methods=['GET'])
def stream():
    global current_audio
    if not current_audio:
        return jsonify({"error": "No track is currently streaming"}), 404

    current_audio.seek(0)
    return send_file(current_audio, mimetype='audio/mpeg')

@socketio.on('connect')
def handle_connect():
    print("Client connected")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
