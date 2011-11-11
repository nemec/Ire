import re
import gtk
import json
import gobject

import actions
import patterns
from eventhandler import EventHandler, Rule, SettingsEncoder, SettingsDecoder

# http://www.pygtk.org/pygtk2tutorial/sec-FileChoosers.html
# http://www.pygtk.org/pygtk2tutorial/sec-TextBuffers.html#id2855626
# http://www.pygtk.org/docs/pygtk/class-gtkentrycompletion.html
# http://www.pygtk.org/docs/pygtk/class-gtktextbuffer.html#method-gtktextbuffer--apply-tag


class AutoCompleteActionEntry(gtk.Entry):
  def __init__(self):
    super(AutoCompleteActionEntry, self).__init__()
    
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
    for match in re.findall("{0}\w*".format(EventHandler.sub_marker), entry):
      if modelstr.startswith(match):
        return True
    return False

  def add_tag(self, completion, model, tree_iter):
    pos = self.get_position()
    text = self.get_text()
    start = text.rfind(EventHandler.sub_marker, 0, pos)
    selected_sub = EventHandler.sub_marker + model[tree_iter][0]
    
    def subber(match):
      if match.start() == start:
        return selected_sub
      else:
        return match.group()
    txt = re.sub('({0}\w*)'.format(EventHandler.sub_marker), subber, text)
    if txt:
      self.set_text(txt)
      self.set_position(start + len(selected_sub))
    return True


class Item(gtk.HBox):
  def __init__(self):
    super(Item, self).__init__()
    self.plus = gtk.Button("+")
    self.minus = gtk.Button("-")
    
    self.pack_end(self.plus, expand=False)
    self.pack_end(self.minus, expand=False)


class ActionItem(Item):
  def __init__(self):
    super(ActionItem, self).__init__()

    self.substitution_model = gtk.ListStore(str, str)
    for sub in EventHandler.subs:
      self.substitution_model.append(sub[:2])

    # action (type, displayname, description)
    self.action_model = gtk.ListStore(str, str, str)
    self.action_arg_model = []  # (arg name, arg displayname, arg description)
    for action in actions.__all__:
      a = getattr(actions, action, None)
      self.action_model.append((
        a.__name__,  # Internal name, for saving to file.
        getattr(a, "displayname", a.__name__),  # Name to display in the dialog
        getattr(a, "description", "")  # Description of action
      ))
      self.action_arg_model.append(a.form_display)

    self.action_chooser = gtk.ComboBox(model=self.action_model)
    cell = gtk.CellRendererText()
    self.action_chooser.pack_start(cell, True)
    self.action_chooser.add_attribute(cell, 'text', 1)
    if len(self.action_model) > 0:
      self.action_chooser.set_active(0)
    self.pack_start(self.action_chooser, expand=False)

    self.action_forms = gtk.HBox()
    self.set_active_form(self.action_chooser, self.substitution_model)
    self.action_chooser.connect("changed", self.set_active_form,
                                self.substitution_model)
    self.pack_start(self.action_forms)

  def set_active_form(self, chooser, substitution_model):
    self.action_forms.foreach(lambda w: self.action_forms.remove(w))
    args = self.action_arg_model[chooser.get_active()]
    for internal, display, description in args:
      label = gtk.Label(display)
      entry = AutoCompleteActionEntry()
      entry.set_model(substitution_model)
      self.action_forms.pack_start(label, expand=False, padding=5)
      self.action_forms.pack_start(entry)
    self.action_forms.show_all()

  def get_active_action(self):
    active_ix = self.action_chooser.get_active()
    action_type = self.action_model[active_ix][0]
    args = {}
    
    arg_iter = iter(self.action_arg_model)
    # Should be in order of addition, which is order of list
    for child in self.action_forms.get_children():
      if isinstance(child, AutoCompleteActionEntry):
        arg_name, display, description = arg_iter.next()[0]
        arg_content = child.get_text()
        args[arg_name] = arg_content
    return args


class PatternItem(Item):
  def __init__(self):
    super(PatternItem, self).__init__()

    self.pattern_model = gtk.ListStore(str, str, str)
    for pattern in patterns.__all__:
      p = getattr(patterns, pattern, None)
      self.pattern_model.append((
        p.__name__,
        getattr(p, "displayname", p.__name__),
        getattr(p, "description", "")
      ))

    name_label = gtk.Label("Filename ")
    self.pack_start(name_label)

    self.pattern_chooser = gtk.ComboBox(model=self.pattern_model)
    cell = gtk.CellRendererText()
    self.pattern_chooser.pack_start(cell, True)
    self.pattern_chooser.add_attribute(cell, 'text', 1)
    if len(self.pattern_model) > 0:
      self.pattern_chooser.set_active(0)
    self.pack_start(self.pattern_chooser)

    self.text = gtk.Entry()
    self.pack_start(self.text)

  def get_active_pattern(self):
    return {
            "style": self.pattern_model[self.pattern_chooser.get_active()][0],
            "pattern": self.text.get_text()
           }

