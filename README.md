# Quizzly Backend

Django REST API that turns a YouTube video into a multiple choice quiz: the audio is
downloaded with yt-dlp, transcribed with Whisper and handed to Gemini, which returns ten
questions. Quizzes belong to the user who created them.

## Requirements

- Python 3.13
- [ffmpeg](https://ffmpeg.org/) on the PATH (Whisper needs it to read the audio)
- A Gemini API key

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own values:

| Key | Meaning |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key, generate with the command in `.env.example` |
| `DEBUG` | `True` during development |
| `ALLOWED_HOSTS` | Comma separated host names |
| `CORS_ALLOWED_ORIGINS` | Where the frontend runs, with scheme and port |
| `GEMINI_API_KEY` | API key for the quiz generation |

Then create the database and start the server:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Authentication

JWT via httpOnly cookies. `login` sets `access_token` and `refresh_token`; the tokens are
never part of the response body. Every following request is authenticated from those
cookies, so no `Authorization` header is needed.

## Endpoints

All routes are prefixed with `/api/`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `register/` | Create a new user |
| `POST` | `login/` | Log in, sets the JWT cookies |
| `POST` | `logout/` | Log out, blacklists the refresh token and clears the cookies |
| `POST` | `token/refresh/` | New access token from the refresh cookie |
| `GET` | `quizzes/` | All quizzes of the logged in user |
| `POST` | `quizzes/` | Create a quiz from a YouTube URL |
| `GET` | `quizzes/<id>/` | A single quiz with its questions |
| `PATCH` | `quizzes/<id>/` | Change title and description |
| `DELETE` | `quizzes/<id>/` | Delete the quiz and its questions |

The `quizzes/` routes require a logged in user, and the detail routes only work on your own
quizzes.

### Creating a quiz

```json
POST /api/quizzes/
{ "url": "https://www.youtube.com/watch?v=..." }
```

The response is the stored quiz with ten questions. The request runs download,
transcription and generation in one go and takes a while.

## Tests

```powershell
python manage.py test auth_app quizzly_app
```

## Project layout

```
auth_app/          registration, login, logout, token refresh
  api/             serializers, views, urls, cookie authentication
  tests/
quizzly_app/       quizzes and questions
  api/             serializers, views, urls, permissions
  services/        yt-dlp download, Whisper transcription, Gemini generation
  tests/
core/              settings and root urlconf
```
