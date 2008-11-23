#!/bin/sh
sudo python setup.py install
sudo gtk-update-icon-cache /usr/share/icons/hicolor
sudo update-menus # is this necessary?