class ExpandableContainer(gtk.VBox):
  def __init__(self, item_type):
    super(ExpandableContainer, self).__init__()
    self.item_type = item_type
    self.add_item(None)
  
  def add_item(self, obj):
    item = self.item_type()
    item.plus.connect("clicked", self.add_item)
    item.minus.connect("clicked", self.remove_item)
    
    if len(self.get_children()) == 0:
      item.minus.set_sensitive(False)
    else:
      for child in self.get_children():
        child.minus.set_sensitive(True)

    self.pack_start(item, expand=False)
    item.show_all()
  
  def remove_item(self, minus_button):
    self.remove(minus_button.parent)
    if len(self.get_children()) == 1:
      for child in self.get_children():
        child.minus.set_sensitive(False)


class AddRuleDialog(gtk.Dialog):
  def __init__(self):
    super(AddRuleDialog, self).__init__(title="Add Rule")
    self.set_modal(True)
    self.add_button(gtk.STOCK_OK, 1)
    self.add_button(gtk.STOCK_CANCEL, -1)

    h_layout = gtk.HBox()
    v_layout = gtk.VBox()

    title_box = gtk.HBox()
    
    label_box = gtk.VBox()
    name_label = gtk.Label("Name:")
    name_label.set_alignment(1, 0)
    description_label = gtk.Label("Description:")
    label_box.pack_start(name_label, expand=False, padding=5)
    label_box.pack_start(description_label, expand=False, padding=5)
    
    entry_box = gtk.VBox()
    self.name_entry = gtk.Entry()
    self.description_entry = gtk.Entry()
    entry_box.pack_start(self.name_entry, expand=False)
    entry_box.pack_start(self.description_entry, expand=False)
    
    title_box.pack_start(label_box, expand=False)
    title_box.pack_start(entry_box, expand=False)
    v_layout.pack_start(title_box, expand=False, padding=5)
    
    pattern_box = gtk.VBox()
    condition_box = gtk.HBox()
    condition_label_start = gtk.Label("If ")
    self.condition_model = gtk.ListStore(str, str)
    for condition in Rule.pattern_conditions:
      self.condition_model.append(condition)
    self.condition = gtk.ComboBox(model=self.condition_model)
    cell = gtk.CellRendererText()
    self.condition.pack_start(cell, True)
    self.condition.add_attribute(cell, 'text', 1)
    self.condition.set_active(0)
    condition_label_end = gtk.Label(" of the following conditions are met:")
    
    condition_box.pack_start(condition_label_start, expand=False)
    condition_box.pack_start(self.condition, expand=False)
    condition_box.pack_start(condition_label_end, expand=False)
    pattern_box.pack_start(condition_box, expand=False)
    
    self.pattern_container = ExpandableContainer(PatternItem)
    pattern_box.pack_start(self.pattern_container)
    v_layout.pack_start(pattern_box, padding=5)
    
    action_box = gtk.VBox()
    action_label = gtk.Label("Do the following:")
    action_label.set_alignment(0, 0)
    action_box.pack_start(action_label, expand=False)
    
    self.action_container = ExpandableContainer(ActionItem)
    action_box.pack_start(self.action_container)
    v_layout.pack_start(action_box, padding=5)

    h_layout.pack_start(v_layout, padding=20)
    self.get_content_area().add(h_layout)
    
    self.show_all()
  
  def get_rule(self):
    pattern_condition = self.condition_model[self.condition.get_active()][0]

    pattern_list = []
    for item in self.pattern_container.get_children():
      pattern_list.append(item.get_active_pattern())

    action_list = []
    for item in self.action_container.get_children():
      action_list.append(item.get_active_action())

    return Rule(
      name=self.name_entry.get_text(),
      description=self.description_entry.get_text(),
      pattern_condition=pattern_condition,
      pattern_list=pattern_list,
      actions=action_list)


