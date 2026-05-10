"""Sample Spin HTTP application for testing build-and-push.

This is a simple HTTP handler that responds with a JSON message.
"""

from spin_sdk.http import IncomingHandler, Request, Response


class IncomingHandler(IncomingHandler):
    """HTTP request handler for Spin application."""
    
    def handle_request(self, request: Request) -> Response:
        """Handle incoming HTTP request.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            HTTP response with JSON body
        """
        return Response(
            200,
            {"content-type": "application/json"},
            b'{"message": "Hello from Blue FaaS!", "status": "success"}'
        )
