#!/usr/bin/env python

import os
import sys
import argparse

import inotifyhandler

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
    "Watches folders for certain files and executes actions on them.")
  parser.add_argument('-p', action="store", dest="pidfile", type=str,
                      default="/tmp/ire.pid",
                      help="The path to where the PID file should be created.")
  parser.add_argument('-c', action="store", dest="configfile", type=str,
                      default="settings.conf",
                      help="The path to where the settings file is saved.")
  args = parser.parse_args()

  handler = inotifyhandler.EventHandler(args.configfile)
  handler.start()
