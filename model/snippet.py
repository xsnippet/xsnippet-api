from google.appengine.ext import db

class Snippet(db.Model):
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.TextProperty()
    language = db.StringProperty()
    tags = db.StringListProperty()

    # language name to highlight.js name mapping
    languages = {
            "C": "cpp",
            "C++": "cpp",
            "C#": "cs",
            "Java": "java",
            "Python": "python",
            "Bash": "bash",
            "HTML": "xml",
            "XML": "xml",
            "CSS": "css",
            "JavaScript": "javascript",
            "PHP": "php",
            "SQL": "sql",
            "Ruby": "ruby",
            "1C": "1c",
            "Apache": "apache",
            "CMake": "cmake",
            "Delphi": "delphi",
            "diff": "diff",
            "Django": "django",
            "DOS": "dos",
            "Erlang": "erlang",
            "Go": "go",
            "Haskell": "haskell",
            "ini": "ini",
            "Lisp": "lisp",
            "Lua": "lua",
            "Nginx": "nginx",
            "Objective-C": "objectivec",
            "Perl": "perl",
            "Scala": "scala",
            "Smalltalk": "smalltalk",
            "TeX": "tex",
            "VBScript": "vbscript",
            "VHDL": "vhdl",
            "Text": "no-highlight",
            "Autodetection": "" ,
    }

    # language name to filename extension mapping 
    extensions = {
            "C": ".c",
            "C++": ".cpp",
            "C#": ".cs",
            "Java": ".java",
            "Python": ".py",
            "Bash": ".sh",
            "HTML": ".html",
            "XML": ".xml",
            "CSS": ".css",
            "JavaScript": ".js",
            "PHP": ".php",
            "SQL": ".sql",
            "Ruby": ".rb",
            "Apache": ".conf",
            "CMake": ".cmake",
            "Delphi": ".pas",
            "diff": ".diff",
            "Django": ".html",
            "DOS": ".bat",
            "Erlang": ".erl",
            "Go": ".go",
            "Haskell": ".hs",
            "ini": ".ini",
            "Lisp": ".lisp",
            "Lua": ".lua",
            "Nginx": ".conf",
            "Objective-C": ".m",
            "Perl": ".pl",
            "Scala": ".scale",
            "Smalltalk": ".sm",
            "TeX": ".tex",
            "VBScript": ".vbs",
            "VHDL": ".vhdl",
            "Text": ".txt",
            "Autodetection": ".txt"
    }
