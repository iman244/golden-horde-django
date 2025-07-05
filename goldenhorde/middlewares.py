
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