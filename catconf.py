#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  catconf.py
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


#Imports
import inspect						# Stack inspection for logging
import xml.etree.ElementTree as ET  # XML parser library
import logging						# Nothing happens in production w/o logs
import logging.config   			# logging lib conf file processing
import logging.handlers				# lib for rotating logfiles & syslog
import RPi.GPIO as GPIO				# GPIO library
import time							# time library for sleep()
from time import sleep
import ipaddress					# ipaddress module
import subprocess					# sub process forking lib
import os							# for file handling
import cat_global
import catnotify					# notification classes
import catcam						# camera class
from daemon3x import daemon			# this is what turns us into a proper daemon
import sys, signal					# for signal handling within the daemon

#Constants
logger_ID				= "catinatord"

#Module Variables

#Classes and methods/functions

# Door class  -> contains the door GPIO pins, the door state, and 
# methods to read the values.
class door_type:

			#Class Members
		
			door_ID    		= "door"
			door_number_ID 	= "number"
			gpio_ID			= "gpio"
			up_down_ID		= "up_down"
			number			= 0
			gpio			= 0
			up_down			= GPIO.PUD_UP
			door_open		= False  #Inits all doors to closed
			
			#Class door_type contructor	
			def __init__(self, config_tree, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("XML Object: %s" % config_tree)
				
				#Start function
				
				#Capture the door number
				if (config_tree.tag != self.door_ID):
					logger.error("Bad element tag; does not equal door")
					return_value = 1
				else:
					self.number = int(config_tree.attrib[self.door_number_ID])
					logger.debug("Number %s" % self.number)					
				
					#Iterate through the XML config tree and populate the door config
					#This is just a big case statement that populates the class members
					# PS: look for a better way to do this one day... there has to be
					for elem in config_tree.iter():
						if 	(elem.tag == self.gpio_ID):
							self.gpio = int(elem.text)
							logger.debug("gpio %s" % self.gpio)
						elif (elem.tag == self.up_down_ID):
							if (elem.text.upper() == "UP"):
								self.up_down = GPIO.PUD_UP
							else:
								self.up_down = GPIO.PUD_DOWN
							logger.debug("Pull up/down %s" % elem.text.upper())
															
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

#  Read the configured pin for the given door and return if door is open or closed
#  Also, update the door_open state value for the door at the same time
			def read(self, logger):
				#Constants
				
				#Variables
				return_value = 0
				pin_value    = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
							
				#Start function
				
				#read the GPIO input channel
				pin_value = GPIO.input(self.gpio)
				logger.debug("Read %s from pin %s with pull up/down set to %s" %
							(return_value, self.gpio, self.up_down))
											
				# Is the door open or closed?
				# This next conditional makes use of an assumption:
				# If the gpio pin state is equal to its pull up/down value,
				# then the switch controlling the door is OPEN
				# and, in the catinator, an open switch is a closed door
				# and a closed switch is an open door
				# this way, the pull up/down settings can be reversed for
				# different h/w configs in order to conserve power
				# default setting is PUD_UP where the open switch is
				# conserving power by being pulled up.
				# the catinator is actually assumed to be in the CLOSED
				# state the majority of time.  (which it is, if used propoerly)
				if (((self.up_down == GPIO.PUD_UP) and (pin_value == GPIO.HIGH)) or
				    ((self.up_down == GPIO.PUD_DOWN) and (pin_value == GPIO.LOW))):
					return_value = self.door_open = False  	#CLOSED door
				else:
					return_value = self.door_open = True	#open or ARMED door			

				logger.debug("Setting door_open to %r" % return_value)

				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return (return_value)


# Trapdoors class  -> contains a list of door type members and implements
# the methods necessary to read the individual doors and determine if
# the catinator trap is ARMED, CLOSED, or JAMMED.
#  ARMED is when all doors are open
#  CLOSED is when all doors are closed
#  JAMMED is when at least one door is open and at least one door is closed
class trapdoors_type:
			#Trap doors
			trapdoors_ID 	= "trapdoors"
			door_ID			= "door"
			door_list = []	# The list of door objects
			total_doors		= 0
			cond_state		= cat_global.CLOSED # default door condition state
							# Can be CLOSED, ARMED, or JAMMED

			#Class trapdoors_type contructor	
			def __init__(self, config_tree, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("XML Object: %s" % config_tree)
				
				#Start function
				
				#Capture the door number
				if (config_tree.tag != self.trapdoors_ID):
					logger.error("Bad element tag; does not equal trapdoors")
					return_value = 1
				else:
					# Iterate through the trap doors and build the list
					for elem in config_tree.iter():
						if (elem.tag == self.door_ID):
							logger.debug("Location: %s" % elem.tag)
							self.door_list.append(door_type(elem, logger))
							self.total_doors += 1
							logger.debug("trapdoors list: %s" % self.door_list)

					logger.debug("total doors: %s" % self.total_doors)
															
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

# Method: Initialize the GPIO functions within the systems
# Return of 0 if success, return non zero if failure
			def GPIO_init(self, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
							
				#Start function
				
				#Debug log the GPIO version to the log to make sure
				#enviroment is OK.
				logger.debug("GPIO Version: %s", GPIO.VERSION)
				
				#Setup the GPIO mode
				logger.info("Setting up GPIO to BOARD mode")
				GPIO.setwarnings(False)		# Disable warnings in case catinatord restarted on bad exit
				GPIO.setmode(GPIO.BOARD)	# Pins in board mode are easier to count ;-)
						
				# Loop though trapdoors and set door pin as input and set the pull up/down resistor
				for door in self.door_list:
					#Set the input pin and pull up/down resistor for the door
					logger.info("Setting up door %s to input on GPIO pin %s with pull up/down resistor as %s" % 
					(door.number, door.gpio, door.up_down))
					GPIO.setup(door.gpio,GPIO.IN, pull_up_down=door.up_down)

				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return (return_value)


# Method: Get the condition of the catinator doors
# Return one of three conditions, CLOSED, ARMED, or JAMMED
# Raise an exception if the door.read()s return an undefined value
# since we can't return an error
			def get_cond(self, logger):
				#Constants
				
				#Variables
				return_value = 0
				door_cond_accumulator = 0 # accumulates the door conditions

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
							
				#Start function
				
				#loop through the doors, read, and get their door_open states
				#convert the true/false booleans to a 0 or 1 integer and add
				for door in self.door_list:
					door_cond_accumulator += int(door.read(logger))
					logger.debug("Sum of door totals: %s" % door_cond_accumulator)
				
				# Check the accumlator with this logic
				# A 0 value in the accumlator is a CLOSED condition (all doors closed)
				# A value equal to the number of doors in the system is an ARMED condition (all doors open)
				# Anything between 0 < x < number of doors is a JAMMED condition (some open, some closed)
				if   (door_cond_accumulator == 0):
					return_value = cat_global.CLOSED
				elif (door_cond_accumulator == self.total_doors):
					return_value = cat_global.ARMED
				elif ((door_cond_accumulator > 0) and (door_cond_accumulator < self.total_doors)):
					return_value = cat_global.JAMMED
				else:
					# The door accumlator has read a number outside the boundary range. That really isn't possible.
					# Something bad has happened, so, raise an exception and exit the daemon
					raise Exception("get_cond() has accumulated a value outside the total doors bound: door_cond_accumulator %s total_doors %s " %
					(door_cond_accumulator, self.total_doors))
					return_value = cat_global.JAMMED

				logger.debug("get_cond(): door_cond_accumulator %s total_doors %s condition %s" %
					(door_cond_accumulator, self.total_doors,cat_global.state_str[return_value]))

				#Set the trapdoors object condition state as final step
				self.cond_state = return_value

				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % cat_global.state_str[return_value])
				return (return_value)
				
# Method - The trapdoors class clean up function; runs right before destructors at exit
			def cleanup(self, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
							
				#Start function
				logger.info("Cleaning up GPIO")
				GPIO.cleanup() # clean up GPIO			

				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return (return_value)



# Network Interface class  -> contains simple network members and manipulation
# methods.
class interface_type:
			
			#Class Members

			DHCP_ID    = "DHCP"
			dhcp	   = False
			ip_addr_ID = "ip_addr"
			netmask_ID = "netmask"
			gateway_ID = "gateway"
			dns_ID     = "dns"
			ip_addr_str = ""
			netmask_str = ""
			gateway_str = ""
			dns_str     = ""
			ip_addr     = 0
			netmask     = 0
			gateway     = 0
			dns         = 0

			#class interface_type constructor
			def __init__(self, config_tree, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("XML Object: %s" % config_tree)
				
				#Start function
				
				#Iterate through the XML config tree and populate the interface config
				#This is just a big case statement that populates the class members
				# PS: look for a better way to do this one day... there has to be
				for elem in config_tree.iter():
						if   (elem.tag == self.ip_addr_ID):
							self.ip_addr_str = elem.text
							logger.debug("ip_addr %s" % self.ip_addr_str)
						elif (elem.tag == self.netmask_ID):
							self.netmask_str = elem.text
							logger.debug("netmask %s" % self.netmask_str)
						elif (elem.tag == self.gateway_ID):
							self.gateway_str = elem.text
							logger.debug("gateway %s" % self.gateway_str)				
						elif (elem.tag == self.dns_ID):
							self.dns_str = elem.text
							logger.debug("dns %s" % self.dns_str)
									
				# Convert string values to unsigned 32 bit integers
				if (self.ip_addr_str != self.DHCP_ID):
					ipaddr  = ipaddress.ip_address(self.ip_addr_str)
					netmask = ipaddress.ip_address(self.netmask_str)
					gateway = ipaddress.ip_address(self.gateway_str)
					dns     = ipaddress.ip_address(self.dns_str)
				else:
					self.dhcp = True
				
				logger.debug("dhcp %r" % self.dhcp)
									
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__


# Catinator class  -> main system data structure
# This is a derivation and overload of the daemon class from daemon3x
# The 
class catinator_type(daemon):

		#Class Members

		#platform/hardware
		ID				= "Catinator"
		series_ID 		= "series"
		series			= "000" # Catinator series number designates app version
		model_ID 		= "hardware"
		model_attrib_ID = "model"
		model			= "101" # model designates trap doors, eg. 101 = 1 doors, 102 = 2 doors, etc... -->
		platform_ID		= "platform"
		platform		= "rpiA" # values = rpi0, rpiA, rpiB, rpi2, rpi3, etc...

		
		#Trap doors
		trap_state		= cat_global.CLOSED  #defaults trap state to closed
		trapdoors_ID 	= "trapdoors"
		trapdoors		= None				 #pointer to list of trap doors
		sleep_interval_ID = "sleep"
		sleep_interval	= 2					 #default polling interval
		path_to_catinatord_state_ID = "state"
		path_to_catinatord_state = "/var/run/catinatord.state"
		#defaults the state file in case one does not exist in config
		state_file		= None				 #file object for saving state
		pidfile			= cat_global.path_to_catinator_pid
		
		#Required System Services
		services_ID		= "depend"
		services 		= []   # The list of strings of services
			
		#Interfaces
		eth0 			= True		#eth0 boolean
		eth0_ID 		= "eth0"
		_eth0_ID 		= "eth0_"
		wlan0 			= False		#wlan0 boolean
		wlan0_ID		= "wlan0"
		_wlan0_ID		= "wlan0_"
		usbmodem		= False		#usbmodem boolean
		usbmodem_ID		= "usbmodem"
		_usbmodem_ID	= "usbmodem_"
		interfaces_ID 	= "networking"
		interfaces      = []		# The list of interfaces
		
		#More hardware
		camera_ID 		= "camera"
		camera__ID 		= "camera_"
		camera_attrib_ID = "id"
		camera_enabled	= False	#Boolean for camera presence
		camera_id 		= "generic_usb"  #String of camera type
		camera			= None			#Camera object
		
		battery_ID 		= "installed"
		battery			= False  #Boolean for Battery presence
		capacity_ID 	= "capacity"
		battery_capacity = 0 	#counter for capacity
		capacity_unit_ID = "unit"
		battery_unit 	= "mAh"    #string for battery units
		
		night_mode_ID 	= "night_mode"
		night_mode 		= False #Boolean for night mode
		power_off_ID 	= "power_off"
		power_on_ID 	= "power_on"
		poweroff_cmd 	= "sudo /usr/bin/hub-ctrl -h 0 -P 2 -p 0"
		poweron_cmd 	= "sudo /usr/bin/hub-ctrl -h 0 -P 2 -p 1"
		sleep_timer_ID 	= "sleep_timer"
		sleep_timer		= 10 # default, but configurable

		#Notifications
		notifications_ID= "notifications"
		notify 			= None		#ptr to notification object

		#logging info
		log_conf_ID		= "logconf"
		log_conf		= "/etc/catinator/catinator.log.conf"
		logger			= None  #for signal handlers

#Catinator type constructor				
		def __init__(self, config_tree, logger):
			#Constants
			
			#Variables
			interface_elem = None
			return_value = 0

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
			logger.debug("XMl Object: %s" % config_tree)
			
			#Start function
			self.logger = logger
			
			#Iterate through the XML config tree and populate the catinator config
			#This is just a big case statement that populates the class members
			# PS: look for a better way to do this one day... there has to be
			for elem in config_tree.iter():
					if   (elem.tag == self.ID):
						self.series = elem.attrib[self.series_ID]
						logger.debug("Series %s" % self.series)
					elif (elem.tag == self.model_ID):
						self.model = elem.attrib[self.model_attrib_ID]
						logger.debug("Model %s" % self.model)
					elif (elem.tag == self.platform_ID):
						self.platform = elem.text
						logger.debug("Platform %s" % self.platform)
					elif (elem.tag == self.eth0_ID):
						self.eth0 = (elem.text == "TRUE")
						logger.debug("eth0 %r" % self.eth0)
					elif (elem.tag == self.wlan0_ID):
						self.wlan0 = (elem.text == "TRUE")
						logger.debug("wlan0 %r" % self.wlan0)				
					elif (elem.tag == self.usbmodem_ID):
						self.usbmodem = (elem.text == "TRUE")
						logger.debug("usbmodem %r" % self.usbmodem)
					elif (elem.tag == self.camera_ID):
						self.camera_enabled = (elem.text == "TRUE")
						logger.debug("camera %r" % self.camera)
						self.camera_ID = elem.attrib[self.camera_attrib_ID]
						logger.debug("camera_ID %s" % self.camera_ID)
					elif (elem.tag == self.battery_ID):
						self.battery = elem.text
						logger.debug("battery %s" % self.battery)
					elif (elem.tag == self.capacity_ID):
						self.battery_capacity = int(elem.text)
						logger.debug("battery capacity %s" % self.battery_capacity)					
						self.battery_unit = elem.attrib[self.capacity_unit_ID]
						logger.debug("capacity units %s" % self.battery_unit)
					elif (elem.tag == self.night_mode_ID):
						self.night_mode = (elem.text == "TRUE")
						logger.debug("night mode %r" % self.night_mode)				
					elif (elem.tag == self.power_off_ID):
						self.poweroff_cmd = elem.text
						logger.debug("USB power off Cmd %s" % self.poweroff_cmd)					
					elif (elem.tag == self.power_on_ID):
						self.poweron_cmd = elem.text
						logger.debug("USB power on Cmd %s" % self.poweron_cmd)					
					elif (elem.tag == self.sleep_timer_ID):
						self.sleep_timer = int(elem.text)
						logger.debug("USB power sleep timer %s sec" % self.sleep_timer)
					elif (elem.tag == self.log_conf_ID):
						self.log_conf = elem.text
						logger.debug("logconf %s" % self.log_conf)
					elif (elem.tag == self.sleep_interval_ID):
						self.sleep_interval = int(elem.text)
						logger.debug("GPIO polling sleep interval is %s seconds" % self.sleep_interval)
					elif (elem.tag == self.path_to_catinatord_state_ID):
						if (elem.text != ""):
							self.path_to_catinatord_state = elem.text
						else:
							logger.debug("No state file path, defaulting...")
						logger.debug("State file path %s" % self.path_to_catinatord_state)
					elif (elem.tag == self.interfaces_ID):
						interface_elem = elem
					elif (elem.tag == self.trapdoors_ID):
						logger.debug("Building trapdoors...")
						self.trapdoors = trapdoors_type(elem, logger)
						# Check doors against model #, they should match
						if (self.trapdoors.total_doors != (int(self.model) % cat_global.model_mask)):
							logger.warning("Total doors configured do not match model designation!")
						else:
							logger.debug("Total doors configured matches model") 
					elif (elem.tag == self.services_ID):
						self.services.append(elem.text)
					elif (elem.tag == self.notifications_ID):
						logger.debug("Building notification structure")
						self.notify = catnotify.notification_type(elem, logger)
					elif (elem.tag == self.camera__ID):
						logger.info("Initializing camera...")
						self.camera = catcam.camera_type(self.camera_enabled, elem,logger)

			#log service list
			logger.debug("service list %s" % self.services)
							
			# Iterate through the networking interfaces and build the list
			for sub_elem in interface_elem.iter():
				if ((sub_elem.tag == self._eth0_ID) or
				    (sub_elem.tag == self._wlan0_ID) or
				    (sub_elem.tag == self._usbmodem_ID)):
					logger.debug("Location: %s" % sub_elem.tag)
					self.interfaces.append(interface_type(sub_elem, logger))
					logger.debug("interface list: %s" % self.interfaces)

			#Open the catinatord state file
			try:
				logger.info("Opening state file: %s" % self.path_to_catinatord_state)
				self.state_file = open(self.path_to_catinatord_state, "w")
			except Exception as err:
				logger.exception("Cannot open state file: %s" % self.path_to_catinatord_state)
	
			#Lastly, we're a daemon, make sure we behave nicely with signals
			logger.debug("Setting up signals...")
			signal.signal(signal.SIGINT, self.catch_signal)
			signal.signal(signal.SIGTERM, self.catch_signal)
									
			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			#don't return, because we're an __init__

# Method:Start a required system service
# Return of 0 is success; return of 1 is failure
		def start_service(self, service, logger):
			#Constants
			
			#Variables
			return_value = 0
			cmd_output   = ""

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
			logger.debug("Service: %s" % service)
						
			#Start function
			
			#Check that the list of services is not blank
			if (service == ""):
				logger.error("no service specified")
				return_value = 1
			else:
				#Call the OS to start the service
				cmd_output = subprocess.getoutput(
				cat_global.start_service_command % service)
				
				#Now, check the service for status
				cmd_output = subprocess.getoutput(
				cat_global.check_service_command % service)
				
				#Is service running?
				if (cmd_output != cat_global.active_service_response):
					#No, service isn't running
					logger.warning("service %s did not start" % service)
					return_value = 1
				else: #Yes, return Success
					logger.info("service %s started" % service)
					return_value = 0
			
			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)

# Method: Check for a single required system service
# Return of 0 is success (Active); return of 1 is failure (Not Active)
		def test_service(self, service, logger):
			#Constants
			
			#Variables
			return_value = 0
			cmd_output   = ""

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
			logger.debug("Service: %s" % service)
						
			#Start function
			
			#Check that the list of services is not blank
			if (service == ""):
				logger.error("no service specified")
				return_value = 1
			else:
				#Call the OS to get the service status
				cmd_output = subprocess.getoutput(cat_global.check_service_command % service)
				
				#Is service running?
				if (cmd_output != cat_global.active_service_response):
					#No, service isn't running
					logger.warning("service %s is not active and running" % service)
					return_value = 1
				else: #Yes, return Success
					logger.debug("service %s is active and running" % service)
					return_value = 0
			
			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)

# Method: Check for required system services and restart, if necessary
# Return the number of failed services.  Return of 0 is success.
		def test_services(self, logger):
			#Constants
			
			#Variables
			return_value = 0

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
						
			#Start function
			
			#Check that the list of services is not blank
			if (self.services == []):
				logger.warning("service dependency list is empty")
			else:
				#iterate through service list and check those services
				for service in self.services:
					is_running = self.test_service(service, logger)
					if (is_running != 0): #if service not running, try to start the service
						logger.info("starting service %s" % service)
						is_running = self.start_service(service, logger) 
						if (is_running != 0): #if still not running, fail and warn
							logger.error("cannot start service %s" % service)
							return_value += 1  #increament value of failed services
						else:
							logger.info("service %s has started" % service)
					else:
						logger.info("service %s is running" % service)
			
			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)

# Method - Save the state of the catinator to internal memory and disk
		def save_state(self, state, logger):
			#Constants
			
			#Variables
			return_value = 0
			state_file = None

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
			logger.debug("State: %s" % cat_global.state_str[state])
						
			#Start function
				
			logger.debug("Saving state to trap_state and %s" % self.path_to_catinatord_state)
			self.trap_state = state  # save state to the catinator memory object

			# save the state to the state file on disk
			try:
				#reset to head of file
				self.state_file.seek(0)
				
				#save the state, either CLOSED, ARMED, JAMMED, or JAM_REPORTED
				self.state_file.write("%s\n" % cat_global.state_str[state])
				logger.debug(cat_global.state_str[state])

				#Also save the door states as well
				for door in self.trapdoors.door_list:
				  self.state_file.write("door %s: state: %s\n" % (door.number,cat_global.state_str[int(door.door_open)]))
				  logger.debug("door %s: state: %s" % (door.number,cat_global.state_str[int(door.door_open)]))

			except Exception as err:
				logger.exception("Cannot write to state file object: %s" % self.state_file)

			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)

