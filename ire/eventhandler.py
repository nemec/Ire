import re
import json
import signal
import os.path
import threading

import ire.actions as action_module
import ire.patterns as pattern_module


class locked:
  def __init__(self, lock):
    self.lock = lock

  def __enter__(self):
    self.lock.acquire()

  def __exit__(self, type, value, tb):
    self.lock.release()


class SettingsEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Rule):
      return Rule.serialize(obj)


class SettingsDecoder(json.JSONDecoder):
  def decode(self, json_str):
    rules = []
    data = json.loads(json_str)
    for rule in data["rules"]:
      try:
        r = Rule(**rule)
        if Rule.validate(r):
          rules.append(r)
      except TypeError as e:
        print "Invalid rule with name {0}".format(rule["name"])
    data["rules"] = rules
    return data


class Rule(object):
  pattern_conditions = (("AND", "all"), ("OR", "any"))

  def __init__(self, name="Untitled",
                description="",
                pattern_condition=pattern_conditions[0][0],
                pattern_list=None,
                actions=[]):
    self.name = name
    self.description = description
    self.pattern_condition = pattern_condition
    self.pattern_list = pattern_list
    self.actions = actions
  
  @staticmethod
  def validate(rule):
    try:
      return (rule.name and rule.pattern_list and rule.actions)
    except AttributeError:
      return False
  
  @staticmethod
  def serialize(obj):
    return {
              "name": obj.name,
              "description": obj.description,
              "pattern_condition": obj.pattern_condition,
              "pattern_list": obj.pattern_list,
              "actions": obj.actions
            }
    
  def __repr__(self):
    return ("<Rule: name={0}, pattern_condition={1}, pattern_list={2}, "
            "actions={3}").format(self.name,
                                  self.pattern_condition,
                                  self.pattern_list,
                                  self.actions)


class EventHandler(object):
  sub_marker = "%"
  subs = [
    ("s", "Insert the full filename and path.", lambda x: x),
    ("f", "Insert just the filename.", lambda x: os.path.basename(x)),
  ]

  def __init__(self, settingsfile):
    self.settingsfile = settingsfile
    self.rules_lock = threading.Lock()
    self.watches_lock = threading.Lock()
    self.load_config(settingsfile)
    
    self.actions = dict(zip(action_module.__all__,
      [getattr(action_module, action) for action in action_module.__all__]))
    self.patterns = dict(zip(pattern_module.__all__,
      [getattr(pattern_module, pattern) for pattern in pattern_module.__all__]))
    
  
  def load_config(self, settingsfile):
    try:
      with open(settingsfile, 'r') as f:
        settings = json.load(f, cls=SettingsDecoder)
      with locked(self.rules_lock):
        self.rules = settings["rules"]
      with locked(self.watches_lock):
        self.watches = settings["watches"]
    except IOError as e:
      print "Could not load config."

  def config_reset_handler(self, signum, frame):
    self.load_config(self.settingsfile)

  def matches(self, filename, watchid):
    matched = []
    
    # Each entry in the pattern list contains the
    # style and the pattern to match
    def get_pattern_class(pattern):
      style = pattern["style"]
      if style not in self.patterns:
        raise pattern_module.UnknownPatternStyleError(style)
      return self.patterns[style].match(pattern["pattern"], filename)
    
    with locked(self.rules_lock):
      for rule in self.rules:
        func = None
        if rule.pattern_condition.upper() == "AND":
          func = all
        elif rule.pattern_condition.upper() == "OR":
          func = any
        try:
          if func and func(get_pattern_class(pat) for pat in rule.pattern_list):
            with locked(self.watches_lock):
              for watch in self.watches:
                if(watchid == os.path.expanduser(watch["location"]) and
                    rule.name in watch["rules"]):
                  matched.append(rule)
        except pattern_module.PatternError as e:
          print e
    return matched
  
  def sub_args(self, out, pathname):
    to_sub = out.copy()
    for key in to_sub:
      for sub in self.subs:
        to_sub[key] = re.sub(self.sub_marker + sub[0],
                              sub[2](pathname), to_sub[key])
    to_sub.update({ "_filename": os.path.basename(pathname),  # filename
                  "_directory": os.path.dirname(pathname),  # just the directory
                  "_path": pathname})  # full path (dir+filename)
    return to_sub
    
  def exe(self, action_type, kwdict):
    # TODO Spin off into threads? Might be helpful for long-running actions
    try:
      self.actions[action_type].trigger(**kwdict)
    except Exception as e:
      print e  # Don't want to crash everything... right?
  
  def start(self):
    raise NotImplementedError