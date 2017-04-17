#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  catinatord.py
#  
#  Copyright 2016 James M. Coulthard <james.m.coulthard@gmail.com>
#  
#  This is the main loop of The Catinator daemon.
#  This file is forked from catinator_init.py after init has checked the config
#  and started all sub-processes necessary to execute the catinator.
#  catinatord.py assumes it's enviroment is ok to execute, and less 
#  checks are done here.  (That's the init's job)
#  The basic function of the catinator is:
#  1) Load config
#  		a. Setup GPIO ports
#		b. read in notifcation templates
#		c. Initialize notifcation objects
#  2) Enter the main function loop, call the FSM in a do-while...
#		a. Poll GPIO ports/read door state
#		b. if doors go from close to open state, send "Armed" notifications
#		c. if doors go from open to close state, send "Sprung" notifications
#			i.  Take a picture from webcam and attach to notifcations
#		d. if not all doors close at same time, send "Jammed" notifications
#		e. Wait interval, then loop back to top
#  3) Clean up/Exit gracefully upon OS signal/request
#  4) Catch exceptions and send to logs
#
#  Doors are polled on a preset interval (1 to 5 sec). The idea here is that the speed
#  of notification is not critical, but door condition is critical.  A jammed
#  door will indicate a problem with the trap, so, we really want to 
#  wait as long as possible between door checks to ensure all doors are
#  closed before sending a "Jammed" notification.  This is basically an
#  exagerated debouncing algorhythm, but necessary due to the physical
#  structure of the trap.  Door jams are certainly possible.
#
#  The process sleeps in between polling, and wakes again at every interval.
#  It does this until requested to exit by OS signal. (SIGTERM or other)
#
#  Basic catinator function looping is as follows:
#  catinator_init.py  -->  start the catinatord.py & all services
#                          fork off the catinatord.py process
#  catinatord.py      -->  the basic main loop of the catinator
#
#  catinatord.py is designed to be called by catinator_init.py in
#  an init.d startup script and exit, thus making catinatord a system service.
#  catinatord is designed not to exit unless killed via signal. (stopped)
#  Once configured and operating, the service runs uninterrupted.
#  Both processes log to the same logfile and syslog
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  


#Imports
import sys, getopt					# libs for processing cmd line arguments
import os							# Signal handling
import xml.etree.ElementTree as ET  # XML parser library
import logging						# Nothing happens in production w/o logs
import logging.config   			# logging lib conf file processing
import logging.handlers				# lib for rotating logfiles & syslog
import RPi.GPIO as GPIO				# GPIO library
import time							# time library for sleep()
from time import sleep
import subprocess					# for spawning notifications
import cat_global
import catconf						# module for catinator configuation


#Constants
logger_ID				= "catinatord"

#Module Variables

#Classes and methods/functions


# Wrapper for standalone functional script implementation
#
# Usage: Catinatord.py -c <configuration file>
#		 Catinatord.py -h
# Ex: <python> Catinatord.py -c /etc/catinator/catinator.conf.xml
#
# Command line options:
#		<conf file> - path to catinator.conf.xml
#		-h       - help, outputs usage
#
# Return Value: 
#		0    Success
#		1    "-h" help input argument detected
#		2    Argument processing failure
#
# Note: this wrapper script can either be invoked by calling python or
# by calling it directly from the shell if the script has execute 
# permissions.
#
# Tested in Python 2.7.9 on "Jessie" Raspian 4.4.13-v7+ #894
# with Motion 3.2.12+git20140228
#
def main(argv):
	
	#Constants
	Usage = """Usage: catinatord.py <start/stop/restart> -c </path/configuration file>
Ex: <python3> catinatord.py <start/stop/restart> -c /etc/catinator/catinator.conf.xml"""

	#Variables
	conf_file    = "" # path to configuration file
	return_value = 0  # Return value assumes success
	version 	 = "" # Version string
	hw_model	 = "" # Model string
	log_conf 	 = "" # String of Log config file
	daemon_cmd	 = "" # string of daemon command	
	
	#parse arguments
	if (len(argv) <= 0):   #Test to see if we have arguments...
		print("Not enough arguments")
		return_value = 4  #Not enough args
	else:    # Yes, we do have proper number of args
		try: #Try to get the options
			opts, args = getopt.getopt(argv,"strhc:", ["start", "stop", "restart", "help", "config-file="])
		except Exception as err:  #Print an error if occurs
			print("Argument Error: ", err)  
			return_value = 5
		else:
			if (not opts): #Any recognized opts present in argv?
				print("No recognized arguments")
				return_value = 6    # No, do not process
			else:  #We have valid options in argv
				for opt, arg in opts:		#Test the options in the args
					if  opt in ("-h","--help"):		#Help arg, just print usage
						return_value = 1
					elif opt in ("-c","--config-file="): #-c is the "conf" file
						conf_file = arg     # arg is present, store it
					elif opt in ("-s","-t","-r","--start","--stop","--restart"):
						daemon_cmd = opt
					else:
						print("Unknown argument")
						return_value = 7	# unknown option
				
				if (return_value != 0):		#Argv processing not ok?
					conf_file = ""			#Clear the conf_file
				else:
					#got valid arguments, create the catinator instance

					# Step 1 - Read in the config file and parse it
					try: 
						config_tree = ET.parse(conf_file)
					except Exception as err:
						print ("Fatal parse error in %s:\n%s" % (conf_file, err))
						return_value = 1
					else:
						# XML is OK, Grab the basic config data structure
						config_root = config_tree.getroot()
						# Get the version string
						version     = config_root.attrib[cat_global.version_attribute_ID]
	
						# iterate and get the log element and model
						# these early steps are *just* to start the log file	
						for elem in config_root.iter():
							if (elem.tag == cat_global.log_conf_ID):
								log_conf = elem.text
							elif (elem.tag == cat_global.hw_model_ID):
								hw_model = elem.attrib[cat_global.hw_model_attrib_ID]
								
						#Setup logging
						try: 
							logging.config.fileConfig(log_conf)
						except Exception as err:
							print("logging configuration file error: %s" % err)
							return_value = 1
						else:
							#Setup system logging
							logger = logging.getLogger(logger_ID)
							logger.critical("Catinatord - Series: %s  Model: %s" % (version, hw_model))

							# Read in the configuration
							logger.info("Read in the config file and parsed it ...")
							logger.info("Populate system data structures for service initialization")
							catinator = catconf.catinator_type(config_root, logger)

							#Execute the daemon and stand back!  This block always sys.exits...
							if daemon_cmd in ("-t", "--stop"):
								logger.critical("Stopping Catinatord")
								catinator.stop()
							elif daemon_cmd in ("-r", "--restart"):
								logger.critical("Restarting Catinatord")
								catinator.restart(logger)
							elif daemon_cmd in ("-s", "--start"):
								logger.critical("Starting Catinatord")							
								return_value = catinator.start(logger)
							else:
							    print("No start/stop/restart command argument")
							    return_value = 8
							
													
	#Check return value, if not success, print Usage
	if (return_value != 0):
		print (Usage)			# Catch any errors and print Usage
	else:
		print (cat_global.tag_line2)		# We're outta here!
	
	return (return_value)


# if invoked from command line and this module is 'main', then call main
if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