class AddWatchDialog(gtk.Dialog):
  def __init__(self, rule_model):
    super(AddWatchDialog, self).__init__(title="Add Watch")
    self.set_modal(True)
    self.add_button(gtk.STOCK_OK, 1)
    self.add_button(gtk.STOCK_CANCEL, -1)

    self.toggle_model = gtk.ListStore(bool, str, object)
    for row in rule_model:
      self.toggle_model.append((False, row[0], row[1]))

    h_layout = gtk.HBox()
    v_layout = gtk.VBox()

    folder_selector_box = gtk.HBox()
    folder_label = gtk.Label("Watched Folder:")
    self.folder_button = gtk.FileChooserButton("Select a Folder")
    self.folder_button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    folder_selector_box.pack_start(folder_label, expand=False, padding=5)
    folder_selector_box.pack_start(self.folder_button, expand=False)
    
    rule_view = gtk.TreeView(model=self.toggle_model)
    
    toggle = gtk.CellRendererToggle()
    toggle.set_property('activatable', True)
    toggle_column = gtk.TreeViewColumn('Selected', toggle, active=0)
    toggle.connect("toggled", self.do_toggle)
    rule_view.append_column(toggle_column)
    
    cell = gtk.CellRendererText()
    rule_column = gtk.TreeViewColumn('Rules', cell)
    rule_column.add_attribute(cell, 'text', 1)
    rule_view.append_column(rule_column)
    rule_view.set_headers_visible(False)
    
    v_layout.pack_start(folder_selector_box, expand=False)
    v_layout.pack_start(rule_view)
    h_layout.pack_start(v_layout, padding=20)
    self.get_content_area().add(h_layout)
    
    self.show_all()

  def do_toggle(self, cell, row):
    self.toggle_model[row][0] = not self.toggle_model[row][0]
  
  def get_watch(self):
    return {
      "location": self.folder_button.get_filename(),
      "rules": [r[2].name for r in self.toggle_model if r[0]]
    }


