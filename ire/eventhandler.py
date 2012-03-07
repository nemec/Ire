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
    
    self.actions = dict(zip(action_module.action_list,
      [getattr(action_module, action) for action in
                                          action_module.action_list]))
    self.patterns = dict(zip(pattern_module.pattern_list,
      [getattr(pattern_module, pattern) for pattern in
                                            pattern_module.pattern_list]))
    
  
  def load_config(self, settingsfile):
    """Load configuration from a filename."""
    try:
      with open(settingsfile, 'r') as f:
        settings = json.load(f, cls=SettingsDecoder)
      with locked(self.rules_lock):
        self.rules = settings["rules"]
      with locked(self.watches_lock):
        self.watches = settings["watches"]
    except IOError as e:
      raise Exception("Could not load config.")

  def config_reset_handler(self, signum, frame):
    """Signal handler to reload configuration settings from a file."""
    self.load_config(self.settingsfile)

  def matches(self, path, filename):
    """
    Return a list of rules that match the given filename.

    Keyword arguments:
    path -- The file path that determines valid rules.
    filename -- The filename to match against valid rules.
    
    """
    matched = []
    
    def get_pattern_class(pattern):
      """
      Each entry in the pattern list contains the
      style and the pattern to match.

      """
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
                if(path == os.path.expanduser(watch["location"]) and
                    rule.name in watch["rules"]):
                  matched.append(rule)
        except pattern_module.PatternError as e:
          print e
    return matched

  def do_actions(self, rules, pathname):
    """Combine the actions for each rule and execute them."""
    actions = []
    with locked(self.rules_lock):
      for rule in rules:
        actions.extend(rule.actions)

    for action in actions:
      args = self.sub_args(action["args"], pathname)
      self.exe(action["type"], args)
  
  def sub_args(self, out, pathname):
    """
    Substitute text for shorthand directives (eg. %s) in all arguments.
    Full list of subs can be found in EventHandler.subs

    """

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
    """Execute the action with argument dictionary."""
    # TODO Spin off into threads? Might be helpful for long-running actions
    if action_type not in self.actions:
      raise KeyError("Unknown action type specified.")
    try:
      self.actions[action_type].trigger(**kwdict)
    except Exception as e:  # Don't want to crash everything... right?
      print ("Exception encountered running action "
            "{0}: {1}".format(action_type, e))
  
  def start(self):
    """
    Watch the filesystem for changes in watched directories, matching and
    executing actions for each change.

    """
    raise NotImplementedError
