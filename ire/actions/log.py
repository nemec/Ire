class Log(object):
  displayname = "Log"
  form_display = [("text", "with message", "Text to write to the log file."),
                  ("destination", "to", "File path to append to.")]

  @staticmethod
  def trigger(**kwargs):
    with open(kwargs["destination"], 'a') as f:
      f.write(kwargs["text"] + '\n')
