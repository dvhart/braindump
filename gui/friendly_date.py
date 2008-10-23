#    Filename: friendly_date.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: utilities to convert from and to friendly date strings
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
# Copyright (C) Darren Hart, 2008
#
# 2008-Oct-19:	Initial version by Darren Hart <darren@dvhart.com>

from datetime import datetime,timedelta
import re
from logging import debug, info, warning, error, critical

# FIXME: change "This Friday" to "This Week", and make it <= days until friday

def datetime_ceiling(datetime_val):
    """Extend the time component to the latest possible value while maintaining the same day"""
    ret = datetime_val.replace(hour=23, minute=59, second=59, microsecond=999999)
    return ret

def friendly_to_datetime(friendly_str):
    """Convert a friendly date string to a datetime object"""
    ret = None

    if friendly_str == "None":
        ret = None
    elif friendly_str == "Today":
        ret = datetime.now()
    elif friendly_str == "Tomorrow":
        ret = datetime.now() + timedelta(days=1)
    # FIXME: match with a reg ex and compute the delta accordingly
    elif friendly_str == "This Friday":
        ret = datetime.now()
        day = ret.isoweekday()
        delta = 5 - day
        if delta < 0:
            delta = delta + 7
        ret = ret + timedelta(days=delta)
    # FIXME: match with a reg ex and compute the delta accordingly
    elif friendly_str == "Next Week":
        ret = datetime.now() + timedelta(days=7)
    else:
        debug("Unknown friendly date string: %s" % (friendly_str))

    if ret:
        ret = datetime_ceiling(ret)
    return ret

def datetime_to_friendly(datetime_val):
    ret = "None"
    if datetime_val is None:
        return ret

    datetime_val = datetime_ceiling(datetime_val)
    today = datetime_ceiling(datetime.now())
    delta_days = (datetime_val - today).days
    days_to_friday = 5 - today.isoweekday()
    if days_to_friday < 0:
        days_to_friday = days_to_friday + 7

    if datetime_val == datetime_ceiling(datetime.now()):
        ret = "Today"
    elif datetime_val == (today + timedelta(days=1)):
        ret = "Tomorrow"
    elif delta_days == days_to_friday:
        ret = "This Friday"
    elif delta_days == 7:
        ret = "Next Week"
    elif delta_days < 364:
        ret = datetime_val.strftime("%b %d")
    else:
        ret = datetime_val.strftime("%b %d %Y")

    return ret
