from spin_sdk.http import IncomingHandler, Request, Response
import json

class IncomingHandler(IncomingHandler):
    def handle_request(self, request: Request) -> Response:
        try:
            body = request.body
            if body:
                data = json.loads(body.decode("utf-8"))
                message = data.get("message", "")
            else:
                message = ""

            response_data = {
                "status": "success",
                "output": message
            }

            return Response(
                200,
                {"content-type": "application/json"},
                bytes(json.dumps(response_data, ensure_ascii=False), "utf-8")
            )
        except Exception as e:
            error_response = {
                "status": "error",
                "message": str(e)
            }
            return Response(
                400,
                {"content-type": "application/json"},
                bytes(json.dumps(error_response), "utf-8")
            )
