import torch
from model_arc import EfficientNetClassifier

def export_model():
    # Load your improved trained model
    model = EfficientNetClassifier(num_classes=2)
    model.load_state_dict(torch.load('models/improved_All_nz_regions_model.pth', map_location='cpu'))
    
    # Export to ONNX with improved model name
    onnx_path = 'models/improved_All_nz_regions_model.onnx'
    model.export_to_onnx(onnx_path)
    
    print(f"Improved model successfully exported to {onnx_path}!")

if __name__ == "__main__":
    export_model()