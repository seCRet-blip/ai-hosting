
# ============================================
# FILE: app.py
# Save as: C:\ai-model-docker\app.py
# ============================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import base64
import numpy as np
import os
import torch
# Import your model library
# import tensorflow as tf
# import torch

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Load model
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models/your_model.h5')

print("="*50)
print("🤖 Loading AI Model...")
print(f"📁 Model path: {MODEL_PATH}")

try:

    
    # FOR PYTORCH:
    model = torch.load(MODEL_PATH, map_location='cpu')
    model.eval()
    print("✅ PyTorch model loaded successfully!")
    
    # TEMPORARY: Comment out when you add your model
    model = None
    print("⚠️  Using dummy model - replace with your actual model loading code")
    
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

print("="*50)


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'service': 'AI Model Prediction API',
        'status': 'running',
        'endpoints': {
            '/health': 'GET - Health check',
            '/predict': 'POST - Make prediction'
        }
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Decode base64 image
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Preprocess image
        image = image.resize((128, 128))  # Adjust to your model size
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image) / 128.0
        image_array = np.expand_dims(image_array, axis=0)
        
        # ============================================
        # YOUR MODEL PREDICTION CODE HERE
        # ============================================
        
        if model is None:
            # Dummy response for testing
            result = {
                'class': 'test_class',
                'confidence': 0.95,
                'all_predictions': {
                    'test_class': 0.95,
                    'other_class': 0.03,
                    'another_class': 0.02
                }
            }
        else:
            # TENSORFLOW EXAMPLE:
            # predictions = model.predict(image_array)
            # predicted_idx = int(np.argmax(predictions[0]))
            # confidence = float(predictions[0][predicted_idx])
            # class_names = ['cat', 'dog', 'bird']  # Your classes
            # 
            # result = {
            #     'class': class_names[predicted_idx],
            #     'confidence': confidence,
            #     'all_predictions': {
            #         class_names[i]: float(predictions[0][i])
            #         for i in range(len(class_names))
            #     }
            # }
            
            # PYTORCH EXAMPLE:
            # import torch
            # with torch.no_grad():
            #     tensor = torch.from_numpy(image_array).float()
            #     predictions = model(tensor)
            #     probs = torch.softmax(predictions, dim=1)[0]
            #     predicted_idx = int(torch.argmax(probs))
            #     confidence = float(probs[predicted_idx])
            #     
            # class_names = ['cat', 'dog', 'bird']
            # result = {
            #     'class': class_names[predicted_idx],
            #     'confidence': confidence,
            #     'all_predictions': {
            #         class_names[i]: float(probs[i])
            #         for i in range(len(class_names))
            #     }
            # }
            
            result = {}  # Replace with actual prediction
        
        print(f"✅ Prediction: {result['class']} ({result['confidence']:.2%})")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 AI MODEL SERVICE STARTING")
    print("="*50)
    print("📡 Server: http://0.0.0.0:5000")
    print("📍 Endpoints:")
    print("   GET  /        - API info")
    print("   GET  /health  - Health check")
    print("   POST /predict - Make prediction")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)