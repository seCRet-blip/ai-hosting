from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from model_arc import ONNXInference
from PIL import Image
import io
import numpy as np
import torch
from torchvision import transforms
import os
import hashlib
from functools import wraps
import logging

# Configure secure logging (errors logged but not exposed to clients)
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
# CORS is handled by nginx proxy, disable Flask CORS to prevent duplicate headers
# CORS(app)

# Rate limiting - strict limits to prevent abuse
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["30 per hour"],  # Align with nginx limits
    storage_uri="memory://"
)

# API Key Authentication with hashing
RAW_API_KEY = os.environ.get('AI_API_KEY')
# Hash the API key on startup for secure comparison
API_KEY_HASH = hashlib.sha256(RAW_API_KEY.encode()).hexdigest()

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow health checks without authentication
        if request.path == '/health':
            return f(*args, **kwargs)
        
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'Unauthorized - Invalid or missing API key'}), 401
        
        # Hash the provided key and compare with stored hash
        provided_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if provided_key_hash != API_KEY_HASH:
            return jsonify({'error': 'Unauthorized - Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Initialize the ONNX model
try:
    predictor = ONNXInference("models/improved_All_nz_regions_model.onnx")
    logging.info("Model loaded successfully")
except Exception as e:
    logging.error(f"Failed to load model: {type(e).__name__}")
    predictor = None

def preprocess_image(image):
    """Preprocess image for EfficientNet"""
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    tensor = transform(image).unsqueeze(0)  # Add batch dimension
    return tensor

@app.route('/', methods=['GET'])
@limiter.limit("30 per hour")
def home():
    return jsonify({
        "message": "AI Model API is running!",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST with file upload)"
        },
        "note": "API key required for /predict endpoint"
    }), 200

@app.route('/health', methods=['GET'])
@limiter.limit("60 per hour")  # More generous for monitoring
def health_check():
    return jsonify({"status": "healthy", "model_loaded": predictor is not None}), 200

@app.route('/predict', methods=['POST'])
@limiter.limit("30 per hour")  # 30 predictions per hour
@require_api_key
def predict():
    try:
        if predictor is None:
            return jsonify({"error": "Model not loaded"}), 500
        
        # Validate request size (already handled by nginx, but double check)
        if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
            return jsonify({"error": "File too large - maximum 10MB"}), 413
        
        # Check if image file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"}), 400
        
        # Read file with size limit
        file_data = file.read(10 * 1024 * 1024)  # Read max 10MB
        if len(file_data) == 0:
            return jsonify({"error": "Empty file"}), 400
        
        # Load and validate image
        try:
            image = Image.open(io.BytesIO(file_data))
            image.verify()  # Verify it's a valid image
            image = Image.open(io.BytesIO(file_data))  # Reopen after verify
            image = image.convert('RGB')
        except Exception as e:
            logging.warning(f"Image validation failed: {type(e).__name__}")
            return jsonify({"error": "Invalid or corrupted image file"}), 400
        
        # Validate image dimensions (prevent extremely large images)
        if image.size[0] > 4096 or image.size[1] > 4096:
            return jsonify({"error": "Image dimensions too large - maximum 4096x4096"}), 400
        
        # Preprocess image
        tensor = preprocess_image(image)
        
        # Run inference - this returns numpy array
        result = predictor.predict(tensor)
        
        # Handle different result shapes
        if result.ndim == 1:
            logits = result
        elif result.ndim == 2 and result.shape[0] == 1:
            logits = result[0]
        else:
            logits = result.flatten() if result.size > 0 else result
        
        # Convert to probabilities using softmax
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)
        
        # Get prediction and confidence
        prediction = int(np.argmax(logits))
        confidence = float(np.max(probabilities))
        
        return jsonify({
            "prediction": prediction,
            "probabilities": probabilities.tolist(),
            "confidence": confidence
        })
        
    except Exception as e:
        # Log error type only, not detailed message to prevent info leakage
        logging.error(f"Prediction failed: {type(e).__name__}")
        return jsonify({"error": "Prediction failed"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large - maximum 10MB"}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logging.info("Starting Flask server on 0.0.0.0:5001")
    logging.info("API Key authentication enabled")
    # Disable debug mode for production
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)