import re
import gtk
import patterns
# http://www.pygtk.org/pygtk2tutorial/sec-FileChoosers.html
# http://www.pygtk.org/pygtk2tutorial/sec-TextBuffers.html#id2855626
# http://www.pygtk.org/docs/pygtk/class-gtkentrycompletion.html
# http://www.pygtk.org/docs/pygtk/class-gtktextbuffer.html#method-gtktextbuffer--apply-tag

class FilenameTag(gtk.TextTag):
  def __init__(self, name):
    super(PatternTag, self).__init__(name)
    self.set_property("background", "#f0f")
    self.set_property("editable", False)


class PatternTag(gtk.TextTag):
  def __init__(self, name):
    super(PatternTag, self).__init__(name)
    self.set_property("background", "#f00")
    self.set_property("editable", False)


class PatternTaggerEntry(gtk.Entry):
  def __init__(self, marker_char):
    super(PatternTaggerEntry, self).__init__()
    self.marker_char = marker_char
    self.tags = gtk.TextTagTable()
    
    self.completion = gtk.EntryCompletion()
    self.completion.set_match_func(self.completion_match)

    description = gtk.CellRendererText()
    description.set_property('editable', False)
    self.completion.pack_start(description)
    self.completion.add_attribute(description, "text", 1)

    self.set_completion(self.completion)
    self.completion.connect("match-selected", self.add_tag)

  def set_model(self, model, text_column=0):
    self.completion.set_model(model)
    self.completion.set_text_column(text_column)

  def completion_match(self, completion, entry, tree_iter):
    model = completion.get_model()
    modelstr = "%{0}".format(model[tree_iter][0])
    for match in re.findall("{0}\w*".format(self.marker_char), entry):
      if modelstr.startswith(match):
        return True
    return False

  def add_tag(self, completion, model, tree_iter):
    pos = self.get_property("cursor_position")
    text = self.get_text()
    start = text.rfind(self.marker_char, 0, pos)
    def subber(match):
      if match.start() == start:
        return self.create_tag(model[tree_iter][0])
    self.set_text(re.sub(self.marker_char + '\w+', subber, text))
    return True
  
  def create_tag(self, tag):
    print tag
    return "--"


class WatcherUI(gtk.Window):
  def __init__(self, marker_char='%'):
    super(WatcherUI, self).__init__()
    self.set_size_request(500, 400)
    
    self.connect("destroy", gtk.main_quit)
    
    self.text = PatternTaggerEntry(marker_char)
    self.text.tags.add(PatternTag("regex"))
    
    l = gtk.Label("hello")
    self.text.add_child(l)
    
    model = gtk.ListStore(str, str)
    model.append(["regex", "A regular expression to match on."])
    model.append(["glob", "Completion on *, ?, or []"])
    self.text.set_model(model)
    
    self.add(self.text)


if __name__ == "__main__":
  w = WatcherUI()
  w.show_all()
  gtk.main()
