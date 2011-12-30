#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import gtk
import json

import ire.actions as actions
import ire.patterns as patterns
from ire.eventhandler import EventHandler, Rule, SettingsEncoder, SettingsDecoder


class AutoCompleteActionEntry(gtk.Entry):
  def __init__(self, model, text_column=0):
    super(AutoCompleteActionEntry, self).__init__()
    
    self.completion = gtk.EntryCompletion()
    self.completion.set_match_func(self.completion_match)

    description = gtk.CellRendererText()
    description.set_property('editable', False)
    self.completion.pack_start(description)
    self.completion.add_attribute(description, "text", 1)

    self.set_completion(self.completion)
    self.completion.connect("match-selected", self.add_tag)

    self.completion.set_model(model)
    self.completion.set_text_column(text_column)

  def completion_match(self, completion, entry, tree_iter):
    """Check if the text in the entry matches up to any model text."""
    model = completion.get_model()
    modelstr = "%{0}".format(model[tree_iter][0])
    for match in re.findall("{0}\w*".format(EventHandler.sub_marker), entry):
      if modelstr.startswith(match):
        return True
    return False

  def add_tag(self, completion, model, tree_iter):
    """Format the selected item for entry into the textbox and
      substitute it for the previously typed shortcut.

    """
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
    self.minus = gtk.Button("-")
    self.pack_end(self.minus, expand=False)

  def is_complete(self):
    raise NotImplementedError


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
    """Set the active Action type's form elements.
      Each Action has different arguments, so the form must be dynamically
      created whenever a new action is chosen.

    """
    self.action_forms.foreach(lambda w: self.action_forms.remove(w))
    args = self.action_arg_model[chooser.get_active()]
    for internal, display, description in args:
      label = gtk.Label(display)
      entry = AutoCompleteActionEntry(model=substitution_model)
      self.action_forms.pack_start(label, expand=False, padding=5)
      self.action_forms.pack_start(entry)
    self.action_forms.show_all()

  def is_complete(self):
    """The active action is filled in.
      Return True if each textbox is not empty.

    """
    return all(len(x) > 0 for x in self.get_active_choice().values())

  def get_active_choice(self):
    """Collect the Action's type and arguments into a dictionary
      for serialization.

    """
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

  def is_complete(self):
    """The active pattern is filled in.
      The textbox that contains the pattern is not empty.

    """
    return all(len(x) > 0 for x in self.get_active_choice().values())

  def get_active_choice(self):
    return {
            "style": self.pattern_model[self.pattern_chooser.get_active()][0],
            "pattern": self.text.get_text()
           }

class ExpandableContainer(gtk.HBox):
  """A container that holds a varying number of inner widgets.
    Widgets can be added and removed by clicking on the + or - buttons
    next to each widget.

  """
  def __init__(self, item_factory):
    super(ExpandableContainer, self).__init__()
    self.item_factory = item_factory
    
    self.container = gtk.VBox()
    self.pack_start(self.container)
    
    spacer = gtk.Alignment(0, 1, 0, 0)
    plus = gtk.Button("+")
    plus.connect("clicked", self.add_item)
    spacer.add(plus)
    self.pack_start(spacer, expand=False)
    
    self.add_item(None)
  
  def add_item(self, obj):
    """Add a new item to the bottom of the widget.
      Item is created from the factory function and its - button
      set to remove the item when clicked.

    """
    item = self.item_factory()
    item.minus.connect("clicked", self.remove_item, item)
    
    if len(self.container.get_children()) == 0:
      item.minus.set_sensitive(False)
    else:
      for child in self.container.get_children():
        child.minus.set_sensitive(True)

    self.container.pack_start(item, expand=False)
    item.show_all()
  
  def remove_item(self, minus_button, item):
    """Remove the item from the container.
      If there is only one item remaining in the
      container, disable its remove button.

    """
    self.container.remove(item)
    if len(self.container.get_children()) == 1:
      for child in self.container.get_children():
        child.minus.set_sensitive(False)

  def get_items(self):
    return self.container.get_children()


