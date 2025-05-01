from flask import Flask, render_template, request, flash, redirect, url_for
import os
import time
from deepface import DeepFace
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secret123'

# Config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['CELEBRITY_FOLDER'] = 'static/celebrities'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CELEBRITY_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
            
            # Show confirmation page before processing
            return render_template('confirm.html', 
                               user_image=filepath)
    
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    filepath = request.form['filepath']
    
    # Find best match with loading simulation
    best_match = None
    best_score = 0
    
    for celeb in os.listdir(app.config['CELEBRITY_FOLDER']):
        if not allowed_file(celeb):
            continue
            
        celeb_path = os.path.join(app.config['CELEBRITY_FOLDER'], celeb)
        try:
            result = DeepFace.verify(
                img1_path=filepath,
                img2_path=celeb_path,
                model_name='Facenet',
                enforce_detection=False
            )
            
            similarity = (1 - result['distance']) * 100
            if similarity > best_score:
                best_score = similarity
                best_match = {
                    'name': os.path.splitext(celeb)[0].replace('_', ' ').title(),
                    'path': celeb_path,
                    'score': round(similarity, 1)
                }
        except Exception as e:
            print(f"Error comparing with {celeb}: {str(e)}")
            continue
    
    return render_template('result.html', 
                       user_image=filepath,
                       match=best_match if best_match and best_match['score'] > 0 else None)

if __name__ == '__main__':
    app.run(debug=True)