from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import torch
from torchvision import transforms
from PIL import Image
import onnxruntime as ort
import io
import base64

app = Flask(__name__)
CORS(app)

class ONNXInference:
    """ONNX inference class"""
    def __init__(self, onnx_path):
        self.session = ort.InferenceSession(onnx_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        # Print model info
        print(f"Input name: {self.input_name}")
        print(f"Input shape: {self.session.get_inputs()[0].shape}")
        print(f"Output name: {self.output_name}")
        print(f"Output shape: {self.session.get_outputs()[0].shape}")
    
    def predict(self, input_tensor):
        """Run inference on input tensor"""
        if isinstance(input_tensor, torch.Tensor):
            input_tensor = input_tensor.numpy()
        
        result = self.session.run(
            [self.output_name],
            {self.input_name: input_tensor}
        )
        return result[0]

# Load ONNX model once when server starts
try:
    onnx_model = ONNXInference('models/All_nz_regions_model.onnx')
    print("ONNX model loaded successfully!")
except Exception as e:
    print(f"Error loading ONNX model: {e}")
    onnx_model = None

# Define preprocessing transforms (match your training preprocessing)
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

@app.route('/health', methods=['GET'])
def health_check():
    status = "healthy" if onnx_model else "unhealthy"
    return jsonify({"status": status}), 200 if onnx_model else 500

@app.route('/predict', methods=['POST'])
def predict():
    if not onnx_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.get_json()
        
        # Handle base64 encoded image
        if 'image' in data:
            image_data = data['image']
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Preprocess image
            input_tensor = transform(image).unsqueeze(0).numpy()
            
        elif 'input' in data:
            # Direct numpy array input
            input_tensor = np.array(data['input'])
            
        else:
            return jsonify({"error": "No valid input found. Provide 'image' or 'input' field"}), 400
        
        # Run inference
        output = onnx_model.predict(input_tensor)
        
        # Apply softmax to get probabilities
        probabilities = softmax(output)
        predicted_class = int(np.argmax(probabilities, axis=1)[0])
        confidence = float(probabilities[0][predicted_class])
        
        return jsonify({
            "predicted_class": predicted_class,
            "confidence": confidence,
            "probabilities": probabilities[0].tolist()
        })
        
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

def softmax(x):
    """Apply softmax to convert logits to probabilities"""
    exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return exp_x / np.sum(exp_x, axis=1, keepdims=True)
    
    print(f"Raw output: {output}")
    print(f"Output shape: {output.shape}")
    
if __name__ == '__main__':
    print("Starting ONNX Inference Service on port 5001...")
    try:
        app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {e}")