from PIL import Image
import torch
import clip
from torchvision import transforms
import numpy as np

# Carrega o modelo CLIP
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def image_to_vector(image_path):
    """Converte uma imagem em um vetor usando CLIP."""
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
    return image_features.cpu().numpy().tolist()[0]  # Retorna o vetor como lista
