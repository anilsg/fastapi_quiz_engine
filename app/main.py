"""
Example FastAPI ASGI Quizzes application with Redis storage and oAuth2 compliant JOSE/JWT access token authentication.

To run with uvicorn use::

    uvicorn main:app --reload
"""
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth import authenticate_user, create_access_token, get_current_active_user, create_new_user
from models import User, UserNew, Token, Question, Quiz, Solution, SolutionRec
from db import read_question, save_question, remove_question, is_published_question, user_questions
from db import read_quiz, save_quiz, remove_quiz, user_quizzes
from db import exists_solution, read_solution, save_solution, user_solutions, quiz_solutions


API = "/api/v1"
app = FastAPI(
    title="Example FastAPI Quizzes Project",
    description=__doc__,
    version="0.1",
    contact={
        "name": "Neil Gulati",
        "url": "https://www.linkedin.com/in/anilsgulati/",
    },
)


@app.get(API + "/")
async def get_introduction():
    """Unauthenticated response from root providing description for client."""
    return {"introduction": "Quizzes on <b>FastAPI</b>"}


@app.post("/token", response_model=Token)
async def get_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """oAuth2 compliant authentication end point can be hosted separately if required."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get(API + "/users/me", response_model=User)
async def get_users_me(current_user: User = Depends(get_current_active_user)):
    """Return user data for authenticated user."""
    return current_user


@app.post(API + "/users", response_model=User)
async def create_user(user: UserNew):
    """Registration endpoint to create new User."""
    if not user.name or not user.email or not user.plain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User name, email and password required")
    user.active = 1
    user.email = user.email.lower()
    user = create_new_user(user.dict())
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
    return user



@app.get(API + "/questions", response_model=List[Question])
async def get_user_questions(user: User = Depends(get_current_active_user)):
    """Get list of Question owned by authenticated user."""
    return user_questions(user.uuid)


@app.get(API + "/questions/{uuid}", response_model=Question)
async def get_question(uuid: str, user: User = Depends(get_current_active_user)):
    """Get specified individual Question."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only read your own Questions")
    question = read_question(uuid)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@app.post(API + "/questions", response_model=Question)
async def create_question(question: Question, user: User = Depends(get_current_active_user)):
    """Create new Question."""
    if not question.text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text is required")
    if not (len(question.answers) <= 5 or len(question.correct) <= 5):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question cannot have more than 5 answers")
    if question.correct and not any(question.correct):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question must have a correct answer")
    question.uuid = ""
    question.owner = user.uuid
    question = save_question(question)
    if not question:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Question not created")
    return question


@app.put(API + "/questions/{uuid}", response_model=Question)
async def update_question(uuid: str, question: Question, user: User = Depends(get_current_active_user)):
    """Update specified Question if not yet published."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only edit your own Questions")
    if is_published_question(uuid) is True:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update published Questions")
    if not (len(question.answers) <= 5 or len(question.correct) <= 5):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question cannot have more than 5 answers")
    if question.correct and not any(question.correct):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question must have a correct answer")
    question.uuid = uuid
    question.owner = user.uuid
    question = save_question(question)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@app.delete(API + "/questions/{uuid}", response_model=Question)
async def delete_question(uuid: str, user: User = Depends(get_current_active_user)):
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only delete your own Questions")
    if is_published_question(uuid) is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete Questions in use")
    question = remove_question(uuid)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question



@app.get(API + "/quizzes", response_model=List[Quiz])
async def get_user_quizzes(user: User = Depends(get_current_active_user)):
    """Get list of Quizzes owned by authenticated user."""
    return user_quizzes(user.uuid)


@app.get(API + "/quizzes/{uuid}/solutions", response_model=List[Solution])
async def get_quiz_solutions(uuid: str, user: User = Depends(get_current_active_user)):
    """Return all Solutions recorded for specified individual Quiz owned by authenticated user."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only view your own Quizzes")
    return quiz_solutions(user.uuid, uuid)


