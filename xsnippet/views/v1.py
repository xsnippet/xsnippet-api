from flask import abort
from flask import Blueprint
from flask.views import MethodView


api = Blueprint('v1', __name__)


class SnippetAPI(MethodView):
    def get(self, snippet_id):
        abort(501)

    def post(self):
        abort(501)

    def delete(self, snippet_id):
        abort(501)

    def put(self, snippet_id):
        abort(501)


snippet_view = SnippetAPI.as_view('snippet_api')
api.add_url_rule('/snippets/',
                 defaults={'snippet_id': None},
                 view_func=snippet_view,
                 methods=['GET'])
api.add_url_rule('/snippets/',
                 view_func=snippet_view,
                 methods=['POST'])
api.add_url_rule('/snippets/<int:snippet_id>',
                 view_func=snippet_view,
                 methods=['GET', 'PUT', 'DELETE'])
