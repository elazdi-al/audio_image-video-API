from flask import Flask, request, send_file, jsonify
import logging
import os
from moviepy.editor import ImageClip, AudioFileClip
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Allowable file extensions for audio and image
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'aac', 'm4a'}

# Helper function to check allowed file extensions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        # Check if both 'audio' and 'image' are present in the request
        if 'audio' not in request.files or 'image' not in request.files:
            return jsonify({'error': "Please provide both 'audio' and 'image' files."}), 400

        logging.info('Received files')

        # Retrieve the files
        audio_file = request.files['audio']
        image_file = request.files['image']

        # Secure file names
        audio_filename = secure_filename(audio_file.filename)
        image_filename = secure_filename(image_file.filename)

        logging.info(f'Audio file name: {audio_filename}, Image file name: {image_filename}')

        # Check for allowed file types
        if not allowed_file(image_filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': 'Unsupported image format. Allowed formats: png, jpg, jpeg, bmp'}), 400

        if not allowed_file(audio_filename, ALLOWED_AUDIO_EXTENSIONS):
            return jsonify({'error': 'Unsupported audio format. Allowed formats: mp3, wav, ogg, aac, m4a'}), 400

        # Save files temporarily
        audio_file_path = os.path.join('/tmp', audio_filename)
        image_file_path = os.path.join('/tmp', image_filename)

        audio_file.save(audio_file_path)
        image_file.save(image_file_path)

        logging.info('Files saved successfully')

        # Process the image and audio
        image_clip = ImageClip(image_file_path)
        audio_clip = AudioFileClip(audio_file_path)

        logging.info('Loaded image and audio clips')

        # Set video duration to match the audio length
        image_clip = image_clip.set_duration(audio_clip.duration)

        # Resize and pad the image to fit 1920x1080
        # Get the original size of the image
        original_width, original_height = image_clip.size

        # Calculate the aspect ratio of the image
        aspect_ratio = original_width / original_height

        # Target video size
        target_width = 1920
        target_height = 1080
        target_aspect = target_width / target_height

        # Decide how to resize the image
        if aspect_ratio > target_aspect:
            # Image is wider than the target aspect ratio
            # Resize image width to target width; height will be less than target height
            image_clip = image_clip.resize(width=target_width)
        else:
            # Image is narrower than the target aspect ratio
            # Resize image height to target height; width will be less than target width
            image_clip = image_clip.resize(height=target_height)

        # Now, pad the image to make it exactly 1920x1080
        image_clip = image_clip.on_color(size=(target_width, target_height), color=(0, 0, 0), col_opacity=1)

        # Set the audio for the video
        video_clip = image_clip.set_audio(audio_clip)

        # Save the final video to an in-memory buffer
        video_output_path = '/tmp/output_video.mp4'
        video_clip.write_videofile(video_output_path, codec="libx264", audio_codec="aac", fps=24)

        logging.info('Video created successfully')

        # Clean up temporary files
        os.remove(audio_file_path)
        os.remove(image_file_path)

        # Return the video file as a response
        return send_file(video_output_path, as_attachment=True)

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
