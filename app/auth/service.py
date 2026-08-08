from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.auth.repository import AuthRepository
from app.auth.schemas import MerchantSignupRequest
from app.auth.schemas import MerchantLoginRequest , DeviceType
from app.security.passwords import hash_password, verify_password
from app.security.jwt import create_access_token, create_refresh_token, verify_token
from app.security.hashing import hash_secret
from app.auth.models import RefreshToken

from app.merchant.models import Merchant, MerchantStatus
from app.merchant.repository import MerchantRepository
from datetime import datetime, timedelta, timezone
from app.core.settings import settings
expires_at = datetime.now(timezone.utc) + timedelta(
    days=settings.REFRESH_TOKEN_EXPIRE_DAYS
)

class AuthService:
    def __init__(self):
        self.merchant_repository = MerchantRepository()
        self.auth_repository = AuthRepository()

    def signup(self, db: Session, request: MerchantSignupRequest):
        # Step 1: Check if merchant already exists
        existing_merchant = self.merchant_repository.get_by_email(
            db=db,
            email=request.email,
        )

        if existing_merchant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Merchant with this email already exists.",
            )

        # Step 2: Hash password
        hashed_password = hash_password(request.password)

        # Step 3: Create merchant object
        merchant = Merchant(
            business_name=request.business_name,
            email=request.email,
            password_hash=hashed_password,
        )

        # Step 4: Save merchant
        merchant = self.merchant_repository.create(
            db=db,
            merchant=merchant,
        )

        # Step 5: Generate JWTs
        access_token = create_access_token(
            merchant_id=str(merchant.merchant_id),
        )

        refresh_token = create_refresh_token(
            merchant_id=str(merchant.merchant_id),
        )

        # Step 6: Store hashed refresh token
        refresh_token_record = RefreshToken(
            merchant_id=merchant.merchant_id,
            token_hash=hash_secret(refresh_token),
            device_identifier=request.device_identifier,
            expires_at =  expires_at,
        )

        self.auth_repository.create_refresh_token(
            db=db,
            refresh_token=refresh_token_record,
        )

        # Step 7: Commit transaction
        db.commit()

        # Step 8: Return tokens
        return merchant, access_token, refresh_token




    def login(self, db: Session,request:MerchantLoginRequest):
          existing_merchant = self.merchant_repository.get_by_email(
            db=db,
            email=request.email,
        )
          if not existing_merchant:
              raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Credentials.",
              ) 
          
          if not verify_password(request.password, existing_merchant.password_hash):
               raise HTTPException(
                   status_code=status.HTTP_401_UNAUTHORIZED,
                   detail="Invalid Credentials.",
               )
          if existing_merchant.merchant_status != MerchantStatus.ACTIVE:
              raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN
              )
              
          access_token = create_access_token(
                merchant_id=str(existing_merchant.merchant_id),
            )

          refresh_token = create_refresh_token(
                merchant_id=str(existing_merchant.merchant_id),
            )

            # Step 6: Store hashed refresh token

          refresh_token_record = RefreshToken(
                merchant_id=existing_merchant.merchant_id,
                token_hash=hash_secret(refresh_token),
                device_identifier=request.device_identifier,
                expires_at =  expires_at,
            )
        
          self.auth_repository.create_refresh_token(
                db=db,
                refresh_token=refresh_token_record,
            )

            # Step 7: Commit transaction
          db.commit()

            # Step 8: Return tokens
          return existing_merchant, access_token, refresh_token          

    def logout(self, token: str, db: Session) -> None:

        verify_token(token, verify_exp=False)

        token_hash = hash_secret(token)

        session = self.auth_repository.get_refresh_token_by_hash(
                 db,
             token_hash,
            )

        if session and session.revoked_at is None:
            self.auth_repository.revoke_refresh_token(session)

        db.commit()

    def refresh_token(self, token:str,db:Session,device_identifier: DeviceType):
        verify_token(token)

        token_hash = hash_secret(token)

        refresh_token_record = self.auth_repository.get_refresh_token_by_hash(
            db=db,
            token_hash=token_hash,
        )

        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        if refresh_token_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired.",
            )
        
        if refresh_token_record.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is revoked.",
            )
        
        merchant = self.merchant_repository.get_by_id(
            db=db,
            merchant_id= refresh_token_record.merchant_id,
        )

        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found.",
            )
        if merchant.merchant_status != MerchantStatus.ACTIVE:
              raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED,
           detail="Merchant account is inactive.",
          ) 

        access_token = create_access_token(
            merchant_id=str(merchant.merchant_id),
        )

        new_refresh_token = create_refresh_token(
            merchant_id=str(merchant.merchant_id),
        )
         
        # Rotate the refresh token record
        self.auth_repository.revoke_refresh_token(refresh_token_record)
     

        refresh_token_record = RefreshToken(
                        merchant_id=merchant.merchant_id,
                        token_hash=hash_secret(new_refresh_token),
                        device_identifier=device_identifier,
                        expires_at =  expires_at,
                    )

        self.auth_repository.create_refresh_token(
                    db=db,
                    refresh_token=refresh_token_record,
                )
        
        
        db.commit()

        return access_token, new_refresh_token
        