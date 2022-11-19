.. set ft=rst spell

================
Quiz Builder App
================

-----------
31 Aug 2022
-----------

Application Setup
=================

Example ASGI application running on Flask and Redis.

Environment
-----------

Configure JOSE/JWT tokens and Redis database in the environment::

    export JWT_SIGNATURE='***************************'
    export JWT_ALGORITHM='HS256'
    export JWT_EXPIRE_MINUTES='720'

    export REDIS_HOST='***********.***********.ec2.cloud.redislabs.com'
    export REDIS_PORT='19008'
    export REDIS_USER='default'
    export REDIS_PASSWORD='********************************'

Run Application
---------------

To run the application with ``uvicorn`` use::

    cd app
    uvicorn main:app --reload

Code Quality
------------

Flake8 is provided in ``requirements.txt``.
Run against the ``app`` directory to check code is clean::

    flake8 app

Unit Tests
----------

Unit testing is run with ``pytest``.
Currently unit tests rely on a test Redis being available,
and the environment needs to be set up in when running tests::

    cd app
    pytest

TO DO:

- Implement mock Redis to eliminate dependency on Redis test data
- Probably best to implement class-based tests
- More tests and coverage needed

Requirements and Functionality
==============================

Authentication and Authorisation
--------------------------------

- Users can register and sign in with email / password
- All API calls are authenticated, therefore all users are authenticated
- Authentication is oAuth2 compliant using advanced JOSE/JWT access tokens
- Access tokens pack username (email) and expiry time
- oAuth2 is useful for different scenarios including separate auth server
- Access tokens can be generated with different expiries as required
- JOSE/JWT tokens support scopes for varying authorisation if required in future

- All endpoints are authenticated
- All operations are available to all users
- Some operations are only available for quizzes or questions created by the authenticated user

Quizzes and Questions
---------------------

To create a quiz, a user creates questions, and then creates a quiz referencing some questions.

- A quiz has a title, 1 - 10 questions, and can be published or unpublished
- Published quizzes can no longer be modified and can only be deleted

- Questions have question text and 1 - 5 possible answers
- Questions can have a single correct answer or multiple correct answers
- All Questions with a single correct answer are treated as a single answer question
- Questions are tracked as to their participation in published and unpublished quizzes
- Questions in unpublished quizzes can be modified but not deleted
- Questions in published quizzes cannot be modified or deleted

Scoring Quizzes
---------------

:Correct answer:   1 point
:Skipped question: 0 points
:Incorrect answer: -1 points

- It's not possible to submit multiple answers to a question with only one answer
- Multiple answer questions count fractions of a point per correct / incorrect answer

Solutions
---------

- Quizzes can be taken by other users once published
- When taken by owner quizzes are scored, and the score returned, but not saved
- Users can take any published quiz, but can only take a quiz once
- Users can see what they scored for each question and the quiz but not the answers
- When taken by others the quiz is scored and the scores stored in a solution
- The solution records the result even after the quiz is deleted

