""" Quickstart script for MediumPy usage """

# imports
from mediumpy import MediumPy
from mediumpy import smart_run
from socialcommons.file_manager import set_workspace
from mediumpy import settings

import random
import datetime
now = datetime.datetime.now()

# set workspace folder at desired location (default is at your home folder)
set_workspace(settings.Settings, path=None)

# get an MediumPy session!
session = MediumPy(use_firefox=True)

with smart_run(session):
    session.set_do_follow(enabled=True, percentage=40, times=1)


