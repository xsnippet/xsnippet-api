from google.appengine.ext import db

class Snippet(db.Model):
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.TextProperty()
    language = db.StringProperty()
    tags = db.StringListProperty()

