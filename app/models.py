"""
Models for request bodies, responses, and storage.
Some data has multiple models suited for different usage.
E.g. UserRec includes hashed password for storage but User omits it for response.
Application structure is simplified for this project.
All models are contained in this file.
Settings are case insensitive securely captured from the environment.
"""
from typing import Union, List
from pydantic import BaseModel
from pydantic import BaseSettings


class JWTSettings(BaseSettings):
    jwt_signature: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


class RedisSettings(BaseSettings):
    redis_host: str
    redis_port: int
    redis_password: str
    redis_user: str = 'default'


class Token(BaseModel):
    """oAuth2 compliant access token returned for login response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data stored in oAuth2 JWT access token, currently only username (email) but could include more."""
    username: Union[str, None] = None


class User(BaseModel):
    """User response model does not contain password hash."""
    uuid: str = ""
    email: str = ""
    active: int = 1  # Using bool is awkward in Redis HMSET
    name: str = ""


class UserRec(User):
    """Full User model for storage including password hash."""
    hashed: str


class UserNew(User):
    """User model including password for registration requests."""
    plain: str


class Question(BaseModel):
    """Question UUID combines the owner's user UUID with it's own unique string."""
    uuid: str = ""  # "<owner>-<uuid>" UUID
    owner: str = ""
    text: str = ""
    answers: List[str] = []  # Ordered list of possible answer texts
    correct: List[bool] = []  # True/1 if corresponding answer is a correct answer


class Quiz(BaseModel):
    """Quiz UUID is a combination of the owner's user UUID and it's own unique string."""
    uuid: str = ""  # "<owner>-<uuid>" UUID
    owner: str = ""
    published: bool = False
    title: str = ""
    questions: List[str] = []  # Uuids of questions assigned to this quiz


class Solution(BaseModel):
    """Solution UUIDs combine the UUID of the user submitting the solution with the combined quiz UUID."""
    uuid: str = ""  # "<user>-<owner>-<quiz>" UUID
    user: str = ""  # "<user>" UUID
    quiz: str = ""  # "<owner>-<quiz>" UUID
    title: str = ""
    questions: List[str] = []  # Text of questions from the quiz (available after quiz deleted)
    scores: List[int] = []  # Percentage score per question
    score: int = 0  # Overall average percentage score for all questions in quiz


class SolutionRec(Solution):
    """Request body contains answers that are not returned in the response."""
    answers: List[List[bool]]  # For each Question in the Quiz there is a List[bool] of answers