# Method - turns USB power on the RPi on or off based upon the state and night mode
		def change_power_state(self, on_off, logger, sleep_timer = 0):
			#Constants
			
			#Variables
			return_value = 0
			power_ctl_cmd = self.poweron_cmd
			cmd_output    = ""

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
			logger.debug("On/Off: %s" % on_off)
			logger.debug("Sleep Timer: %s" % sleep_timer)
			logger.debug("Night Mode: %r" % self.night_mode)					

			#Start function

			# Assign the proper power control string based upon the state
			if((on_off == "off") and (self.night_mode == True)):
				logger.info("Turning off USB power...")
				power_ctl_cmd = self.poweroff_cmd  #only turn off USB if we are in night mode
			else:
				logger.info("Turning on USB power...")
				power_ctl_cmd = self.poweron_cmd   # all other states, leave USB on

			#execute the command				
			logger.debug("Executing power control command: %s" % power_ctl_cmd)
			try:
				cmd_output = subprocess.getoutput(power_ctl_cmd)
				logger.debug("Power control command output: %s" % cmd_output)
			
			except Exception as err:
				logger.exception("Cannot execute power control command: %s" % power_ctl_cmd)
				return_value = 1
			
			if (sleep_timer > 0):  
				logger.info("Waiting %s sec for USB power to take affect..." % sleep_timer)
				sleep(sleep_timer) #let power changes take affect, sleep a few intervals

			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)

