from app.auth.models import RefreshToken
from sqlalchemy.orm import Session
from datetime import datetime, timezone
class AuthRepository:

    def create_refresh_token(
        self,
        db: Session,
        refresh_token: RefreshToken,
    ) -> RefreshToken:

        db.add(refresh_token)

        db.flush()

        db.refresh(refresh_token)

        return refresh_token
    
    def get_refresh_token_by_hash(
    self,
    db: Session,
    token_hash: str,
) -> RefreshToken | None:
        return (
    db.query(RefreshToken)
    .filter(
        RefreshToken.token_hash == token_hash
    )
    .first()
)

    def revoke_refresh_token(
    self,
    refresh_token: RefreshToken,
) -> None:
        refresh_token.revoked_at = datetime.now(timezone.utc)