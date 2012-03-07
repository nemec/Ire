import shutil
        

class Move(object):
  displayname = "Move file"
  form_display = [("destination", "to", "Destination path and filename."), ]
  
  @staticmethod
  def trigger(**kwargs):
    shutil.move(kwargs["_path"], kwargs["destination"])
