
""" Actions
  Actions are classes that contain three attributes:
    displayname: The name of the action that is displayed to the user.
    form_display: A list of three-tuples describing each argument that
      needs to be provided to the action. The format is
      (argument name, arg label, arg description)
    trigger: A static method that takes in the keyword arguments specified
      in form_display and performs some task.

"""

action_list = []

class PlatformError(Exception):
  """The action cannot be run on this platform"""
  pass

def import_action(cls, frm=None):
  try:
    tmp = __import__("ire.actions."+frm, fromlist=[cls], level=1)
    globals()[cls] = getattr(tmp, cls)
    action_list.append(cls)
  except PlatformError:
    pass

import_action('Alert', frm='alert')
import_action('Log', frm='log')
import_action('Move', frm='move')
import_action('Notify', frm='notify')
import_action('Shell', frm='shell')
