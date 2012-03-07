class Alert(object):
  displayname = "Send alert"
  form_display = [("text", "with message", "Message to display in the alert."),
                  ]
  
  @staticmethod
  def trigger(**kwargs):
    print kwargs["text"]
