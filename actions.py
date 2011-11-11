import shutil

__all__ = ['Move', 'Log', 'Shell', 'Alert']


class Action(object):
  form_display = ()

  @staticmethod
  def trigger(**kwargs):
    raise NotImplementedError("Must create an action in subclass.")
  
  # Should not be serialized because actions are "static classes"
  """@staticmethod
  def serialize(obj, **kwargs):
    args = {}
    for item, desc in obj.form_display:
      if item in kwargs:
        args[item] = kwargs[item]
    return {"type": obj.__name__,
            "args": args}
  """
  

class Move(Action):
  displayname = "Move file"
  form_display = (("destination", "to", "Destination path and filename."), )
  
  @staticmethod
  def trigger(**kwargs):
    shutil.move(kwargs["_path"], kwargs["destination"])


class Log(Action):
  displayname = "Log"
  form_display = (("text", "with message", "Text to write to the log file."),
                  ("destination", "to", "File path to append to."))

  @staticmethod
  def trigger(**kwargs):
    with open(kwargs["destination"], 'a') as f:
      f.write(kwargs["text"] + '\n')


class Alert(Action):
  displayname = "Send alert"
  form_display = (("text", "with message", "Message to display in the alert."),
                  )
  
  @staticmethod
  def trigger(**kwargs):
    print kwargs["text"]


class Shell(Action):
  displayname = "Execute"
  form_display = (("command", "the shell command",
                              "Full text of command to execute."),
                  )
  
  @staticmethod
  def trigger(**kwargs):
    import sys
    if sys.version_info.major < 3:
      # Unicode strings don't work in Popen in 2.x, encode to ascii
      kwargs["command"] = kwargs["command"].encode('ascii', 'ignore')
      
    import subprocess, shlex
    p = subprocess.Popen(shlex.split(kwargs["command"]))
