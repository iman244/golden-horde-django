# HeaderTokenAuthMiddleware
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
import logging

logger = logging.getLogger(__name__)

class HeaderTokenAuthMiddleware:
    """
    Middleware that authenticates a user based on a token provided either in the query string (as 'token')
    or in the 'Authorization' header (format: 'Token <your_token>').
    
    Security note: Passing tokens in the query string can expose them in logs and browser history. Prefer headers for non-browser clients.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        logger.debug(f"HeaderTokenAuthMiddleware: Start processing for path {scope.get('path', '')}")
        token_key = self.get_token_from_scope(scope)
        scope["user"] = await self.get_user(token_key)
        logger.debug(f"HeaderTokenAuthMiddleware: Finished authentication for path {scope.get('path', '')}")
        return await self.inner(scope, receive, send)

    def get_token_from_scope(self, scope):
        # Check query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token_key = query_params.get('token')
        if token_key:
            return token_key[0]
        # Check headers
        for header, value in scope.get('headers', []):
            if header == b'authorization':
                auth = value.decode()
                if auth.startswith('Token '):
                    return auth.split(' ', 1)[1]
        return None

    @database_sync_to_async
    def get_user(self, token_key):
        if not token_key:
            return AnonymousUser()
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            logger.warning(f"Failed WebSocket token authentication attempt with token: {token_key}")
            return AnonymousUser()


# QueryCountMiddleware
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class QueryCountMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Clear any existing queries before the request starts
        connection.queries.clear()

    def process_response(self, request, response):
        # After the view logic and before sending the response
        query_count = len(connection.queries)
        print(f"Number of queries for {request.path}: {query_count}")
        
        # Optionally log the SQL queries (be mindful of sensitive information in production)
        if query_count > 0:
            for query in connection.queries:
                # logger.info(f"SQL Query: {query['sql']}")
                # logger.debug(f"SQL Query: {query['sql']}")
                pass

        return response