import re
import json
import shutil
import os.path

import actions
import patterns
import inotifyhandler

# ~/.local/share/Trash/

# http://lxr.free-electrons.com/source/include/linux/inotify.h#L29
# https://github.com/seb-m/pyinotify/wiki/Tutorial
# http://seb-m.github.com/pyinotify/
# http://docs.python.org/library/shutil.html

# http://files.minuslab.net/doc.html
# http://www.noodlesoft.com/features.php
# http://lifehacker.com/341950/belvedere-automates-your-self+cleaning-pc    


class Rule(object):
  def __init__(self, name,
                description = "",
                pattern_type = "AND",
                pattern_list = None,
                action_type = "",
                action_args = ""):
    self.name = name
    self.description = description
    self.pattern_type = pattern_type
    self.pattern_list = pattern_list
    self.action_type = action_type
    self.action_args = action_args
    
  def is_valid(self):
    return (self.name and self.pattern_list and
            self.action_type and type(self.action_args) == dict)
    
  def __repr__(self):
    return ("<Rule: name={0}, pattern_type={1}, pattern_list={2}, "
            "action_type={3}, action_args={4}").format(self.name,
                                                      self.pattern_type,
                                                      self.pattern_list,
                                                      self.action_type,
                                                      self.action_args)
  
class SettingsEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Rule):
      return {
                "name": obj.name,
                "description": obj.description,
                "pattern_type": obj.pattern_type,
                "pattern_list": obj.pattern_list,
                "action_type": obj.action_type,
                "action_args": obj.action_args,
              }
    elif isinstance(obj, actions.Action):
      return obj.serialize()
    return
    
class SettingsDecoder(json.JSONDecoder):
  def decode(self, json_str):
    rules = []
    data = json.loads(json_str)
    for rule in data["rules"]:
      r = Rule(rule["name"],
                rule["description"],
                rule["pattern_type"],
                rule["pattern_list"],
                rule["action_type"],
                rule["action_args"])
      if r.is_valid():
        rules.append(r)
    data["rules"] = rules
    return data
      

if __name__ == "__main__":  
  settings = json.load(open("save.json"), cls=SettingsDecoder)

  handler = inotifyhandler.EventHandler(settings["rules"],
                                        settings["watches"])

  handler.start()
  
