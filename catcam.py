#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  catcam.py
#  
#  Copyright 2016 James M. Coulthard <james.m.coulthard@gmail.com>
#  
#  This module contains the notifcation class and methods of the
#  catinator application.  The class _init_ reads in the 
#  contents of the etree that is passed to it and populates internal
#  data structures.  The class also has a initialize() method that
#  tests for required sendmail daemon enviroment.
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
import inspect						# Stack inspection for logging
import xml.etree.ElementTree as ET  # XML parser library
import logging						# Nothing happens in production w/o logs
import logging.config   			# logging lib conf file processing
import logging.handlers				# lib for rotating logfiles & syslog
import os,time						# for file handling
import shutil						# high level file operations
from os.path import basename
import mjpegframegrab
from mjpegframegrab import html_jpeg_frame_grab	#handles connecting to motion and taking the picture
import cat_global


# camera class   
#	Must save to filename to include as image in encoding html and plain text attachments
#   Will take picture first in blocking manner before sending notification
#		this is just a wrapper class/method on the html_jpeg_frame_grab() module
#	class has to handle presence/no presence of camera
# methods:
#	_init_()
#	take_picture()  --> take picture save to file, if camera is enabled, otherwise, save blank picture to file
#						will block while taking picture
#	read_picture()  --> reads the picture file in from capture file, for use in MIME attach to plain text email

class camera_type:

			#Class Members
			
			camera__ID					= "camera_"
			capture_ID					= "capture_file"
			nopic_ID					= "nopic_file"
			motion_ID					= "motion_url"
			token_ID					= "content_identifier"
			scan_len_ID					= "scan_buffer"
			capture_file				= "/etc/catinator/templates/image/catpic.jpg"	# default path to capture file
			nopic_file					= "/etc/catinator/templates/image/nopic.jpg"	# default path to blank picture
			motion						= "http://127.0.0.1:8081/"	# default motion server URL
			content_token				= "Content-Length" #default content token on motion server
			scan_len					= 1024			# default input buffer length
			enabled						= False			# camera enabled boolean
						
		
		
#Class camera_type contructor	
			def __init__(self, enabled, config_tree, logger):
				#Constants
				
				#Variables
				return_value = 0
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("enabled: % r" % enabled)
				logger.debug("XML Object: %s" % config_tree)
				
				#Start function
				
				#Determine if members can be parsed
				if (config_tree.tag != self.camera__ID):
					logger.error("Bad root element tag; does not equal camera_")
				else:
					logger.debug("Loading camera settings")
				
					#Save camera enable/disable state
					self.enabled = enabled
					if (self.enabled):
						logger.debug("Camera is enabled")
					else:
						logger.debug("Camera is disabled")
						
					#Iterate through the XML config tree and populate the config
					#This is just a big case statement that populates the class members
					# PS: look for a better way to do this one day... there has to be					
					for elem in config_tree.iter():
						if (elem.tag == self.capture_ID):
							self.capture_file = elem.text
							logger.debug("Image capture file: %s" % self.capture_file)
						elif (elem.tag == self.nopic_ID):
							self.nopic_file = elem.text
							logger.debug("No picture file: %s" % self.nopic_file)
						elif (elem.tag == self.motion_ID):
							self.motion = elem.text
							logger.debug("Motion Server URL: %s" % self.motion)
						elif (elem.tag == self.token_ID):
							self.content_token = elem.text
							logger.debug("Content Token: %s" % self.content_token)
						elif (elem.tag == self.scan_len_ID):
							self.scan_len = int(elem.text)
							logger.debug("Scan Buffer Length: %s" % self.scan_len)
					
					logger.debug("Finished loading camera settings")
																				
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

#Method: take_picture - opens a file for capturing on disk, and then connects to the motion server
#URL to grab a picture from the stream.  Saves the retrieved buffer to the capture file.
#If camera is not enabled, simply copies the blank no picture file to the capture file
#Acts as wrapper method to the mjpegframegrap module.  Blocks while retrieving the jpeg.
			def take_picture(self, logger):
				#Constants
				
				#Variables
				return_value = 0
				foo			 = None  #arbitrary file object
				pic_buffer	 = None  #picture buffer
				new_file	 = ""    #filename of copy of picture file
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)

				#Start function
				try:
					if (not os.access(self.nopic_file, os.R_OK)): #test read of file
						logger.error("Cannot open no picture file: %s" % self.nopic_file)
						return_value = 1
				except Exception as err:
						logger.exception("Cannot open no picture file: %s" % self.nopic_file)
						return_value = 1
				else:
					try:
						if (not self.enabled):
							logger.debug("Camera is not enabled, copying no picture file")
							shutil.copy2(self.nopic_file, self.capture_file) #copy2() maintains file metadata
						else:
							#Build the new file name for backup
							new_file = self.capture_file + "." + time.strftime("%m-%d-%Y_%H-%M-%S", time.localtime())  #Append time to new file name
							logger.debug("Saving old picture file to: %s" % new_file)

							#Backup the old picture file
							shutil.copy2(self.capture_file, new_file) #copy2() maintains file metadata

							#Open the capture file to its head position
							logger.debug("Opening to write to capture file: %s" % self.capture_file)
							foo = open(self.capture_file, "wb")  # open a binary file for writing
							
							# Smile!! Take a picture
							logger.info("Taking a picture...")

							#Use mjpegframegrap module to capture a single picture from the motion server
							#This is implementation specific and assumes jpeg format from motion; call blocks
							pic_buffer = html_jpeg_frame_grab(self.motion, self.content_token,
															self.scan_len,
															mjpegframegrab.start_of_jpeg_token,
															mjpegframegrab.end_of_jpeg_token)
							
							#Write the picture to the file
							logger.debug("Saving the picture...")						
							foo.write(pic_buffer)
							
							#close the file
							foo.close()
							logger.debug("Success...")

						#If we get here, then all file ops were successful
						return_value = 0
					except Exception as err:
						logger.exception("Cannot process capture file: %s" % self.capture_file)
						return_value = 1
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return(return_value)

#Method: read_picture() - read the capture file from disk and return contents in buffer
			def read_picture(self, logger):
				#Constants
				
				#Variables
				return_value = None
				foo			 = None  #arbitrary file object
				pic_buffer	 = None  #picture buffer
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)

				#Start function
				try:
					if (not os.access(self.capture_file, os.R_OK)): #test read of file
						logger.error("Cannot open picture file: %s" % self.capture_file)
						return_value = None
						return(return_value)
				except Exception as err:
						logger.exception("Cannot open picture file: %s" % self.capture_file)
						return_value = None
				else:
					try:
						logger.debug("Opening to read from capture file: %s" % self.capture_file)
							
						#Open the file
						foo = open(self.capture_file, "rb")  # open a binary file for reading
							
						#Read the picture from the file
						logger.debug("Reading the picture...")						
						pic_buffer = foo.read()
							
						#close the file
						foo.close()
						logger.debug("Success...")

						#If we get here, then all file ops were successful
						return_value = pic_buffer
					except Exception as err:
						logger.exception("Cannot read capture file: %s" % self.capture_file)
						return_value = None
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				#logger.debug("Return Value: %s" % return_value)
				return(return_value)



def main():
	
	return 0

if __name__ == '__main__':
	main()

