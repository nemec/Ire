

__all__ = ['Move', 'Shell', 'Alert']


class Field(object):
  pass


# Represents a type of pattern
# Simple (glob)
# Complex (regex)
class PatternField(object):
  pass


class Action(object):
  form_display = ()
  
  @staticmethod
  def trigger(self, *args, **kwargs):
    raise NotImplementedError("Must create an action in subclass.")
    
  """def serialize():
    return {}
  """


class Move(Action):
  source = str
  destination = str
  
  form_display = (("source", "Path of file to move."),
                  ("destination", "Destination path and filename."))
  
  @staticmethod
  def trigger(*args, **kwargs):
    shutil.move(kwargs["source"], kwargs["destination"])


class Alert(Action):
  text = str
  
  form_display = (("text", "Message to display in the alert."),
                  )
  
  @staticmethod
  def trigger(*args, **kwargs):
    print kwargs["text"]


class Shell(Action):
  command = str
  
  form_display = (("command", "Full text of command to execute."),
                  )
  
  @staticmethod
  def trigger(*args, **kwargs):
    import sys
    if sys.version_info.major < 3:
      # Unicode strings don't work in Popen in 2.x, encode to ascii
      kwargs["command"] = kwargs["command"].encode('ascii', 'ignore')
      
    import subprocess, shlex
    p = subprocess.Popen(shlex.split(kwargs["command"]))
