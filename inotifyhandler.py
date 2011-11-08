import re
import os.path
import pyinotify

import eventhandler

class EventHandler(pyinotify.ProcessEvent, eventhandler.EventHandler):

  def __init__(self, rules, watches):
    pyinotify.ProcessEvent.__init__(self)
    eventhandler.EventHandler.__init__(self, rules, watches)
    self.in_progress = set()
    
  def process_IN_CREATE(self, event):
    if self.matches(os.path.basename(event.pathname), event.path):
      self.in_progress.add(event.wd)
    
  def process_IN_CLOSE_NOWRITE(self, event):
    filename = os.path.basename(event.pathname)
    rules = self.matches(filename, event.path)
    if event.wd in self.in_progress:
      for rule in rules:
        self.exe(rule.action_type, self.sub_args(rule.action_args, event.pathname))
      self.in_progress.remove(event.wd)
    
  def process_IN_MOVED_TO(self, event):
    filename = os.path.basename(event.pathname)
    rules = self.matches(filename, event.path)
    for rule in rules:
      self.exe(rule.action_type, self.sub_args(rule.action_args, event.pathname))
      
  def start(self):
    wm = pyinotify.WatchManager()
    mask = pyinotify.IN_CREATE|pyinotify.IN_CLOSE_NOWRITE|pyinotify.IN_MOVED_TO
    notifier = pyinotify.Notifier(wm, self)
    for watch in self.watches:
      wdd = wm.add_watch(os.path.expanduser(watch["location"]), mask)
    notifier.loop()
