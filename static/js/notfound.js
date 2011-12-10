var terminal = {
  cmdIdx: 0,
  currentCommand: null,
  pos: 0,
  prompt: "<b>error@xsnippet:/$</b> ",
  screen: null,
  init: function(obj) {
    terminal.screen = obj;
    terminal.nextCommand();
  },

  nextCommand: function() {
    if (terminal.cmdIdx < msg.length) {
      terminal.startCommand();
    }
  },

  startCommand: function() {
    var pauseInterval = 0;
    terminal.currentCommand = msg[terminal.cmdIdx];
    node = document.createElement("span");
    node.innerHTML = terminal.prompt;
    terminal.screen.append(node);
    terminal.typeCommand();
  },

  typeCommand: function() {
    var pauseInterval = 100;
    var node;

    if (terminal.currentCommand.cmd && (terminal.pos < terminal.currentCommand.cmd.length)) {
      var ch = terminal.currentCommand.cmd.substr(terminal.pos, 1);
      terminal.pos++;

      switch (ch.charCodeAt(0)) {
        case 125: { node = document.createElement("br"); break; }
        case 94: { pauseInterval = 1000; break; }
        default: { node = document.createTextNode(ch); break; }
      }

      if (node != null) terminal.screen.append(node);
      $("#cursor").remove().appendTo($(terminal.screen));

      if (pauseInterval > 0)
        setTimeout(terminal.typeCommand, pauseInterval)
      else
        terminal.typeCommand();
    }
    else
      terminal.showResponse();
  },

  showResponse: function() {
    terminal.pos = 0;
    if (terminal.currentCommand.response != null)
      terminal.screen.append(document.createTextNode(terminal.currentCommand.response));
    if (terminal.currentCommand.br)
      terminal.screen.append(document.createElement("br"));
    $("#cursor").remove().appendTo($(terminal.screen));
    terminal.cmdIdx++;
    terminal.nextCommand();
  }
}
