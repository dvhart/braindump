#!/usr/bin/env python
#    Filename: config.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: BrainDump configuration classs based on ConfigObj
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright (C) Darren Hart, 2009
#
# 2009-Mar-1:  Initial version by Darren Hart <darren@dvhart.com>

import os, os.path
from configobj import ConfigObj

import logging
from logging import debug, info, warning, error, critical

class Config(ConfigObj):
    def __init__(self):
        # Ensure the user braindump directory exists
        home_dir = os.environ["HOME"]
        self.braindump_dir = home_dir + "/braindump"
        if not os.path.exists(self.braindump_dir):
            info("creating directory: %s" % (self.braindump_dir))
            os.makedirs(self.braindump_dir)
        elif os.path.isfile(self.braindump_dir):
            critical("unable to create data directory, file already exists with same name: %s" \
                     % (self.braindump_dir))

        # Initialize the config object
        config_path = self.braindump_dir + "/config"
        ConfigObj.__init__(self, config_path)

        # Check if the config file exists
        if not os.path.exists(config_path):
            info("creating initial config file with default settings: %s" % (config_path))
            self.set_defaults()

    def set_defaults(self):
        view = {
            'show_completed':False,
            'show_realms':False,
            'show_filters':False,
            'show_details':False,
            'show_new_task_defaults':False,
            'layout':"Horizontal"
        }
        self['view'] = view

        filters = {
            'filter_by_state':None
        }
        self['filters'] = filters

        self.write()
