"""
File Upload Helpers
檔案上傳處理工具
"""
import os
import uuid
from typing import Optional, Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app
from PIL import Image
import base64
from io import BytesIO


def allowed_file(filename: str) -> bool:
    """
    檢查檔案副檔名是否允許
    
    Args:
        filename: 檔案名稱
        
    Returns:
        是否允許上傳
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一的檔案名稱
    
    Args:
        original_filename: 原始檔案名稱
        
    Returns:
        唯一的檔案名稱
    """
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
    return f"{uuid.uuid4().hex}.{ext}"


def save_uploaded_file(file: FileStorage, subfolder: str = 'photos') -> Tuple[bool, str]:
    """
    儲存上傳的檔案
    
    Args:
        file: 上傳的檔案
        subfolder: 子資料夾名稱
        
    Returns:
        Tuple of (success, file_path or error_message)
    """
    if not file or file.filename == '':
        return False, '未選擇檔案'
    
    if not allowed_file(file.filename):
        return False, '檔案格式不支援'
    
    # Generate unique filename
    filename = generate_unique_filename(file.filename)
    
    # Create subfolder if not exists
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_folder, exist_ok=True)
    
    # Full file path
    file_path = os.path.join(upload_folder, filename)
    
    try:
        # Save file
        file.save(file_path)
        
        # Optimize image if it's an image file
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            optimize_image(file_path)
        
        # Return relative path
        relative_path = os.path.join(subfolder, filename)
        return True, relative_path
        
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        return False, f'檔案儲存失敗: {str(e)}'


def save_base64_image(base64_data: str, subfolder: str = 'photos') -> Tuple[bool, str]:
    """
    儲存 Base64 編碼的圖片
    
    Args:
        base64_data: Base64 編碼的圖片資料
        subfolder: 子資料夾名稱
        
    Returns:
        Tuple of (success, file_path or error_message)
    """
    try:
        # Remove data URL prefix if exists
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        
        # Open image
        image = Image.open(BytesIO(image_data))
        
        # Generate filename
        filename = f"{uuid.uuid4().hex}.jpg"
        
        # Create subfolder
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Full file path
        file_path = os.path.join(upload_folder, filename)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Save image
        image.save(file_path, 'JPEG', quality=85, optimize=True)
        
        # Return relative path
        relative_path = os.path.join(subfolder, filename)
        return True, relative_path
        
    except Exception as e:
        current_app.logger.error(f"Error saving base64 image: {str(e)}")
        return False, f'圖片儲存失敗: {str(e)}'


def optimize_image(file_path: str, max_size: Tuple[int, int] = (1920, 1920), quality: int = 85):
    """
    優化圖片大小與品質
    
    Args:
        file_path: 檔案路徑
        max_size: 最大尺寸 (寬, 高)
        quality: JPEG 品質 (1-100)
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if larger than max_size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save with optimization
            img.save(file_path, 'JPEG', quality=quality, optimize=True)
            
    except Exception as e:
        current_app.logger.error(f"Error optimizing image: {str(e)}")


def delete_file(file_path: str) -> bool:
    """
    刪除檔案
    
    Args:
        file_path: 檔案相對路徑
        
    Returns:
        是否成功刪除
    """
    try:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {str(e)}")
        return False
