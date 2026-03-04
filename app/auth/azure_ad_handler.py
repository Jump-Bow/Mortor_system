"""
Azure AD (Microsoft Entra ID) Authentication Handler
使用 MSAL 進行 OAuth 2.0 Authorization Code Flow 認證

核心認知：Azure AD 僅負責驗證身份。
AD 帳號 = hr_account.id，認證成功後直接查詢資料庫中對應的使用者。
"""
import msal
from flask import current_app
from typing import Optional, Dict, Tuple


class AzureADHandler:
    """Azure AD 認證處理器，封裝 MSAL 邏輯"""

    @staticmethod
    def _get_msal_app() -> msal.ConfidentialClientApplication:
        """
        建立 MSAL ConfidentialClientApplication 實例

        Returns:
            MSAL 應用程式實例
        """
        return msal.ConfidentialClientApplication(
            client_id=current_app.config['AZURE_CLIENT_ID'],
            client_credential=current_app.config['AZURE_CLIENT_SECRET'],
            authority=current_app.config['AZURE_AUTHORITY'],
        )

    @staticmethod
    def is_enabled() -> bool:
        """檢查 Azure AD 認證是否已啟用"""
        return current_app.config.get('USE_AZURE_AD', False)

    @staticmethod
    def get_auth_url() -> Tuple[Optional[str], Optional[str]]:
        """
        產生 Azure AD 授權 URL

        Returns:
            Tuple of (auth_url, error_message)
            - auth_url: Azure AD 登入頁面 URL
            - error_message: 錯誤訊息 (成功時為 None)
        """
        try:
            app = AzureADHandler._get_msal_app()
            result = app.get_authorization_request_url(
                scopes=current_app.config['AZURE_SCOPE'],
                redirect_uri=current_app.config['AZURE_REDIRECT_URI'],
            )
            return result, None
        except Exception as e:
            current_app.logger.error(f'Azure AD get_auth_url error: {str(e)}')
            return None, f'無法產生 Azure AD 授權 URL: {str(e)}'

    @staticmethod
    def acquire_token_by_code(code: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        使用 authorization code 換取 token

        Args:
            code: Azure AD 回傳的 authorization code

        Returns:
            Tuple of (result, error_message)
            - result: MSAL 回傳的 token 結果 (含 id_token_claims)
            - error_message: 錯誤訊息 (成功時為 None)
        """
        try:
            app = AzureADHandler._get_msal_app()
            result = app.acquire_token_by_authorization_code(
                code=code,
                scopes=current_app.config['AZURE_SCOPE'],
                redirect_uri=current_app.config['AZURE_REDIRECT_URI'],
            )

            if 'error' in result:
                error_desc = result.get('error_description', result.get('error', '未知錯誤'))
                current_app.logger.error(f'Azure AD token acquisition failed: {error_desc}')
                return None, f'Azure AD 認證失敗: {error_desc}'

            return result, None

        except Exception as e:
            current_app.logger.error(f'Azure AD acquire_token error: {str(e)}')
            return None, f'Azure AD Token 交換失敗: {str(e)}'

    @staticmethod
    def get_username_from_token(result: Dict) -> Optional[str]:
        """
        從 MSAL token 結果中提取使用者帳號

        優先順序:
        1. preferred_username (通常為 AD 帳號，如 user@domain.com)
        2. 取 @ 前面的部分作為帳號 (如 user)

        Args:
            result: MSAL acquire_token 回傳的結果

        Returns:
            使用者帳號 (對應 hr_account.id)，或 None
        """
        claims = result.get('id_token_claims', {})

        # 取得 preferred_username
        preferred_username = claims.get('preferred_username', '')

        if not preferred_username:
            current_app.logger.warning('Azure AD token 中未包含 preferred_username')
            return None

        # 取 @ 前面的部分作為帳號 (如 user@chimei.com → user)
        username = preferred_username.split('@')[0] if '@' in preferred_username else preferred_username

        current_app.logger.info(f'Azure AD 認證成功, preferred_username={preferred_username}, mapped_id={username}')
        return username

    @staticmethod
    def get_user_info_from_token(result: Dict) -> Dict:
        """
        從 MSAL token 結果中提取使用者基本資訊

        Args:
            result: MSAL acquire_token 回傳的結果

        Returns:
            包含 name, email 等資訊的字典
        """
        claims = result.get('id_token_claims', {})
        return {
            'name': claims.get('name', ''),
            'email': claims.get('preferred_username', ''),
            'oid': claims.get('oid', ''),
        }