class AddRuleDialog(gtk.Dialog):
  def __init__(self):
    super(AddRuleDialog, self).__init__(title="Add Rule")
    self.set_modal(True)
    self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

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
    """Iterate through all of the dialog's children and use filled-in
      data to create a Rule object.
      If not all of the data is completed, return None.

    """
    name = self.name_entry.get_text()
    desc = self.description_entry.get_text()
    pattern_condition = self.condition_model[self.condition.get_active()][0]

    pattern_list = []
    for item in self.pattern_container.get_items():
      if item.is_complete():
        pattern_list.append(item.get_active_choice())

    action_list = []
    for item in self.action_container.get_items():
      if item.is_complete():
        action_list.append(item.get_active_choice())

    if all(len(x) > 0 for x in (name, pattern_list, action_list)):
      return Rule(
        name=name,
        description=desc,
        pattern_condition=pattern_condition,
        pattern_list=pattern_list,
        actions=action_list)


class AddWatchDialog(gtk.Dialog):
  def __init__(self, rule_model):
    super(AddWatchDialog, self).__init__(title="Add Watch")
    self.set_modal(True)
    self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

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
    """Convert the data entered into the form into a dictionary
      containing the chosen filename and rules.
      If no data exists for either key, return None.

    """
    fname = self.folder_button.get_filename()
    rules = [r[2].name for r in self.toggle_model if r[0]]
    if all(len(x) for x in (fname, rules)):
      return {
        "location": fname,
        "rules": rules
      }


