import re
import os.path

import actions as action_module
import patterns as pattern_module


class EventHandler(object):

  def __init__(self, rules, watches):
    self.rules = rules
    self.watches = watches
    
    self.actions = dict(zip(action_module.__all__,
      [getattr(action_module, action) for action in action_module.__all__]))
    self.patterns = dict(zip(pattern_module.__all__,
      [getattr(pattern_module, pattern) for pattern in pattern_module.__all__]))
    
    self.subs = [
      ("%s", "Insert the full filename and path.", lambda x: x),
      ("%f", "Insert just the filename.", lambda x: os.path.basename(x)),
    ]
    
    
  def matches(self, filename, watchid):
    matched = []
    
    # Each entry in the pattern list contains the
    # style and the pattern to match
    def get_pattern_class(pattern):
      style = pattern["style"]
      if style not in self.patterns:
        raise pattern_module.UnknownPatternStyleError(style)
      return self.patterns[style].match(pattern["pattern"], filename)
    
    for rule in self.rules:
      func = None
      if rule.pattern_type.upper() == "AND":
        func = all
      elif rule.pattern_type.upper() == "OR":
        func = any
      try:
        if func and func(map(get_pattern_class, rule.pattern_list)):
          for watch in self.watches:
            if(watchid == watch["location"] and
                rule.name in watch["rules"]):
              matched.append(rule)
      except pattern_module.PatternError as e:
        print e
    return matched
  
  def sub_args(self, out, pathname):
    to_sub = out.copy()
    for key in to_sub:
      for sub in self.subs:
        to_sub[key] = re.sub(sub[0], sub[2](pathname), to_sub[key])
    return to_sub
    
  def exe(self, action_type, kwdict):
    self.actions[action_type].trigger(**kwdict)
  
  def start(self):
    raise NotImplementedError
