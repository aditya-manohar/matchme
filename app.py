from flask import Flask, render_template, request, flash, redirect, url_for
import os
import requests
from werkzeug.utils import secure_filename
import base64
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)
app.secret_key = 'secret123'

# Config - keeping your original structure
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['CELEBRITY_FOLDER'] = 'static/celebrities'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# Face++ API Config
FACEPP_API_KEY = 'yxPWWRh4XE_7ucx5W3Y8d0XmvXGBZI1z'
FACEPP_API_SECRET = '5slzsoUGLlqBcj8GPXKPab2BNwea-rpn'
FACEPP_COMPARE_URL = 'https://api-us.faceplusplus.com/facepp/v3/compare'

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def compare_face(celeb, filepath):
    celeb_path = os.path.join(app.config['CELEBRITY_FOLDER'], celeb)
    try:
        similarity = compare_faces(filepath, celeb_path)
        return {
            'name': os.path.splitext(celeb)[0].replace('_', ' ').title(),
            'path': celeb_path,
            'score': round(similarity, 1)
        } if similarity > 0 else None
    except Exception as e:
        print(f"Error comparing with {celeb}: {str(e)}")
        return None

def compare_faces(image1_path, image2_path):
    try:
        image1_base64 = encode_image_to_base64(image1_path)
        image2_base64 = encode_image_to_base64(image2_path)
        
        response = requests.post(
            FACEPP_COMPARE_URL,
            data={
                'api_key': FACEPP_API_KEY,
                'api_secret': FACEPP_API_SECRET,
                'image_base64_1': image1_base64,
                'image_base64_2': image2_base64
            },
            timeout=10  # Add timeout to prevent hanging
        )
        
        result = response.json()
        return result.get('confidence', 0)
    except Exception as e:
        print(f"API Error: {str(e)}")
        return 0

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return render_template('confirm.html', user_image=filepath)
    
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    filepath = request.form['filepath']
    best_match = None
    best_score = 0
    
    # Get all valid celebrity files
    celebrities = [f for f in os.listdir(app.config['CELEBRITY_FOLDER']) if allowed_file(f)]
    
    # Process comparisons in parallel
    futures = []
    for celeb in celebrities:
        futures.append(executor.submit(compare_face, celeb, filepath))
    
    # Wait for results
    for future in futures:
        result = future.result()
        if result and result['score'] > best_score:
            best_score = result['score']
            best_match = result
            if best_score >= 95:  # Early exit for perfect match
                break
    
    return render_template('result.html', 
                       user_image=filepath,  # Now showing the image
                       match=best_match if best_match and best_match['score'] > 0 else None)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  
    app.run(host='0.0.0.0', port=port, threaded=True)
