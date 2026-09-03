import torch
import torch.nn as nn
from torchvision import models
import onnx
import onnxruntime as ort
import numpy as np

class EfficientNetClassifier(nn.Module):
    """EfficientNet-B3 with custom head"""
    def __init__(self, num_classes=2, pretrained=True):
        super(EfficientNetClassifier, self).__init__()
        if pretrained:
            self.backbone = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
        else:
            self.backbone = models.efficientnet_b3(weights=None)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)
    
    def export_to_onnx(self, onnx_path, input_shape=(1, 3, 128, 128)):
        """Export the model to ONNX format"""
        self.eval()
        dummy_input = torch.randn(input_shape)
        
        # Export with opset 18 to avoid conversion issues
        with torch.no_grad():
            torch.onnx.export(
                self,
                dummy_input,
                onnx_path,
                export_params=True,
                opset_version=18,  # Use opset 18 to match modern operators
                do_constant_folding=False,  # Disable constant folding to avoid conversion issues
                input_names=['input'],
                output_names=['output'],
                dynamic_axes=None,
                verbose=False
            )
        
        print(f"✓ Model successfully exported to {onnx_path}")
        
        # Test the exported model
        try:
            import onnxruntime as ort
            # Use basic provider to avoid version conflicts
            session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
            test_input = dummy_input.numpy()
            result = session.run(None, {session.get_inputs()[0].name: test_input})
            print(f"✓ Model validation passed - Output shape: {result[0].shape}")
        except Exception as e:
            print(f"⚠ Warning: Model validation failed: {e}")
            print(f"  Model exported but validation could not complete")

class ONNXInference:
    """ONNX inference class"""
    def __init__(self, onnx_path):
        self.session = ort.InferenceSession(onnx_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
    
    def predict(self, input_tensor):
        """Run inference on input tensor"""
        if isinstance(input_tensor, torch.Tensor):
            input_tensor = input_tensor.numpy()
        
        result = self.session.run(
            [self.output_name],
            {self.input_name: input_tensor}
        )
        return result[0]