from fastapi import HTTPException
from starlette import status


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

ownership_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid ownership of requested resource",
)

userExists_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"User with email specified already exists",
)

incorrectCredentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)

incorrectAuth_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Your should login through SSO",
    headers={"WWW-Authenticate": "Bearer"},
)

subscriptionNotExist_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"Subscription doesn't exist!",
)

alreadySub_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"You already have active subscription",
)

notSub_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"You don't have active subscription",
)

tokenExpired_exception = HTTPException(
    status_code=403, 
    detail="Token has been expired"
)

promocodeUsed_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"Promocode is already used",
)

promocodeNotValid_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"Promocode is not valid",
)

promocodeOutdated_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST, 
    detail=f"Promocode is outdated"
)

incorrectLang_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Incorrect language specified"
)

noVideo_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="No video specified"
)

notEnoughFunds_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="You have not enough funds!",
)

bigVideo_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Video exceed maximum duration!",
)