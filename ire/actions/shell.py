import sys
import shlex
import subprocess


class Shell(object):
  displayname = "Execute"
  form_display = [("command", "the shell command",
                              "Full text of command to execute."),
                  ]
  
  @staticmethod
  def trigger(**kwargs):
    if sys.version_info.major < 3:
      # Unicode strings don't work in Popen in 2.x, encode to ascii
      kwargs["command"] = kwargs["command"].encode('ascii', 'ignore')

    p = subprocess.Popen(shlex.split(kwargs["command"]))