class IreUI(gtk.Window):
  """The main window for the UI.
    Contains the menu and allows adding custom watches and rules.
  
  """
  def __init__(self):
    super(IreUI, self).__init__()
    self.set_size_request(500, 400)
    self.connect("delete-event", self.save_if_necessary)
    self.connect("destroy", gtk.main_quit)
    self.set_title(self.title_format)

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
      ( "/_Help/About",   None,     self.about, 0, None ),
    )
    self.item_factory = gtk.ItemFactory(gtk.MenuBar, "<main>", accel_group)
    self.item_factory.create_items(self.menu_items)
    
    self.config_filters = []
    filter = gtk.FileFilter()
    filter.set_name("Config Files (*.conf)")
    filter.add_pattern("*.conf")
    self.config_filters.append(filter)
    filter = gtk.FileFilter()
    filter.set_name("All Files")
    filter.add_pattern("*")
    self.config_filters.append(filter)
    
    def mark_unsaved(*args):
      self.unsaved_edits = True
    
    self.rule_model = gtk.ListStore(str, object)  # (String-rule, Rule object)
    self.rule_model.connect("row_changed", mark_unsaved)
    self.rule_model.connect("row_inserted", mark_unsaved)
    self.watch_model = gtk.ListStore(str, object)  # (String-watch, Watch dict)
    self.watch_model.connect("row_changed", mark_unsaved)
    self.watch_model.connect("row_inserted", mark_unsaved)
    
    menu_box = gtk.VBox()
    menu_box.pack_start(self.item_factory.get_widget("<main>"), expand=False)
    border = gtk.HBox()
    menu_box.pack_start(border)
    vbox = gtk.VBox()
    border.pack_start(vbox, padding=5)

    """Creates the "Rules" view, with its associated labels and buttons."""
    rule_label = gtk.Label("Rules:")
    rule_label.set_alignment(0, 0)
    vbox.pack_start(rule_label, expand=False, padding=5)

    rule_box = gtk.HBox()
    vbox.pack_start(rule_box)
    rule_scroll = gtk.ScrolledWindow()
    rule_box.pack_start(rule_scroll)
    rule_view = gtk.TreeView(model=self.rule_model)
    rule_view.set_headers_visible(False)
    rule_view.connect("row-activated", self.edit_rule)
    rule_view.connect("cursor_changed",
      lambda x: self.rule_remove.set_sensitive(True))
    rule_scroll.add(rule_view)
    cell = gtk.CellRendererText()
    rule_column = gtk.TreeViewColumn('Rules', cell)
    rule_column.add_attribute(cell, 'text', 0)
    rule_view.append_column(rule_column)
    r_small = gtk.VBox()
    rule_add = gtk.Button("+")
    rule_add.connect("clicked", self.create_rule)
    r_small.pack_end(rule_add, expand=False)
    self.rule_remove = gtk.Button("-")
    self.rule_remove.set_sensitive(False)
    def remove_selected_rule(btn):
      dg = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
        message_format="Are you sure you want to remove this rule?")
      resp = dg.run()
      dg.hide()
      if resp == gtk.RESPONSE_YES:
        self.rule_model.remove(self.rule_model.get_iter(rule_view.get_cursor()[0]))
        self.rule_remove.set_sensitive(False)
    self.rule_remove.connect("clicked", remove_selected_rule)
    r_small.pack_end(self.rule_remove, expand=False)
    rule_box.pack_start(r_small, expand=False)

    """Creates the "Watches" view, with its associated labels and buttons."""
    watch_label = gtk.Label("Watches:")
    watch_label.set_alignment(0, 0)
    vbox.pack_start(watch_label, expand=False, padding=5)

    watch_box = gtk.HBox()
    watch_scroll = gtk.ScrolledWindow()
    watch_box.pack_start(watch_scroll)
    watch_view = gtk.TreeView(model=self.watch_model)
    watch_view.set_headers_visible(False)
    watch_view.connect("row-activated", self.edit_watch)
    watch_view.connect("cursor_changed",
      lambda x: self.watch_remove.set_sensitive(True))
    watch_scroll.add(watch_view)
    cell = gtk.CellRendererText()
    watch_column = gtk.TreeViewColumn('Watches', cell)
    watch_column.add_attribute(cell, 'text', 0)
    watch_view.append_column(watch_column)
    w_small = gtk.VBox()
    watch_add = gtk.Button("+")
    watch_add.connect("clicked", self.create_watch)
    w_small.pack_end(watch_add, expand=False)
    self.watch_remove = gtk.Button("-")
    self.watch_remove.set_sensitive(False)
    def remove_selected_watch(btn):
      dg = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
        message_format="Are you sure you want to remove this watch?")
      resp = dg.run()
      dg.hide()
      if resp == gtk.RESPONSE_YES:
        self.watch_model.remove(self.watch_model.get_iter(watch_view.get_cursor()[0]))
        self.watch_remove.set_sensitive(False)
    self.watch_remove.connect("clicked", remove_selected_watch)
    w_small.pack_end(self.watch_remove, expand=False)
    watch_box.pack_start(w_small, expand=False)
    vbox.pack_start(watch_box)
    
    bottom_align = gtk.Alignment(0, 0, 0, 0)
    vbox.pack_end(bottom_align)
    
    self.add(menu_box)
    self.show_all()

  def create_rule(self, btn):
    """Display the dialog for creating a new rule.
      The rule is retrieved from the dialog and appended to the model.

    """
    dg = AddRuleDialog()
    dg.set_transient_for(self)

    rule = None
    while rule is None:
      response = dg.run()
      rule = dg.get_rule()
      if response == gtk.RESPONSE_OK:
        if rule is not None:
          self.rule_model.append(self.build_rule_model_row(rule))
          break
      elif response in (gtk.RESPONSE_CANCEL, gtk.RESPONSE_DELETE_EVENT):
        break
      else:
        print response
      validdg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK,
          message_format="All entries in the form must be filled.")
      validdg.run()
      validdg.hide()
    dg.hide()

  def build_rule_model_row(self, rule):
    """Format the rule for displaying in the main view.
      The display name and the rule itself are returned for
      insertion into the model.
    
    """
    if len(rule.description):
      display = "{0}: {1}".format(rule.name, rule.description)
    else:
      display = rule.name
    return (display, rule)
  
  def edit_rule(self, view, path, col):
    """Display a dialog that allows editing of a previously created rule."""
    pass
  
  def create_watch(self, btn):
    """Display the dialog for creating a new watch.
      The watch is retrieved from the dialog and appended to the model.

    """
    dg = AddWatchDialog(self.rule_model)
    dg.set_transient_for(self)
    
    watch = None
    while watch is None:
      response = dg.run()
      watch = dg.get_watch()
      if response == gtk.RESPONSE_OK:
        if watch is not None:
          self.watch_model.append(self.build_watch_model_row(watch))
          break
      elif response in (gtk.RESPONSE_CANCEL, gtk.RESPONSE_DELETE_EVENT):
        break
      validdg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK,
          message_format="Both a folder and a set of rules must be chosen.")
      validdg.run()
      validdg.hide()
    dg.hide()
  
  def build_watch_model_row(self, watch):
    """Format the watch for displaying in the main view.
      The display name and the watch itself are returned for
      insertion into the model.
    
    """
    display = "{0}: [{1}]".format(watch["location"], ', '.join(watch["rules"]))
    return (display, watch)

  def edit_watch(self, view, path, col):
    """Display a dialog that allows editing of a previously created watch."""
    pass

  __loaded_file = None
  @property
  def loaded_file(self):
    return self.__loaded_file
  @loaded_file.setter
  def loaded_file(self, name):
    self.__loaded_file = name
    self.set_title(self.title_format)

  @property
  def title_format(self):
    """Return the format for the window's title.
      The format is similar to the one used by gedit.

    """
    unsaved = "*" if self.unsaved_edits else ""
    if self.loaded_file:
      path, fname = os.path.split(self.loaded_file)
      home = os.path.expanduser("~")
      if path.startswith(home):
        path = re.sub(home, "~", path)
      return "{0}{1} ({2}) - Ire".format(unsaved, fname, path)
    else:
      return "{0}{1} - Ire".format(unsaved, "Untitled")

  __unsaved_edits = False
  @property
  def unsaved_edits(self):
    return self.__unsaved_edits
  @unsaved_edits.setter
  def unsaved_edits(self, value):
    self.__unsaved_edits = value
    self.set_title(self.title_format)

  def new_settings_file(self, *args):
    """Discard the current settings file and create a new one."""
    self.default_settings = {
      "pidfile": "/tmp/ire.pid"
    }
    
  def open_settings_file(self, *args):
    """Open a settings file and parse it for watches and rules."""
    dg = gtk.FileChooserDialog("Save", action=gtk.FILE_CHOOSER_ACTION_OPEN,
                            buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                      gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    for filter in self.config_filters:
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
      self.unsaved_edits = False
  
  def save_if_necessary(self, *args):
    """Ensure that any unsaved data is either saved or confirmed
      to discard before closing the application.

    """
    if self.unsaved_edits:
      dg = gtk.MessageDialog(type=gtk.MESSAGE_WARNING,
              message_format='Save changed to "{0}" before closing?'.format(
                self.loaded_file or "Untitled"))
      dg.set_modal(True)
      
      dg.add_button("Close without Saving", gtk.RESPONSE_CLOSE)
      dg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
      if self.loaded_file is None:
        dg.add_button(gtk.STOCK_SAVE_AS, gtk.RESPONSE_YES)
      else:
        dg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
      response = dg.run()
      dg.hide()
      if response == gtk.RESPONSE_YES:
        self.save_as_settings_file()
      elif response == gtk.RESPONSE_OK:
        self.save_settings_file()
      elif response == gtk.RESPONSE_CANCEL:
        return True  # Stop propogation of event so window stays open
    return False  # Propogates event
  
  def save_settings_file(self, *args):
    """Save the current data to a file.
      If there is no destination file, display the Save As dialog first.
      Return True if the file was saved, False otherwise.

    """
    if self.loaded_file is None:
      return self.save_as_settings_file()
    else:
      try:
        with open(self.loaded_file, 'w') as f:
          obj = { "rules": [], "watches": [] }
          for rule in self.rule_model:
            obj["rules"].append(rule[1])
          for watch in self.watch_model:
            obj["watches"].append(watch[1])
          json.dump(obj, f, cls=SettingsEncoder)
        self.unsaved_edits = False
        return True
      except IOError as e:
        print e
    return False
  
  def save_as_settings_file(self, *args):
    """Open a FileChooserDialog to pick the new file to save to.
      Return True if file was saved, False otherwise.
    
    """
    dg = gtk.FileChooserDialog("Save", action=gtk.FILE_CHOOSER_ACTION_SAVE,
              buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE,gtk.RESPONSE_OK))
    for filter in self.config_filters:
      dg.add_filter(filter)
    response = dg.run()
    dg.hide()
    if response == gtk.RESPONSE_OK:
      fname = dg.get_filename()
      if fname is not None:
        self.loaded_file = fname
        return self.save_settings_file()
    return False
    
  def about(self, win=None, menu_item=None):
    """Display the About dialog."""
    dg = gtk.AboutDialog()
    program_name = "Ire"
    dg.set_program_name(program_name)
    dg.set_title("About {0}".format(program_name))
    dg.set_comments("Ire is a tool for watching folders on the filesystem "
      "for activity and performing actions on new files.")
    dg.set_version("0.8")
    dg.set_copyright("(c) 2011 Daniel Nemec")
    dg.set_website("http://github.com/nemec")
    dg.set_logo(gtk.gdk.pixbuf_new_from_file("icons/ire.png"))
    def close(win, resp):
      if resp == gtk.RESPONSE_CANCEL:
        win.hide()
    dg.connect("response", close)
    dg.show()
    

if __name__ == "__main__":
  w = IreUI()
  w.show_all()
  gtk.main()
