#!/usr/bin/env python

import re
import os
import shutil
from distutils.core import setup

from ire.autoplatform import platform


if platform == "linux":  # Autodetect platform (Win, Mac, Linux)
  config_application = "ire-config-gtk.py"
  data_files = [
      ("/usr/share/applications", ["data/ire-config.desktop"]),
      ("/usr/share/ire/", ["data/ire.desktop"]),
      ("/usr/share/ire/icons/", ["icons/ire.png"]),
    ]
elif platform == "windows":
  pass
elif plaform == "mac":
  pass
else:
  print "Error. Platform {0} unknown.".format(platform)
  import sys
  sys.exit(1)

config_bin = os.path.splitext(config_application)[0]

bin_dir = "build/bin"

try:
  os.makedirs(bin_dir)
except OSError:
  pass  # Dir already exists
# remove .py from executables
shutil.copyfile('ire.py', '{0}/ire'.format(bin_dir))
shutil.copyfile(config_application, '{0}/{1}'.format(bin_dir, config_bin))

setup(
    name="Ire",
    description="A tool for watching folders.",
    author="Daniel Nemec",
    author_email="djnemec@gmail.com",
    url="https://github.com/nemec/Ire",
    version="0.8",
    packages=["ire", "ire.actions"],
    scripts=[os.path.join(bin_dir, x) for x in ["ire", config_bin]],
    data_files=data_files
)
