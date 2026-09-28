#!/usr/bin/env python
# Convert PNG to ICO format
from PIL import Image
import os

# Load the PNG image
png_path = 'd:\\Project\\POS\\icon.png'
ico_path = 'd:\\Project\\POS\\icon.ico'

try:
    # Open the image
    img = Image.open(png_path)
    
    # Convert to RGB if it has alpha channel (PNG to ICO conversion)
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Resize to standard icon sizes and save as ICO
    # ICO format supports multiple sizes, we'll create a multi-resolution icon
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Create resized versions
    icon_images = []
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Save as ICO with all sizes
    img.save(ico_path, format='ICO', sizes=sizes)
    
    print(f"✅ Successfully converted {png_path} to {ico_path}")
    print("Icon sizes included: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256")
    
except FileNotFoundError:
    print(f"❌ Error: File not found - {png_path}")
    print(f"Make sure 'icon.png' exists in d:\\Project\\POS\\")
except Exception as e:
    print(f"❌ Error: {str(e)}")
