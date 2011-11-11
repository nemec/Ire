import re
import glob

__all__ = ['RegexPattern', 'SimplePattern', 'StartsWithPattern',
            'EndsWithPattern', 'MimetypePattern']


class PatternError(Exception):
  pass


class UnknownPatternStyleError(PatternError):
  def __str__(self):
    return "Unknown pattern style '{0}'".format(' '.join(self.args))


"""
class ExamplePattern(object):
  displayname = "A string that fits in with 'Filename [displayname] entry"
                Something like "matches", "starts with", etc.
  description = "A regular expression to match on."
  
  @staticmethod
  def match(pattern, arg):
    ''' pattern is the pattern string from the settings file
        arg is the filename that triggered the event
        Returns a boolean.
        Should capture all exceptions and reraise them as PatternErrors
        with the captured exception as the "InnerException"
    '''
"""


class RegexPattern(object):
  """ A pattern that matches any valid Python regular expression pattern.
  """
  displayname = "matches regex"
  description = "A regular expression to match on."
  
  @staticmethod
  def match(pattern, arg):
    try:
      return re.search(pattern, arg)
    except Exception as e:
      raise PatternError(e)
    

class SimplePattern(object):
  """ A pattern that matches a simpler form of regex:
      Only *, ?, and [] are allowed.
  """
  displayname = "matches glob"
  description = "Completion on *, ?, or []"
  
  @staticmethod
  def match(pattern, arg):
    for f in glob.iglob(pattern):
      if f == arg:
        return True
    return False
    

class StartsWithPattern(object):
  """ A pattern that matches only if the pattern matches
      the beginning of the string.
  """
  displayname = "starts with"
  
  @staticmethod
  def match(pattern, arg):
    return arg.startswith(pattern)

  
class EndsWithPattern(object):
  """ A pattern that matches only if the pattern matches
      the end of the string.
  """
  displayname = "ends with"
  
  @staticmethod
  def match(pattern, arg):
    return arg.endswith(pattern)


class MimetypePattern(object):
  """ A pattern that checks the filename against its
      guessed mimetype.
  """
  displayname = "mimetype is"
  
  @staticmethod
  def match(mimetype, arg):
    import mimetypes
    return mimetype in mimetypes.guess_type(arg)
      
