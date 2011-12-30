#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from ire.inotifyhandler import EventHandler

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
    "If -r is specified, the listed rules are immediately run and then "
    "the program terminates.")
  parser.add_argument('-p', "--pidfile", action="store", dest="pidfile",
                      type=str, default=None,
                      help="The path to where the PID file should be created.")
  parser.add_argument('-c', "--config", action="store", dest="configfile",
                      type=str, default=None, required=True,
                      help="The path to where the settings file is saved.")
  parser.add_argument('-d', "--dir", action="store", dest="dir", type=str,
                      default='.',
                      help="Directory to run custom rules on.")
  parser.add_argument('-r', "--rules", nargs='+', type=str, dest="rules",
                      default=None,
                      help="List of rules to run immediately without "
                        "starting the event handler.")
  args = parser.parse_args()

  handler = EventHandler(args.configfile)

  if args.rules:  # Replace the default watches with provided custom watch.
    handler.watches = [{
      "location": args.dir,
      "rules": args.rules
    }]
    path = os.path.expanduser(args.dir)
    for filename in os.listdir(path):
      rules = handler.matches(path, filename)
      handler.do_actions(rules, os.path.join(path, filename))
  else:
    handler.start()
