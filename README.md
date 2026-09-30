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
| `DEBUG` | `True` during development, see [Running in production](#running-in-production) |
| `ALLOWED_HOSTS` | Comma separated host names |
| `CORS_ALLOWED_ORIGINS` | Where the frontend runs, with scheme and port |
| `GEMINI_API_KEY` | API key for the quiz generation |

Lists are comma separated, without spaces and without a trailing comma.

Generate a secret key locally, with the venv active:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

On a server without Django, the standard library is enough:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Docker Compose reads `$` in the `.env` as the start of a variable and silently drops what
follows. Django's generator can produce `$`, so either wrap the key in single quotes or use
the second command, whose output only contains letters, digits, `-` and `_`.

Then create the database and start the server:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Authentication and security

JWT via httpOnly cookies. `login` sets `access_token` and `refresh_token`; the tokens are
never part of the response body. Every following request is authenticated from those
cookies, so no `Authorization` header is needed.

- **Lifetimes.** Access tokens live 30 minutes, refresh tokens 1 day. The cookies expire
  together with their token. `token/refresh/` issues a new access token from the refresh
  cookie, `logout/` blacklists the refresh token and clears both cookies. Logging out only
  needs the refresh cookie, so it still works after the access token has expired.
- **CSRF.** Cookies are sent by the browser on its own, so the cookies carry
  `SameSite=Lax`. Browsers then leave them out of cross-site POST, PATCH and DELETE
  requests. This holds as long as the frontend and the API are served from the same site
  (same registrable domain, the port does not matter). On separate domains the cookies
  would need `SameSite=None` plus a CSRF token, which this project does not implement.
- **Cookie flags.** `httponly` and `secure` always. Browsers treat `localhost`
  as a secure context, so the cookies also work in development without TLS.
- **Passwords** only have to match their confirmation. Django's password validators are
  deliberately not applied on registration; the frontend owns the password rules.
- **Rate limits.** `register/` and `login/` allow 10 requests per minute per IP address.
  Creating a quiz is limited to 5 per hour per user. Exceeding a limit returns `429`.
  The endpoint documentation lists no limits; these are a deliberate addition, because
  every quiz costs minutes of CPU and Gemini quota.
- **Ownership.** The list only contains the quizzes of the logged in user. A detail route
  of a quiz that belongs to someone else answers `403`, an unknown id `404`.

## Endpoints

All routes are prefixed with `/api/`.

| Method | Path | Description | Errors |
| --- | --- | --- | --- |
| `POST` | `register/` | Create a new user | `400` invalid or duplicate data, weak password · `429` |
| `POST` | `login/` | Log in, sets the JWT cookies | `401` wrong credentials · `429` |
| `POST` | `logout/` | Blacklist the refresh token, clear the cookies | `401` refresh cookie missing, invalid or blacklisted |
| `POST` | `token/refresh/` | New access token from the refresh cookie | `401` refresh cookie missing, invalid or blacklisted |
| `GET` | `quizzes/` | All quizzes of the logged in user | `401` |
| `POST` | `quizzes/` | Create a quiz from a YouTube URL | see below |
| `GET` | `quizzes/<id>/` | A single quiz with its questions | `401` · `403` foreign quiz · `404` unknown id |
| `PATCH` | `quizzes/<id>/` | Change title and description | `401` · `403` · `404` |
| `DELETE` | `quizzes/<id>/` | Delete the quiz and its questions | `401` · `403` · `404` |

`PUT` is not offered on the detail route (`405`). Fields other than `title` and
`description` are ignored on `PATCH`.

### Creating a quiz

```json
POST /api/quizzes/
{ "url": "https://www.youtube.com/watch?v=..." }
```

The response is the stored quiz with ten questions. The request runs download,
transcription and generation in one go and takes a while.

| Status | Meaning |
| --- | --- |
| `201` | Quiz stored |
| `400` | URL is not a `https://www.youtube.com/watch?v=` link, the video is longer than 20 minutes, or it could not be downloaded |
| `429` | More than 5 quizzes in the last hour |
| `502` | Transcription or generation failed, try again later |

Limits that are intentional: only the desktop watch URL is accepted (`youtu.be` and
`m.youtube.com` are rejected), videos are capped at 20 minutes, and the request is
synchronous. Downloaded audio is deleted right after the transcription. The Whisper model
is loaded once per process and kept in memory.

## Tests

```powershell
python manage.py test auth_app quizzly_app
```

The suite covers registration, login, cookie authentication, refresh, logout and the
blacklist, as well as list, create, retrieve, update and delete of quizzes including
ownership, throttling and the error paths. The download, transcription and generation are
replaced by mocks, so the tests need neither network, ffmpeg nor a Gemini key. They do
need a `.env`, because the settings refuse to start without one.

## Running in production

The repository is configured for development. Before deploying:

- Set `DEBUG=False`.
- Run `python manage.py check --deploy` and set what it lists: `SECURE_SSL_REDIRECT`,
  `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `CSRF_TRUSTED_ORIGINS`, and `SECURE_PROXY_SSL_HEADER` behind a reverse proxy.
- Configure `STATIC_ROOT` and run `collectstatic`, otherwise the admin has no styles.
- Replace SQLite and the console email backend if needed and add a `LOGGING` config;
  errors of the quiz pipeline are logged under `quizzly_app.api.views`.
- Serve with a WSGI server such as gunicorn or waitress instead of `runserver`.
- Run `python manage.py flushexpiredtokens` regularly, the blacklist table grows otherwise.

Known limitation: a quiz is generated inside the request, which can take minutes. A job
queue with a status endpoint would be the next step for real traffic.

## Project layout

```
auth_app/          registration, login, logout, token refresh
  api/             serializers, views, urls, cookie authentication, throttles
  tests/
quizzly_app/       quizzes and questions
  api/             serializers, views, urls, permissions, throttles
  services/        yt-dlp download, Whisper transcription, Gemini generation
  tests/
core/              settings and root urlconf
LICENSE            MIT
```

## License

MIT, see [LICENSE](LICENSE).