@app.get(API + "/quizzes/{uuid}", response_model=Quiz)
async def get_quiz(uuid: str, user: User = Depends(get_current_active_user)):
    """Return specified individual Quiz."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only view your own Quizzes")
    quiz = read_quiz(uuid)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz


@app.post(API + "/quizzes", response_model=Quiz)
async def create_quiz(quiz: Quiz, user: User = Depends(get_current_active_user)):
    """Create new Quiz."""
    if not quiz.title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz title is required")
    if len(quiz.questions) > 10:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quiz cannot have more than 10 questions")
    quiz.uuid = ""
    quiz.owner = user.uuid
    quiz = save_quiz(quiz)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Quiz not created")
    return quiz


@app.put(API + "/quizzes/{uuid}", response_model=Quiz)
async def update_quiz(uuid: str, quiz: Quiz, user: User = Depends(get_current_active_user)):
    """Update unpublished Quiz."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only edit your own Quizzes")
    old_quiz = read_quiz(uuid)
    if not old_quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    if old_quiz.published:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update published Quiz")
    if len(quiz.questions) > 10:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quiz cannot have more than 10 questions")
    if quiz.published and not (old_quiz.questions or quiz.questions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot publish Quiz with no questions")
    quiz.uuid = uuid
    quiz.owner = user.uuid
    quiz = save_quiz(quiz)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Quiz not updated")
    return quiz


@app.delete(API + "/quizzes/{uuid}", response_model=Quiz)
async def delete_quiz(uuid: str, user: User = Depends(get_current_active_user)):
    """Delete quiz and remove tracking for associated questions."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only delete your own Quizzes")
    quiz = remove_quiz(uuid)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz



def score_single_answer_question(uuid: str, correct: List[bool], answers: List[bool]):
    """Return question score scaled x 1,000 for question requiring only one answer."""
    if sum(answers) == 0:
        return 0  # Skipped question
    if sum(answers) > 1:
        detail = "Multiple answers for single answer question '{}'".format(uuid)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return answers[correct.index(True)] and 1000 or -1000


def score_multi_answer_question(uuid: str, correct: List[bool], answers: List[bool]):
    """Return question score scaled x 1,000 for question allowing multiple answers."""
    if sum(answers) == 0:
        return 0  # Skipped question
    right = sum(correct)
    wrong = len(correct) - right
    right, wrong = 1000 / right, -1000 / wrong
    return sum(q and right or wrong for q, a in zip(correct, answers) if a)


def score_question(uuid: str, correct: List[bool], answers: List[bool]):
    """Return question score scaled x 1,000 for any question."""
    if sum(correct) == 1:
        return score_single_answer_question(uuid, correct, answers)
    else:
        return score_multi_answer_question(uuid, correct, answers)


def score_quiz(quiz: Quiz, solution: SolutionRec):
    """Return scored Quiz as updated SolutionRec given Quiz and SolutionRec."""
    solution.title = quiz.title
    solution.questions = []
    solution.scores = []
    solution.score = 0

    for question, answers in zip(quiz.questions, solution.answers):  # (Question UUID, List[bool])
        question = read_question(question)  # Convert Question UUID to Question instance
        if not question:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Quiz Question missing")
        solution.questions.append(question.text)

        if len(question.correct) != len(answers):
            detail = "Wrong number of answers for question '{}'".format(question.uuid)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        score = score_question(question.uuid, question.correct, answers)  # Score x 1,000
        solution.score += score  # Score x 1,000
        solution.scores.append(round(score / 10))  # Score x 100 percentage

    solution.score = round((solution.score / len(solution.scores)) / 10)  # Overall quiz average question percentage
    return solution



@app.get(API + "/solutions", response_model=List[Solution])
async def get_user_solutions(user: User = Depends(get_current_active_user)):
    """Return all Solutions recorded for current authenticated user."""
    return user_solutions(user.uuid)


@app.get(API + "/solutions/{uuid}", response_model=Solution)
async def get_solution(uuid: str, user: User = Depends(get_current_active_user)):
    """Return individual Solution. Expects full combined solution UUID of "<user>-<owner>-<quiz>"."""
    if uuid.split("-", 1)[0] != user.uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Only view your own Solutions")
    solution = read_solution(uuid)
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")
    return solution


@app.post(API + "/solutions", response_model=Solution)
async def create_solution(solution: SolutionRec, user: User = Depends(get_current_active_user)):
    """Submit set of answers as a solution to a specified quiz. Returns recorded Solution."""
    if not solution.quiz:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz being answered is required")
    quiz = read_quiz(solution.quiz)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    if not quiz.published:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot take unpublished Quiz")
    solution.user = user.uuid
    solution.uuid = "-".join((solution.user, solution.quiz))
    if exists_solution(solution.uuid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot repeat Quiz")
    if not solution.answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answers are required")
    if len(solution.answers) != len(quiz.questions):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong number of answers")
    solution = score_quiz(quiz, solution)
    if quiz.owner != user.uuid:  # Owners solutions respond but don't save
        solution = save_solution(solution)
    if not solution:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Solution not saved")
    return solution