#Method - catinator signal handler
		def catch_signal(self, signum, frame):
			self.cleanup(0, self.logger)


# Method - The catinator class clean up function; runs right before destructors at exit
		def cleanup(self, return_value, logger):
			#Constants
			
			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
						
			#Start function
			
			#Clean up any GPIO artifacts related to the trap doors
			logger.debug("Cleaning up the trapdoors/GPIO")
			return_value += self.trapdoors.cleanup(logger)
			
			try:
				#Close the state file
				if (self.state_file != None):
					self.state_file.close()

				#Remove the state file
				logger.info("Removing the state file: %s" % self.path_to_catinatord_state)
				if (os.access(self.path_to_catinatord_state, os.R_OK)): #test for state file
					os.remove(self.path_to_catinatord_state)  			#remove state file
				else:
					logger.debug("State file not found")
		
			except Exception as err:
				logger.exception("Cannot close state file object: %s" % self.state_file)
				return_value += 1
				
			# Shutdown/Termination
			if (return_value != 0):
				logger.critical("Critical Error shutdown")
			else:
				logger.critical("Normal Shutdown complete")
					
			logger.critical(cat_global.tag_line2)  #C-Ya!!
			print(cat_global.tag_line2)
			sys.exit(return_value)	# and... we're gone...

			return (return_value)
			
			

