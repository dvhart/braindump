#!/bin/sh
sudo python setup.py install --prefix=/usr/local
sudo gtk-update-icon-cache /usr/share/icons/hicolor
sudo update-menus # is this necessary?
