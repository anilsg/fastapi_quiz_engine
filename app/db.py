"""
Storage operations supported by Redis. Test environment runs on Redis Enterprise Cloud.
Alternative back-ends can be used by replacing this module.
Redis is a fast, object-oriented data store, with persistence and high availability options.
FastAPI also supports immediate response, while Redis write is assigned to background tasks (not yet implemented).
Redis settings including Redis location and password are taken securely from the environment.
"""
import shortuuid
import redis
from models import RedisSettings, UserRec, Question, Quiz, Solution, SolutionRec


redis_settings = RedisSettings()
redis = redis.Redis(
    host=redis_settings.redis_host,
    port=redis_settings.redis_port,
    password=redis_settings.redis_password,
)


def get_user(username: str):
    """Lookup username (email) in Redis user database and return UserRec object stored as Redis hash."""
    user = redis.hgetall("user:" + username)  # dict as bytes
    if user:
        user = dict((k.decode('utf-8'), v) for k, v in user.items())
        user = UserRec.parse_obj(user)
    return user

def save_user(user: dict):
    """Create new User."""
    user = UserRec(**user)
    user.uuid = shortuuid.uuid()
    redis.hmset("user:" + user.email, user.dict())
    return user



def publish_question(uuid: str, quiz: str):
    """Record question as published in given quiz uuid."""
    redis.sadd("-".join(("published", uuid)), quiz)
    redis.srem("-".join(("unpublished", uuid)), quiz)


def unpublish_question(uuid: str, quiz: str):
    """Record question as used in unpublished quiz."""
    redis.sadd("-".join(("unpublished", uuid)), quiz)
    redis.srem("-".join(("published", uuid)), quiz)


def depublish_question(uuid: str, quiz: str):
    """Remove question from a quiz altogether."""
    redis.srem("-".join(("unpublished", uuid)), quiz)
    redis.srem("-".join(("published", uuid)), quiz)


def is_published_question(uuid: str):
    """Return True if question is published, False if only in unpublished quizzes, None if unused orphan."""
    if redis.scard("-".join(("published", uuid))):
        return True
    if redis.scard("-".join(("unpublished", uuid))):
        return False
    return None



def exists_by_uuid(prefix: str, uuid: str):
    """Return whether given prefixed UUID exists in Redis as a key."""
    return redis.exists("-".join((prefix, uuid)))


def read_by_uuid(prefix: str, uuid: str, model):
    """Retrieve given model instance from Redis JSON string at prefixed UUID."""
    json = redis.get("-".join((prefix, uuid)))
    if json:
        return model.parse_raw(json)
    return None


def save_by_uuid(prefix: str, instance):
    """Save any model instance in Redis string as JSON under prefixed UUID."""
    key = "-".join((prefix, instance.uuid))
    redis.set(key, instance.json())


def remove_by_uuid(prefix: str, uuid: str):
    """Remove any model instance Redis string under prefixed UUID."""
    key = "-".join((prefix, uuid))
    redis.delete(key)



def read_question(uuid: str):
    return read_by_uuid("question", uuid, Question)


def save_question(question: Question):
    # Update existing question
    if question.uuid:
        old_question = read_question(question.uuid)
        if not old_question:
            return None
        question.owner = old_question.owner
        question.text = question.text or old_question.text
        question.answers = question.answers or old_question.answers
        question.correct = question.correct or old_question.correct
        if len(question.answers) > len(question.correct):
            question.answers = question.answers[0:len(question.correct)]
        elif len(question.answers) < len(question.correct):
            question.correct = question.correct[0:len(question.answers)]
    # Create new question
    else:
        question.uuid = "-".join((question.owner, shortuuid.uuid()))
    # Save updated or new question
    save_by_uuid("question", question)
    return question


def remove_question(uuid: str):
    question = read_question(uuid)
    remove_by_uuid("question", uuid)
    return question


def user_questions(owner: str):
    """Return all Questions owned by UUID owner."""
    keys = redis.keys("-".join(("question", owner, "*")))
    return [Question.parse_raw(redis.get(key)) for key in keys]



def read_quiz(uuid: str):
    return read_by_uuid("quiz", uuid, Quiz)


def save_quiz(quiz: Quiz):
    # Update existing quiz
    if quiz.uuid:
        old_quiz = read_quiz(quiz.uuid)
        if not old_quiz or old_quiz.published:
            return None
        quiz.owner = old_quiz.owner
        quiz.title = quiz.title or old_quiz.title
        quiz.questions = quiz.questions or old_quiz.questions
        for uuid in set(old_quiz.questions) - set(quiz.questions):
            depublish_question(uuid, quiz.uuid)
        publish_or_unpublish_question = quiz.published and publish_question or unpublish_question
        for uuid in quiz.questions:
            publish_or_unpublish_question(uuid, quiz.uuid)
    # Create new quiz
    else:
        quiz.uuid = "-".join((quiz.owner, shortuuid.uuid()))
        quiz.published = False
        for uuid in quiz.questions:
            unpublish_question(uuid, quiz.uuid)
    # Save updated or new quiz
    save_by_uuid("quiz", quiz)
    return quiz


def remove_quiz(uuid: str):
    quiz = read_quiz(uuid)
    if not quiz:
        return None
    remove_by_uuid("quiz", uuid)
    for uuid in quiz.questions:
        depublish_question(uuid, quiz.uuid)
    return quiz


def user_quizzes(owner: str):
    """Return all Quizzes owned by UUID owner."""
    keys = redis.keys("-".join(("quiz", owner, "*")))
    return [Quiz.parse_raw(redis.get(key)) for key in keys]



def exists_solution(uuid: str):
    return exists_by_uuid("solution", uuid)


def read_solution(uuid: str):
    return read_by_uuid("solution", uuid, Solution)


def save_solution(solution: SolutionRec):
    if exists_solution(solution.uuid):
        return None
    save_by_uuid("solution", solution)
    return solution


def remove_solution(uuid: str):
    raise NotImplementedError("Removing solutions is not supported")


def user_solutions(user: str):
    """Return all Solutions recorded for all Quizzes completed by UUID user."""
    keys = redis.keys("-".join(("solution", user)) + "*")
    return [Solution.parse_raw(redis.get(key)) for key in keys]


def quiz_solutions(owner: str, quiz: str):
    """Return all Solutions recorded for UUID quiz owned by UUID owner."""
    keys = redis.keys("-".join(("solution", "*", owner, quiz)))
    return [Solution.parse_raw(redis.get(key)) for key in keys]
