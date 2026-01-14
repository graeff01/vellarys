"""
Serviço de Email usando Resend
"""
import logging
from typing import Optional
import resend
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configurar Resend
if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


async def send_password_reset_email(email: str, reset_token: str, user_name: Optional[str] = None) -> bool:
    """
    Envia email de recuperação de senha.
    
    Args:
        email: Email do destinatário
        reset_token: Token de reset
        user_name: Nome do usuário (opcional)
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    if not settings.resend_api_key:
        logger.warning("Resend API key não configurada. Email não enviado.")
        return False
    
    try:
        reset_link = f"{settings.frontend_url}/reset-password/{reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Recuperação de Senha</h1>
                </div>
                <div class="content">
                    <p>Olá{f", {user_name}" if user_name else ""}!</p>
                    <p>Recebemos uma solicitação para redefinir a senha da sua conta no Vellarys.</p>
                    <p>Clique no botão abaixo para criar uma nova senha:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Redefinir Senha</a>
                    </p>
                    <p><strong>Este link expira em 1 hora.</strong></p>
                    <p>Se você não solicitou esta alteração, ignore este email. Sua senha permanecerá inalterada.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Se o botão não funcionar, copie e cole este link no navegador:<br>
                        <a href="{reset_link}">{reset_link}</a>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 Vellarys - Atendimento Inteligente com IA</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": f"Vellarys <{settings.email_from}>",
            "to": [email],
            "subject": "🔐 Recuperação de Senha - Vellarys",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Email de reset enviado para {email}. ID: {response.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de reset: {e}")
        return False


async def send_welcome_email(email: str, user_name: str, temp_password: Optional[str] = None) -> bool:
    """
    Envia email de boas-vindas para novo usuário.
    
    Args:
        email: Email do destinatário
        user_name: Nome do usuário
        temp_password: Senha temporária (opcional)
        
    Returns:
        True se enviado com sucesso
    """
    if not settings.resend_api_key:
        logger.warning("Resend API key não configurada. Email não enviado.")
        return False
    
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Bem-vindo ao Vellarys!</h1>
                </div>
                <div class="content">
                    <p>Olá, {user_name}!</p>
                    <p>Sua conta foi criada com sucesso. Estamos felizes em tê-lo conosco!</p>
                    {f'<p><strong>Senha temporária:</strong> <code>{temp_password}</code></p><p>Por favor, altere sua senha após o primeiro login.</p>' if temp_password else ''}
                    <p style="text-align: center;">
                        <a href="{settings.frontend_url}/login" class="button">Acessar Dashboard</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": f"Vellarys <{settings.email_from}>",
            "to": [email],
            "subject": "🎉 Bem-vindo ao Vellarys!",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Email de boas-vindas enviado para {email}. ID: {response.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de boas-vindas: {e}")
        return False
