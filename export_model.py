import torch
from model_arc import EfficientNetClassifier

def export_model():
    # Load your trained model
    model = EfficientNetClassifier(num_classes=2)
    model.load_state_dict(torch.load('models/All_nz_regions_model.pth', map_location='cpu'))
    
    # Export to ONNX
    onnx_path = 'models/All_nz_regions_model.onnx'
    model.export_to_onnx(onnx_path)
    
    print("Model successfully exported to ONNX!")

if __name__ == "__main__":
    export_model()