# Method: FSM - Finite State Machine
# Return of 0 if success, return non zero if failure
#
# Implements the Catinator FSM
# There are many, many ways to implementan a FSM, arrays of states and actions,
# lists of states and actions tuples, pointers to state objects, state
# tree/network, as an object FSM where you overload the state machine methods, etc, etc...
#
# We're doing it the old fashioned way, with previous state, next state,
# and a trigger event we call the "trapdoors condition".  We use simple
# boolean logic to determine the next state based on the previous state
# and the current door condition. 
#
# Enter the function and do...
#		a. Poll GPIO ports/read door state
#		b. if doors go from close to open state, send "Armed" notifications
#		c. if doors go from open to close state, send "Sprung" notifications
#			i.  Take a picture from webcam and attach to notifcations
#		d. if not all doors close at same time, send "Jammed" notifications
		def FSM(self, logger):
			#Constants
			
			#Variables
			return_value = 0
			next_state = previous_state = self.trap_state	# Local copy of next & previous state
			current_cond = cat_global.CLOSED				# Default condition is always CLOSED

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
						
			#Start function
			logger.debug("Previous trap state was: %s" % cat_global.state_str[previous_state])

			#		a. Poll GPIO ports/read door condition
			current_cond = self.trapdoors.get_cond(logger)
			logger.debug("Reading current trap condition to be: %s" % cat_global.state_str[current_cond])
			
			#FSM: Determine next state/action based upon door condition and previous state
			#		b. if doors go from close to open state, send "Armed" notifications
			#		c. if doors go from open to close state, send "Sprung" notifications
			#			i.  Take a picture from webcam and attach to notifcations
			#		d. if not all doors close at same time, send "Jammed" notifications
			if  ((current_cond == cat_global.ARMED)  and
				 (previous_state != cat_global.ARMED)):
					logger.info("Trap state changed: CLOSED/JAMMED --> ARMED")
					return_value = self.change_power_state("off", logger)  #power USB off; no wait
					return_value += self.notify.send(current_cond, None, logger)
					next_state = cat_global.ARMED
					logger.info("State complete.")
			elif((current_cond == cat_global.CLOSED) and
				 (previous_state != cat_global.CLOSED)):
					logger.info("Trap state changed: ARMED/JAMMED --> CLOSED")
					return_value = self.change_power_state("on", logger, self.sleep_timer)  # power USB on and wait
					return_value += self.camera.take_picture(logger)		# Take a picture of what is in the trap
					return_value += self.notify.send(current_cond, self.camera, logger)
					next_state = cat_global.CLOSED
					logger.info("State complete.")
			elif((current_cond == cat_global.JAMMED) and
				 (previous_state == cat_global.ARMED)):
					logger.info("Trap state changed: ARMED --> JAMMED; polling one more period")
					return_value = 0 # No notifcations
					next_state = cat_global.JAMMED
					logger.info("State complete.")
			# The inclusion of a JAM_REPORTED state has the affect of polling one more period before reporting a jam
			elif((current_cond == cat_global.JAMMED) and
				 (previous_state == cat_global.JAMMED)):
					logger.info("Trap state changed: JAMMED --> JAM_REPORTED")
					return_value = self.change_power_state("on", logger, self.sleep_timer)  # power USB on and wait
					return_value += self.camera.take_picture(logger)		# Take a picture of what is in the trap
					return_value += self.notify.send(current_cond, None, logger)
					next_state = cat_global.JAM_REPORTED
					logger.info("State complete.")
			else:
					logger.debug("No trap state change detected; doing nothing")
					return_value = 0
					next_state = previous_state
					
			# Save the trap state for all to see
			logger.debug("Setting next trap state to %s" % cat_global.state_str[next_state])
			self.save_state(next_state, logger)
			
			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)			

