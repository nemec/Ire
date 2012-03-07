from .. import autoplatform
from . import PlatformError

platform = autoplatform.platform

if platform == 'linux':
  import pynotify
  pynotify.init("Ire")
  class Notify(object):
    displayname = "Show Notification"
    form_display = [
      ("title", "with title", "Title to display in the notification."),
      ("text", "and message", "Message to display in the notification.")
    ]

    @staticmethod
    def trigger(**kwargs):
      n = pynotify.Notification("Ire: " + kwargs["title"], kwargs["text"])
      n.show()
else:
  raise PlatformError("Platform {0} not supported.".format(platform))
