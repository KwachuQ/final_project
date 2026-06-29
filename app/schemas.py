from pydantic import BaseModel, model_validator


class UserRegister(BaseModel):
    username: str
    password: str
    password_repeat: str

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegister":
        if self.password != self.password_repeat:
            raise ValueError("passwords do not match")
        return self


class UserResponse(BaseModel):
    user_id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ErrorResponse(BaseModel):
    detail: str