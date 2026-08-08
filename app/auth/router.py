from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session

from app.auth.schemas import (
    MerchantSignupRequest,
    MerchantResponse,
    AuthenticationResponse,MerchantLoginRequest,MessageResponse, DeviceIdentifier
)
from app.auth.service import AuthService
from app.db.session import get_db
router = APIRouter(prefix="/auth", tags=["Authentication"])

auth_service = AuthService()


@router.post(
    "/signup",
    response_model=AuthenticationResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    request: MerchantSignupRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    merchant, access_token, refresh_token = auth_service.signup(
        request=request,
        db=db,
    )

    merchant_response = MerchantResponse.model_validate(merchant)

    response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=60 * 15,  # 15 minutes
            )

    response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=60 * 60 * 24 * 7,  # 7 days
            )     

    merchant_response = MerchantResponse.model_validate(merchant)

    return AuthenticationResponse(
                merchant=merchant_response,
            )

@router.post("/login",response_model=AuthenticationResponse, status_code=status.HTTP_200_OK)
def login(request:MerchantLoginRequest, response:Response, db:Session=Depends(get_db)):
        merchant, access_token, refresh_token = auth_service.login(
            request=request,
            db=db,
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 15,  # 15 minutes
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )

        merchant_response = MerchantResponse.model_validate(merchant)

        return AuthenticationResponse(
            merchant=merchant_response,
        )

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,response_model=MessageResponse
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    refresh_token = request.cookies.get("refresh_token")

    if refresh_token is None:
        return {
            "message": "Successfully logged out"
        }

    auth_service.logout(
        token=refresh_token,
        db=db,
    )

    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return MessageResponse(
            message="Logout successfully."
        )

@router.post("/refresh", status_code=status.HTTP_200_OK,response_model=MessageResponse) 
def refresh_token(request: Request, body: DeviceIdentifier,response: Response,db: Session = Depends(get_db),):
         refresh_token = request.cookies.get("refresh_token")
         if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is missing"
            )
         access_token, new_refresh_token = auth_service.refresh_token(refresh_token, db, body.device_identifier)
         response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 15,  # 15 minutes
        )

         response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )
         return MessageResponse(
        message="Session refreshed successfully."
    )
    
          
         

