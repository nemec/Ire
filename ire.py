#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

import ire.autoplatform
import ire.eventhandler

# ~/.local/share/Trash/
# http://lxr.free-electrons.com/source/include/linux/inotify.h#L29
# https://github.com/seb-m/pyinotify/wiki/Tutorial
# http://seb-m.github.com/pyinotify/
# http://docs.python.org/library/shutil.html

# http://files.minuslab.net/doc.html
# http://www.noodlesoft.com/features.php
# http://lifehacker.com/341950/belvedere-automates-your-self+cleaning-pc
      

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=
    "Watches folders for certain files and executes actions on them.\n"
    "If -r is specified, the listed rules are immediately run with the given "
    "directory and then the program terminates.")
#  parser.add_argument('-p', "--pidfile", action="store", dest="pidfile",
#                      type=str, default=None,
#                      help="The path to where the PID file should be "
#                            "created. If not provided, no PID file will "
#                            "be created and the process must be "
#                            "restarted to use an updated config file.")
  parser.add_argument('-c', "--config", action="store", dest="configfile",
                      type=str, default=None, required=True,
                      help="The path to where the settings file is saved.")
  parser.add_argument('-d', "--dir", action="store", dest="dir", type=str,
                      default='.',
                      help="Directory to run custom rules (-r option) on. "
                            "Defaults to current directory.")
  parser.add_argument('-r', "--rules", nargs='+', type=str, dest="rules",
                      default=None,
                      help="List of custom rules to run immediately without "
                        "starting the event handler.")
  args = parser.parse_args()

  if args.rules:
    handler = ire.eventhandler.EventHandler(args.configfile)
    # Replace the default watches with provided custom watch.
    handler.watches = [{
      "location": args.dir,
      "rules": args.rules
    }]
    path = os.path.expanduser(args.dir)
    for filename in os.listdir(path):
      rules = handler.matches(path, filename)
      handler.do_actions(rules, os.path.join(path, filename))
  else:
    platform = ire.autoplatform.platform
    if platform == "linux":  # Detect Linux here:
      import ire.inotifyhandler
      handler = ire.inotifyhandler.EventHandler(args.configfile)
    else:
      sys.stderr.write("Platform '{0}' not supported.\n".format(platform))
      sys.exit(1)
    handler.start()
