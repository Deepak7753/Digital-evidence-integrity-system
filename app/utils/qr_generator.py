import os
import qrcode
from flask import current_app, request

def generate_evidence_qr(evidence_hash: str) -> str:
    """
    Generate QR code image linked to the verification route.
    Saves image under app/static/qr/<hash>.png and returns the relative static URL.
    """
    # Create target URL for the public verification page
    # Use configurable base URL if set, otherwise fall back to request host URL.
    base_url = current_app.config.get('BASE_URL')
    if not base_url:
        # request.host_url includes scheme and trailing slash
        base_url = request.host_url.rstrip('/')
    verify_url = f"{base_url}/evidence/verify/{evidence_hash}"
    
    # Configure QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    
    # Create image using Pillow
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save path setup
    filename = f"{evidence_hash}.png"
    save_dir = os.path.join(current_app.static_folder, 'qr')
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, filename)
    img.save(save_path)
    
    # Return relative URL for Jinja templates
    return f"qr/{filename}"
