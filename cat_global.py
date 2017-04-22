#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  cat_global.py
#
#  Copyright 2016 James M. Coulthard <james.m.coulthard@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

#Constants
path_to_catinatord		= "/usr/local/bin/catinatord.py"
path_to_catinator_pid	= "/var/run/catinatord.py.pid"
tag_line				= "Come with me if you want to meow!!"
tag_line2				= "Hasta la vista, baby!"
version_attribute_ID 	= "series"
hw_model_ID				= "hardware"
hw_model_attrib_ID		= "model"
model_mask 				= 100
log_conf_ID				= "logconf"
check_service_command   = "service %s status | grep Active | cut -d ':' -f 2 | cut -d '(' -f 1"
active_service_response	= " active "
start_service_command	= "service %s start"
_eth0_ 					= 0
_wlan_ 					= 1
_usbmodem_ 				= 2
CLOSED 					= 0
ARMED 					= 1
JAMMED 					= 2
JAM_REPORTED			= 3
state_str				= ["CLOSED", "ARMED", "JAMMED", "JAM_REPORTED"]
html					= 0
text					= 1
smartphone				= 2
email 					= 0
sms						= 1
smart					= 2
target_type_str			= ["html", "plain", "smart"]
target_addr_str			= ["email", "sms", "smartphone"]
email_server_addr		= "127.0.0.1" # submit to sendmail service on localhost
sendmail_cmd			= ["/usr/sbin/sendmail", "-t", "-i"]  #sendmail command as list of argv passed to popen()
html_header				= "<!DOCTYPE"



#Global Variables
logger = None

def int32(x):
	if (x > 0xFFFFFFFF):
	 raise OverflowError
	elif (x > 0x7FFFFFFFF):
		x = int(0x100000000-x)
		if (x < 2147483548):
			return -x
		else:
			return -2147483648
	return (x)

def main():

	return 0

if __name__ == '__main__':
	main()

