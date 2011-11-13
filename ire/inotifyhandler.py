import re
import os.path
import pyinotify

import ire.eventhandler as eventhandler

locked = eventhandler.locked

class EventHandler(pyinotify.ProcessEvent, eventhandler.EventHandler):

  def __init__(self, settingsfile):
    pyinotify.ProcessEvent.__init__(self)
    eventhandler.EventHandler.__init__(self, settingsfile)
    self.in_progress = set()
    
  def process_IN_CREATE(self, event):
    if self.matches(os.path.basename(event.pathname), event.path):
      self.in_progress.add(event.wd)
    
  def process_IN_CLOSE_NOWRITE(self, event):
    filename = os.path.basename(event.pathname)
    rules = self.matches(filename, event.path)
    if event.wd in self.in_progress:
      self.do_actions(rules, event)
      self.in_progress.remove(event.wd)
    
  def process_IN_MOVED_TO(self, event):
    filename = os.path.basename(event.pathname)
    rules = self.matches(filename, event.path)
    self.do_actions(rules, event)

  def do_actions(self, rules, event):
    actions = []
    with locked(self.rules_lock):
      for rule in rules:
        actions.extend(rule.actions)

    for action in actions:
      args = self.sub_args(action["args"], event.pathname)
      self.exe(action["type"], args)
      
  def start(self):
    wm = pyinotify.WatchManager()
    mask = pyinotify.IN_CREATE|pyinotify.IN_CLOSE_NOWRITE|pyinotify.IN_MOVED_TO
    notifier = pyinotify.Notifier(wm, self)
    for watch in self.watches:
      wdd = wm.add_watch(os.path.expanduser(watch["location"]), mask)
    notifier.loop()
