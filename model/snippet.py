from google.appengine.ext import db

class Snippet(db.Model):
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.TextProperty()
    language = db.StringProperty()
    tags = db.StringListProperty()

    # language highlight.js name to full name mapping
    languages = {
            "cpp": "C++",
            "java": "Java",
            "cs": "C#",
            "python": "Python",
            "bash": "Bash",
            "xml": "html (xml)",
            "css": "CSS",
            "javascript": "JavaScript",
            "php": "PHP",
            "sql": "SQL",
            "ruby": "Ruby",
            "1c": "1C",
            "apache": "Apache",
            "avrasm": "AVR Assembler",
            "axapta": "Axapta",
            "cmake": "CMake",
            "delphi": "Delphi",
            "diff": "Diff",
            "django": "Django",
            "dos": "DOS .bat",
            "erlang": "Erlang",
            "erlang_repl": "Erlang REPL",
            "go": "Go",
            "haskell": "Haskell",
            "ini": "Ini",
            "lisp": "Lisp",
            "lua": "Lua",
            "mel": "MEL",
            "nginx": "Nginx",
            "objectivec": "Objective C",
            "parser3": "Parser3",
            "perl": "Perl",
            "profile": "Python profile",
            "rsl": "RenderMan RSL",
            "rib": "RenderMan RIB",
            "scala": "Scala",
            "smalltalk": "Smalltalk",
            "tex": "TeX",
            "vala": "Vala",
            "vbscript": "VBScript",
            "vhdl": "VHDL",
            "no-highlight": "Text"
    }

    # language highlight.js name to filename extension mapping 
    extensions = {
            "cpp": ".cpp",
            "java": ".java",
            "cs": ".cs",
            "python": ".py",
            "bash": ".sh",
            "xml": ".xml",
            "css": ".css",
            "javascript": ".js",
            "php": ".php",
            "sql": ".sql",
            "ruby": ".rb",
            "diff": ".diff",
            "dos": ".bat",
            "erlang": ".erl",
            "go": ".go",
            "haskell": ".hs",
            "ini": ".ini",
            "lisp": ".lisp",
            "lua": ".lua",
            "objectivec": ".m",
            "perl": ".pl",
            "scala": ".scala",
            "smalltalk": ".sm",
            "tex": ".tex",
            "vala": ".vala",
            "vbscript": ".vbs",
            "vhdl": ".hdl",
            "no-highlight": ".txt"
    }
