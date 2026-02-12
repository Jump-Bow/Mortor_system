"""
Input Validators
輸入驗證工具
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime


class Validator:
    """輸入驗證類"""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> Optional[str]:
        """
        驗證必填欄位
        
        Args:
            data: 輸入資料
            required_fields: 必填欄位列表
            
        Returns:
            錯誤訊息或 None
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            return f"缺少必填欄位: {', '.join(missing_fields)}"
        
        return None
    
    @staticmethod
    def validate_string_length(value: str, min_length: int = None, max_length: int = None) -> bool:
        """驗證字串長度"""
        if not isinstance(value, str):
            return False
        
        length = len(value)
        
        if min_length and length < min_length:
            return False
        
        if max_length and length > max_length:
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """驗證電子郵件格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_date_format(date_str: str, format: str = '%Y-%m-%d') -> bool:
        """驗證日期格式"""
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_datetime_format(datetime_str: str, format: str = '%Y-%m-%dT%H:%M:%SZ') -> bool:
        """驗證日期時間格式"""
        try:
            datetime.strptime(datetime_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_numeric_range(value: float, min_value: float = None, max_value: float = None) -> bool:
        """驗證數值範圍"""
        try:
            num_value = float(value)
            
            if min_value is not None and num_value < min_value:
                return False
            
            if max_value is not None and num_value > max_value:
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_enum(value: Any, allowed_values: List[Any]) -> bool:
        """驗證枚舉值"""
        return value in allowed_values
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """清理字串 (移除特殊字元)"""
        if not isinstance(value, str):
            return ''
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|']
        cleaned = value
        for char in dangerous_chars:
            cleaned = cleaned.replace(char, '')
        
        return cleaned.strip()
    
    @staticmethod
    def validate_pagination(page: Any, page_size: Any, max_page_size: int = 1000) -> tuple:
        """
        驗證分頁參數
        
        Returns:
            Tuple of (page, page_size, error_message)
        """
        try:
            page = int(page) if page else 1
            page_size = int(page_size) if page_size else 20
            
            if page < 1:
                return 1, 20, "頁碼必須大於 0"
            
            if page_size < 1:
                return page, 20, "每頁筆數必須大於 0"
            
            if page_size > max_page_size:
                return page, max_page_size, f"每頁筆數不能超過 {max_page_size}"
            
            return page, page_size, None
            
        except (ValueError, TypeError):
            return 1, 20, "分頁參數格式錯誤"
