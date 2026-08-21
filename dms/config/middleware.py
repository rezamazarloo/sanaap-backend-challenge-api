from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = await _user_from_token(_token_from_scope(scope))
        return await self.app(scope, receive, send)


def _token_from_scope(scope):
    header_token = _token_from_authorization_header(scope)
    if header_token:
        return header_token

    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string)
    values = query_params.get("token")
    return values[0] if values else None


def _token_from_authorization_header(scope):
    headers = dict(scope.get("headers") or [])
    authorization = headers.get(b"authorization")
    if not authorization:
        return None

    try:
        keyword, token = authorization.decode("utf-8").split(None, 1)
    except ValueError:
        return None

    if keyword.lower() != "token":
        return None
    return token


@database_sync_to_async
def _user_from_token(token_key):
    if not token_key:
        return AnonymousUser()

    try:
        token = Token.objects.select_related("user").get(key=token_key)
    except Token.DoesNotExist:
        return AnonymousUser()

    return token.user

