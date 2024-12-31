from flask import Flask, request, render_template, send_file
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv
from PIL import Image
import os
import time

# Load environment variables from .env file (useful for local testing)
load_dotenv()

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploaded'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Access environment variables for API Key and Endpoint
COMPUTER_VISION_KEY = os.getenv("KEY")
COMPUTER_VISION_ENDPOINT = os.getenv("ENDPOINT")

# Check if the API Key and Endpoint are set
if not COMPUTER_VISION_KEY or not COMPUTER_VISION_ENDPOINT:
    raise ValueError("API Key or Endpoint is not set. Please check your environment variables.")

# Initialize Computer Vision client
computervision_client = ComputerVisionClient(
    COMPUTER_VISION_ENDPOINT, CognitiveServicesCredentials(COMPUTER_VISION_KEY)
)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Save uploaded image
        file = request.files['image']
        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process OCR
            try:
                extracted_text = extract_text(filepath)
                return render_template('result.html', text=extracted_text, filename=filename)
            except Exception as e:
                return f"An error occurred: {e}"
    return render_template('index.html')

def extract_text(filepath):
    """
    Extracts text from an image using Azure Computer Vision OCR.
    """
    with open(filepath, "rb") as image:
        # Call Azure OCR API
        read_response = computervision_client.read_in_stream(image, raw=True)
        operation_id = read_response.headers["Operation-Location"].split("/")[-1]

        # Wait for the operation to complete
        while True:
            read_result = computervision_client.get_read_result(operation_id)
            if read_result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        # Extract text
        extracted_text = ""
        if read_result.status == 'succeeded':
            for page in read_result.analyze_result.read_results:
                for line in page.lines:
                    extracted_text += line.text + "\n"
        return extracted_text

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    """
    Serve the uploaded file for download.
    """
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
