from google.appengine.ext import db

class Snippet(db.Model):
    title = db.StringProperty()
    author = db.StringProperty()
    content = db.TextProperty()
    language = db.StringProperty()
    tags = db.StringListProperty()
    date = db.DateTimeProperty(auto_now=True)

    # language name to highlight.js name mapping
    languages = {
            "Autodetection": "",
            "C": "c",
            "C++": "cpp",
            "C#": "csharp",
            "Java": "java",
            "Python": "python",
            "Bash": "bash",
            "HTML": "html",
            "XML": "xml",
            "CSS": "css",
            "JavaScript": "js",
            "PHP": "html+php",
            "SQL": "sql",
            "Ruby": "ruby",
            "Apache": "apache",
            "CMake": "cmake",
            "Delphi": "delphi",
            "diff": "diff",
            "Django": "js+django",
            "DOS": "bat",
            "Erlang": "erlang",
            "Go": "go",
            "Haskell": "haskell",
            "ini": "ini",
            "Lisp": "cl",
            "Lua": "lua",
            "Nginx": "nginx",
            "Objective-C": "objectivec",
            "Perl": "perl",
            "Scala": "scala",
            "Smalltalk": "smalltalk",
            "TeX": "tex",
            "VBScript": "vbnet",
            "Verilog": "v",
            "VHDL": "vhdl",
            "Text": "text",
            "Nasm": "nasm",
            "Gas": "gas",
            "LLVM": "llvm"
    }

    # language name to filename extension mapping 
    extensions = {
            "Autodetection": ".txt",
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
            "Verilog": ".v",
            "VHDL": ".vhdl",
            "Text": ".txt",
            "Nasm": ".asm",
            "Gas": ".s",
            "LLVM": ".ll"
    }

    # filename extension to language name mapping
    extensions_reverse = dict([(v, k) for (k, v) in extensions.items()])
