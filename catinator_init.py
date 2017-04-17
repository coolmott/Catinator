#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  catinator_init.py
#  
#  Copyright 2016 James M. Coulthard <james.m.coulthard@gmail.com>
#  
#  This is the daemon initialization function of the Catinator
#  This file reads the Catinator.conf.xml file and configures and loads
#  all sub-processes/env necessary to execute the catinator.
#  It will check for presence key services, and re-execute if necessary.
#  It is intended to run and be executed from init.d at start up
#  It's final action is to fork a catinatord instance.
#
#  Basic catinator function looping is as follows:
#  catinator_init.py  -->  start the catinatord.py & all services
#                          fork off the catinatord.py process
#  catinatord.py      -->  the basic main loop of the catinator
#
#  catinator_init is designed to be called by start-stop-daemon in
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
import xml.etree.ElementTree as ET  # XML parser library
import logging						# Nothing happens in production w/o logs
import logging.config   			# logging lib conf file processing
import logging.handlers				# lib for rotating logfiles & syslog
import cat_global
import catconf						# module for catinator configuation
import subprocess					# call shell to fork catinatord


#Constants
logger_ID				= "catinator_init"

#Module Variables

#Classes and methods/functions

# Function: catinator_init()
# Input:  "conf_file" - full path to the configuration file
#
# Output: "return_value" - 0, success; non-0, failure
#
# Purpose:
#
# This function encompasses the catinator initialization sequence:
#  1) Read in the config file and parse it
#  2) Populate system data structures for service initialization
#  3) setup networking
#  4) setup DDNS
#  5) Check for and start required system services
#  6) Launch catinator_main.py, validate process, save PID
#  7) Setup complete!
#
# This function is standalone and can be imported from this module 
# into other python modules.
#
# Tested in Python 2.7.9 on "Jessie" Raspian 4.4.13-v7+ #894
# with Motion 3.2.12+git20140228
#
def catinator_init(conf_file):

	
	#Variables
	version					= "" # Version string
	hw_model				= "" # Model string
	log_conf 				= "" # String of Log config file	
	return_value 			= 0  # Return value assumes success

	# Step 1 - Read in the config file and parse it
	try: #Parse the xml, catch any errors and fail out
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
			if (elem.tag 	== cat_global.log_conf_ID):
				log_conf = elem.text
			elif (elem.tag 	== cat_global.hw_model_ID):
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
			logger.critical("Catinator Init - Series: %s  Model: %s" % (version, hw_model))
			logger.critical("Logging config file: %s" % log_conf)
			logger.critical("Catinator start up sequence...")
			logger.info("Step 1: Read in the config file and parse it ... complete")
			
			logger.info("Step 2: Populate system data structures for service initialization")
			catinator = catconf.catinator_type(config_root, logger)
			
			logger.info("Step 3: setup networking")
			#do later; not needed for PoC
			
			logger.info("Step 4: setup DDNS")
			#do later; not needed for PoC
			
			logger.info("Step 5: Check for and start required system services")
			return_value += catinator.test_services(logger)
			if (return_value != 0):
				logger.warning("%s services could not be started" % return_value)
			
			try:
				logger.info("Step 6: Fork catinatord, validate process, save PID")
				cmd_output = subprocess.getoutput(cat_global.path_to_catinatord + " --start -c " + conf_file)
				if (cmd_output != ""):
					logger.error("catinatord at %s could not be started" % cat_global.path_to_catinatord)
			except Exception as err:
			    logger.exception("catinatord at %s could not be started" % cat_global.path_to_catinatord)
					
			# Startup complete!!  return status
			if (return_value != 0):
				logger.critical("Critical Error: Start up failed")
			else:
				logger.critical("Start up completed!")
				logger.critical(cat_global.tag_line)  # Are you Rory McQuaid??

	return (return_value)


# Wrapper for standalone functional script implementation
#
# Usage: catinator_init.py -c <configuration file>
#		 catinator_init.py -h
# Ex: <python> catinator_init.py -c /etc/catinator/catinator.conf.xml
#
# Command line options:
#		<configuration file> - path to catinator.conf.xml
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
	Usage = """Usage: catinator_init.py -c </path/configuration file>
Ex: <python3> catinator_init.py /etc/catinator/catinator.conf.xml"""

	#Variables
	conf_file = ""   # path to configuration file
	return_value = 0 # Return value assumes success
	
	#parse arguments
	if (len(argv) <= 0):   #Test to see if we have arguments...
		print("Not enough arguments")
		return_value = 2  #Not enough args
	else:    # Yes, we do have proper number of args
		try: #Try to get the options
			opts, args = getopt.getopt(argv,"hc:")
		except Exception as err:  #Print an error if occurs
			print("Argument Error: ", err)  
			return_value = 2
		else:
			if (not opts): #Any recognized opts present in argv?
				print("No recognized arguments")
				return_value = 2    # No, do not process
			else:  #We have valid options in argv
				for opt, arg in opts:		#Test the options in the args
					if   (opt == "-h"):		#Help arg, just print usage
						return_value = 1
					elif (opt == "-c"):		#-c is the "conf" file
						conf_file = arg     # arg is present, store it
					else:
						print("Unknown argument")
						return_value = 2	# unknown option
				
				if (return_value != 0):		#Argv processing not ok?
					conf_file = ""			#Clear the conf_file
				else:
					#got a valid argument, initialize The Catinator!!
					return_value = catinator_init(conf_file)
					
	#Check return value, if not success, print Usage
	if (return_value != 0):
		print (Usage)			# Catch any errors and print Usage
	else:
		print (cat_global.tag_line)		# It's time to meow... :)
	
	return (return_value)


# if invoked from command line and this module is 'main', then call main
if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))