# Function: run() - an overload of the daemon class run() method
# Input:  "conf_file" - full path to the configuration file
#
# Output: "return_value" - 0, success; non-0, failure
#
# Purpose:
#
# This function encompasses the catinator main loop sequence:
#  1) Load config
#  		a. Setup GPIO ports
#		b. read in notifcation templates
#		c. Initialize notification objects
#  2) Enter the main function loop, call the FSM in do-while...
#		a. Poll GPIO ports/read door state
#		b. if doors go from close to open state, send "Armed" notifications
#		c. if doors go from open to close state, send "Sprung" notifications
#			i.  Take a picture from webcam and attach to notifcations
#		d. if not all doors close at same time, send "Jammed" notifications
#		e. Wait interval, then loop back to top
#  3) Clean up/Exit gracefully upon OS signal/request
#  4) Catch all exceptions and send to logs
#
# This function is standalone and can be imported from this module 
# into other python modules.
#
# Tested in Python 2.7.9 on "Jessie" Raspian 4.4.13-v7+ #894
# with Motion 3.2.12+git20140228
#
		def run(self, logger):
			
			#Variables
			return_value = 0  # Return value assumes success
			
			logger.critical("Catinatord succesfully forked...")			

			#Initialize USB power state
			logger.info("Initializing USB power state")
			if (self.change_power_state("on", logger) != 0):
				logger.error("Cannot initialize USB power")
				return_value = 1
				
			#Setup GPIO and notifications
			logger.info("Setting up GPIO and notifications")
			if (self.trapdoors.GPIO_init(logger) != 0):
				logger.critical("Cannot initialize GPIO ports!!  Exiting...")
				return_value = 2
			else:
				# Start main loop
				logger.critical("Catinator started")
				try:
					#Call the FSM to poll the GPIO then wait the sleep interval...
					while (return_value == 0):
						return_value = self.FSM(logger)
						sleep(self.sleep_interval)
				
				except Exception as err:  #Catch any untrapped exception during FSM execution and log it
					logger.exception("Exception during FSM loop")
					print("Exception during FSM loop: %s" % err)
					return_value = 3

				finally:  # this block will run no matter how the try block exits
					catinator.cleanup(return_value, logger)

			#Graceful exit
			catinator.cleanup(return_value, logger)

			return (return_value)



def main():
	
	return 0

if __name__ == '__main__':
	main()