class IreUI(gtk.Window):
  def __init__(self):
    super(IreUI, self).__init__()
    self.set_size_request(500, 400)
    self.set_title("Ire")
    
    self.connect("destroy", gtk.main_quit)
    self.loaded_file = None

    accel_group = gtk.AccelGroup()
    self.menu_items = (
      ( "/_File",         None,         None, 0, "<Branch>" ),
      ( "/File/_New",     "<ctl>N", self.new_settings_file, 0, None ),
      ( "/File/_Open",    "<ctl>O", self.open_settings_file, 0, None ),
      ( "/File/_Save",    "<ctl>S", self.save_settings_file, 0, None ),
      ( "/File/Save _As", None,     self.save_as_settings_file, 0, None ),
      ( "/File/sep1",     None,         None, 0, "<Separator>" ),
      ( "/File/Quit",     "<ctl>Q", gtk.main_quit, 0, None ),
      ( "/_Help",         None,         None, 0, "<Branch>" ),
      ( "/_Help/About",   None,     self.help_about, 0, None ),
    )
    self.item_factory = gtk.ItemFactory(gtk.MenuBar, "<main>", accel_group)
    self.item_factory.create_items(self.menu_items)
    
    self.rule_model = gtk.ListStore(str, object)  # (String-rule, Rule object)
    self.rule_model.connect("row_changed", self.mark_file_edited)
    self.rule_model.connect("row_inserted", self.mark_file_edited)
    self.watch_model = gtk.ListStore(str, object)  # (String-watch, Watch dict)
    self.watch_model.connect("row_changed", self.mark_file_edited)
    self.watch_model.connect("row_inserted", self.mark_file_edited)
    
    menu_box = gtk.VBox()
    border = gtk.HBox()
    vbox = gtk.VBox()
    rule_label = gtk.Label("Rules:")
    rule_label.set_alignment(0, 0)
    rule_box = gtk.HBox()
    rule_scroll = gtk.ScrolledWindow()
    rule_view = gtk.TreeView(model=self.rule_model)
    rule_scroll.add(rule_view)
    cell = gtk.CellRendererText()
    rule_column = gtk.TreeViewColumn('Rules', cell)
    rule_column.add_attribute(cell, 'text', 0)
    rule_view.append_column(rule_column)
    rule_view.set_headers_visible(False)
    rule_button = gtk.Button("+")
    rule_button.set_alignment(1, 1)
    rule_button.connect("clicked", self.create_rule)
    r_small = gtk.VBox()
    r_small.pack_end(rule_button, expand=False)
    rule_box.pack_start(rule_scroll)
    rule_box.pack_start(r_small, expand=False)
    
    watch_label = gtk.Label("Watches:")
    watch_label.set_alignment(0, 0)
    watch_box = gtk.HBox()
    watch_scroll = gtk.ScrolledWindow()
    watch_view = gtk.TreeView(model=self.watch_model)
    watch_scroll.add(watch_view)
    cell = gtk.CellRendererText()
    watch_column = gtk.TreeViewColumn('Watches', cell)
    watch_column.add_attribute(cell, 'text', 0)
    watch_view.append_column(watch_column)
    watch_view.set_headers_visible(False)
    watch_button = gtk.Button("+")
    watch_button.set_alignment(1, 1)
    watch_button.connect("clicked", self.create_watch)
    w_small = gtk.VBox()
    w_small.pack_end(watch_button, expand=False)
    watch_box.pack_start(watch_scroll)
    watch_box.pack_start(w_small, expand=False)
    
    vbox.pack_start(rule_label, expand=False, padding=5)
    vbox.pack_start(rule_box)
    vbox.pack_start(watch_label, expand=False, padding=5)
    vbox.pack_start(watch_box)
    bottom_align = gtk.Alignment(0, 1, 0, 1)
    vbox.pack_end(bottom_align)
    
    border.pack_start(vbox, padding=5)
    menu_box.pack_start(self.item_factory.get_widget("<main>"), expand=False)
    menu_box.pack_start(border)
    self.add(menu_box)
    self.show_all()

  def create_rule(self, btn):
    dg = AddRuleDialog()
    dg.set_transient_for(self)

    response = dg.run()
    dg.hide()
    if response == 1:
      rule = dg.get_rule()
      self.rule_model.append(self.build_rule_model_row(rule))

  def build_rule_model_row(self, rule):
    display = "{0}: {1}".format(rule.name, rule.description)
    return (display, rule)
  
  def create_watch(self, btn):
    dg = AddWatchDialog(self.rule_model)
    dg.set_transient_for(self)
    
    response = dg.run()
    dg.hide()
    if response == 1:
      watch = dg.get_watch()
      self.watch_model.append(watch)
  
  def build_watch_model_row(self, watch):
    display = "{0}: {1}".format(watch["location"], watch["rules"])
    return (display, watch)

  def save_and_exit(self):
    pass

  def mark_file_edited(self, *args, **kwargs):
    self.unsaved = True
    title = self.get_title()
    if not title.startswith("*"):
      self.set_title("*" + title)
  
  def clear_file_edited(self, *args, **kwargs):
    self.unsaved = False
    title = self.get_title()
    if title.startswith("*"):
      self.set_title(title[1:])

  def new_settings_file(self, win, data):
    print data
    
  def open_settings_file(self, win, data):
    dg = gtk.FileChooserDialog("Save", action=gtk.FILE_CHOOSER_ACTION_OPEN,
                            buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                      gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    filter = gtk.FileFilter()
    filter.set_name("Config Files (*.conf)")
    filter.add_pattern("*.conf")
    dg.add_filter(filter)
    filter = gtk.FileFilter()
    filter.set_name("All Files (*.*)")
    filter.add_pattern("*")
    dg.add_filter(filter)
    response = dg.run()
    dg.hide()
    if response == gtk.RESPONSE_OK:
      self.loaded_file = dg.get_filename()
      self.rule_model.clear()
      self.watch_model.clear()
      settings = {}
      try:
        with open(self.loaded_file, 'r') as f: 
          settings = json.load(f, cls=SettingsDecoder)
      except IOError as e:
        print e
      if "rules" in settings:
        for rule in settings["rules"]:
          self.rule_model.append(self.build_rule_model_row(rule))
      if "watches" in settings:
        for watch in settings["watches"]:
          self.watch_model.append(self.build_watch_model_row(watch))
    
  def save_settings_file(self, win, data):
    if self.loaded_file is None:
      self.save_as_settings_file(None, None)
    else:
      try:
        with open(self.loaded_file, 'w') as f:
          obj = { "rules": [], "watches": [] }
          for rule in self.rule_model:
            obj["rules"].append(rule[1])
          for watch in self.watch_model:
            obj["watches"].append(watch[1])
          json.dump(obj, f, cls=SettingsEncoder)
        self.clear_file_edited()
      except IOError as e:
        print e
  
  def save_as_settings_file(self, win, data):
    dg = gtk.FileChooserDialog("Save", action=gtk.FILE_CHOOSER_ACTION_SAVE,
              buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE,gtk.RESPONSE_OK))
    filter = gtk.FileFilter()
    filter.set_name("Config Files (*.conf)")
    filter.add_pattern("*.conf")
    dg.add_filter(filter)
    filter = gtk.FileFilter()
    filter.set_name("All Files (*.*)")
    filter.add_pattern("*")
    dg.add_filter(filter)
    response = dg.run()
    dg.hide()
    if response == gtk.RESPONSE_OK:
      self.loaded_file = dg.get_filename()
      if self.loaded_file is not None:
        self.save_settings_file(None, None)
    
  def help_about(self, win, data):
    pass

if __name__ == "__main__":
  w = IreUI()
  w.show_all()
  gtk.main()
