from typing import Any, Dict
from app.database import SessionLocal, UserAccount


def get_user_account_info(user_id: str) -> Dict[str, Any]:
    """Consulta os dados cadastrais, plano e status da conta de um usuário no banco de dados.

    Args:
        user_id: O identificador único do cliente (ex: USR-101, USR-102, USR-103).

    Returns:
        Dicionário com nome, email, plano, status da conta, limites de API e MFA.
    """
    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.user_id == user_id).first()

        if not user:
            return {
                "found": False,
                "message": f"Usuário {user_id} não encontrado na base de dados.",
            }

        usage_percentage = round((user.api_calls_this_month / user.api_limit) * 100, 1) if user.api_limit > 0 else 0

        return {
            "found": True,
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "status": user.status,
            "mfa_enabled": user.mfa_enabled,
            "api_calls_this_month": user.api_calls_this_month,
            "api_limit": user.api_limit,
            "usage_percentage": f"{usage_percentage}%",
            "is_quota_exhausted": user.api_calls_this_month >= user.api_limit,
        }
