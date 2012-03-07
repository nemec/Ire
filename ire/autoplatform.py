import platform as pl
import os

if pl.system().lower().startswith('windows'):
  platform = 'windows'
elif pl.system().lower().startswith('darwin'):
  platform = 'mac'
else:
  platform = 'linux'
