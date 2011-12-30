import re
import os.path
import pyinotify

import ire.eventhandler as eventhandler

locked = eventhandler.locked

# event.pathname is the path+filename, event.path is just the path

class EventHandler(pyinotify.ProcessEvent, eventhandler.EventHandler):
  """Event Handler implementation using inotify."""

  def __init__(self, settingsfile):
    pyinotify.ProcessEvent.__init__(self)
    eventhandler.EventHandler.__init__(self, settingsfile)
    self.in_progress = set()
    
  def process_IN_CREATE(self, event):
    """
    Start tracking when a watched file is created.
    Must be paired with process_IN_CLOSE_NOWRITE to ensure that the created
    file is fully completed (eg. after a download).
    
    """
    if self.matches(event.path, os.path.basename(event.pathname)):
      self.in_progress.add(event.wd)
    
  def process_IN_CLOSE_NOWRITE(self, event):
    """
    Execute actions when a watched file is closed.
    Limited to executing on files that were created and subsequently closed,
    to prevent execution when just opening a file.

    """
    if event.wd in self.in_progress:
      filename = os.path.basename(event.pathname)
      self.match_exec(event.path, filename)
      self.in_progress.remove(event.wd)
  process_IN_CLOSE_WRITE = process_IN_CLOSE_NOWRITE
  
  def process_IN_MOVED_TO(self, event):
    """Execute actions when a watched file is moved."""
    filename = os.path.basename(event.pathname)
    self.match_exec(event.path, filename)

  def match_exec(self, path, filename):
    """Match the filename to and existing rules and execute their actions."""
    rules = self.matches(path, filename)
    self.do_actions(rules, os.path.join(path, filename))
      
  def start(self):
    wm = pyinotify.WatchManager()
    mask = (pyinotify.IN_CREATE|pyinotify.IN_MOVED_TO|
            pyinotify.IN_CLOSE_NOWRITE|pyinotify.IN_CLOSE_WRITE)
    notifier = pyinotify.Notifier(wm, self)
    for watch in self.watches:
      wdd = wm.add_watch(os.path.expanduser(watch["location"]), mask)
    notifier.loop()
