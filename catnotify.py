#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  catnotify.py
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
import time							# time library for sleep()
from time import sleep
import os							# for file handling
import subprocess					# for spawning notifications
import threading					# for spawning sending threads
from   threading import Thread		# for spawning sending threads
import smtplib						# Email handling imports
from os.path import basename		
from email.mime.application import MIMEApplication
from email.mime.multipart	import MIMEMultipart
from email.mime.text		import MIMEText
from email.mime.image		import MIMEImage
from email.utils			import COMMASPACE, formatdate
import imghdr						# find out what imgs we're using
import base64 						# for base64 encoding
from bs4					import BeautifulSoup  #HTML scrapper for images
import catcam						# camera class
import cat_global

#--template class
#--enabled <-- member
#--addr <-- which address list to use
#--type <-- html, txt, or smart
#--template <-- char buffer for actual template
#--template.init() <-- read in template from etree
#--template.send(from_addr, address[] list object, condition)  ###STOPPED HERE######################## 

class template_type:

			#Class Members
			CLOSED_ID					= cat_global.state_str[cat_global.CLOSED].lower()
			ARMED_ID					= cat_global.state_str[cat_global.ARMED].lower()
			JAMMED_ID					= cat_global.state_str[cat_global.JAMMED].lower()
			email_ID					= cat_global.target_addr_str[cat_global.email]
			sms_ID						= cat_global.target_addr_str[cat_global.sms]
			smartphone_ID				= cat_global.target_addr_str[cat_global.smartphone]
			html_ID						= cat_global.target_type_str[cat_global.html]
			text_ID						= cat_global.target_type_str[cat_global.text]
			smart_ID					= cat_global.target_type_str[cat_global.smart]
			target_ID					= "target"
			type_ID						= "type"
			addr_ID						= "addr"
			enabled_ID					= "enabled"
			template_type				= cat_global.text
			address_list_type			= cat_global.target_addr_str[cat_global.email]
			attach_token				= "Picture is attached"  #default template string
			enabled						= True
			template					= ["","",""]  # list of template empty buffer strings
						
		
		
			#Class notify_type contructor	
			def __init__(self, config_tree, token, logger):
				#Constants
				
				#Variables
				return_value = 0
				cond_index	 = cat_global.CLOSED  #condition index into templates
				self.template = ["","",""]
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("XML Object: %s" % config_tree)
				logger.debug("Token: %s" % token)
				
				#Start function
				
				#Capture the address list type
				if (config_tree.tag != self.target_ID):
					logger.error("Bad root element tag; does not equal target")
				else:
					logger.debug("Started loading templates")
					
					# Read the basic template parameters
					self.address_list_type = config_tree.attrib[self.addr_ID]
					self.attach_token = token #store the attachment token string
					
					#Parse the template type
					if   (config_tree.attrib[self.type_ID] == cat_global.target_type_str[cat_global.email]):
						self.template_type = cat_global.email
					elif (config_tree.attrib[self.type_ID] == cat_global.target_type_str[cat_global.text]):
						self.template_type = cat_global.text
					elif (config_tree.attrib[self.type_ID] == cat_global.target_type_str[cat_global.smart]):
						self.template_type = cat_global.smart
						
					self.enabled		= (config_tree.attrib[self.enabled_ID].upper() == "TRUE")
					logger.debug("Template: %s of type: %s addr: %s enabled: %s" % (self,
						cat_global.target_type_str[self.template_type], self.address_list_type, self.enabled))

					#Iterate through the XML config tree and populate the config
					#This is just a big case statement that populates the class members
					# PS: look for a better way to do this one day... there has to be					
					for elem in config_tree.iter():
						if (elem.tag == self.CLOSED_ID):
							self.template[cat_global.CLOSED] = self.read_template_file(elem.text, logger)
						elif (elem.tag == self.ARMED_ID):
							self.template[cat_global.ARMED] = self.read_template_file(elem.text, logger)
						elif (elem.tag == self.JAMMED_ID):
							self.template[cat_global.JAMMED] = self.read_template_file(elem.text, logger)
					
					logger.debug("Finished loading templates")
																				
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

#Method: read_template_file - reads a template file from disk and populates into a file buffer
#warning: a very simple read() is executed assuming template files are no more
#than a few 100k large
			def read_template_file(self, filename, logger):
				#Constants
				
				#Variables
				return_value = ""
				foo			 = None  #arbitrary file object
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("Filename: %s" % filename)

				#Start function
				try:
					if (not os.access(filename, os.R_OK)): #test for state file
						logger.error("Cannot open template file: %s" % filename)
						return("")
				except Exception as err:
						logger.exception("Cannot open template file: %s" % filename)
				else:
					try:
						logger.debug("Opening and reading template file: %s" % filename)
						#Open the file
						foo = open(filename)
						
						#read into the local buffer
						return_value = foo.read()
						
						#close the file
						foo.close()
						logger.debug("Success...")
					except Exception as err:
						logger.exception("Cannot open template file: %s" % filename)
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				#logger.debug("Return Value:\n %s" % return_value)
				return(return_value)

			def start_send_thread(self, message, logger):
				#Constants
				
				#Variables
				return_value = 0
				send_thread  = None

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
						
				#Function params
				logger.debug("Object: %s" % self)
													
				#Start function
				try: 
					assert isinstance(message, MIMEMultipart) # Check our message parameter
					
					# Spawn the thread to send the message
					send_thread = Thread(target=self.sending_thread_func, args=(message, logger, ))
					logger.debug("Spawned thread object %s to send message" % send_thread)
					
					#Start the thread going
					logger.debug("Starting thread object: %s" % send_thread)
					send_thread.start()
				except Exception as err:
					logger.exception("Cannot spawn thread")
					return_value = 1

				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return (return_value)			

			def sending_thread_func(self, message, logger):
				#Constants
				
				#Variables
				return_value = 0
				email_connection = None

				#logging preamble
				logger.debug("Entered thread %s of threads %s" % (threading.get_ident(), threading.active_count()))
				logger.debug("Entering function: %s" % inspect.stack()[0][3])
						
				#Function params
				logger.debug("Object: %s" % self)
													
				#Start function
				try: 
					assert isinstance(message, MIMEMultipart) # Check our message parameter
					
					# We're in a thread, so make a connection to sendmail port and send the message
									
					#Create connection
					email_connection = smtplib.SMTP(cat_global.email_server_addr)
					logger.debug("Opened email connection: %s" % email_connection)
					logger.info("Sending message...")
					email_connection.send_message(message)
					
					#Logger the thread details
					logger.debug ("Email message sent on %s ... closing connection" % email_connection)
					email_connection.quit()

				except Exception as err:
					logger.exception("Cannot send message to mail server")
					return_value = 1

				#Return from function
				logger.debug("Exiting function: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				logger.debug("Exiting thread %s of threads %s" % (threading.get_ident(), threading.active_count()))


#Method: send() - formats and sends an email based upon parameters
# from_addr, address_list object, condition to the template
# contained in the object; assume text only email
# If a camera object is present, then attach the picture in the object
			def send(self, from_addr, address_list, cond, camera, logger):
				#Constants
				
				#Variables
				return_value = 0
				msg			 = None  #Buffer ptr to message buffer
				smtp		 = None  #ptr to the smtp object
				proc 		 = None  #ptr to a forked sub-process
				picture		 = None  #ptr to the picture buffer

				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("From: %s" % from_addr)
				logger.debug("To: %s" % address_list)
				logger.debug("Condition: %s" % cat_global.state_str[cond])
				logger.debug("Camera Obj: %s" % camera)				

				#Start function
				try:
					# Check our inputs, raise an exception if funky
					assert (from_addr != "")				# Check from is not empty
					assert isinstance(address_list, list)  	# Check our address list
					assert ((cond >= cat_global.CLOSED) and (cond <= cat_global.JAMMED)) #Make sure condition is within bounds
					
					#Build the MIME message
					msg = MIMEMultipart()
					msg['From'] = from_addr
					msg['To']	= COMMASPACE.join(address_list)  #create comma separated string of addresses
					msg['Date']	= formatdate(localtime=True)
					msg['Subject'] = self.template[cond][:self.template[cond].find("\n")] #Subject is first line of the template
					msg.attach(MIMEText(self.template[cond][(self.template[cond].find("\n")+1):], 
					"plain")) # send as plain in base class of template

					#attach jpeg image to MIME msg, if present, else, do nothing
					if((camera != None) and (camera.enabled) and (self.template[cond].find(self.attach_token) > -1)):
						logger.info("Attaching picture from camera")
						
						picture = camera.read_picture(logger)
						if (picture == None):
							logger.debug("Capture file could not be read")
						else:
							attachment = MIMEImage(picture)
							#attachment = MIMEApplication(picture, Name=basename(camera.capture_file))
							#attachment['Content-Disposition'] = ('attachment; filename "%s"' % basename(camera.capture_file))
							msg.attach(attachment)
					else:
						logger.info("Camera not enabled or token not found in template, not attaching picture")
										
					#print(msg)  #don't dump to log file; debug purposes only
					
					#Send the MIME message
					self.start_send_thread(msg, logger)
					
					# Call subprocess to quickly fork a sendmail command to send the notification; this is NON-BLOCKING
					#proc = subprocess.Popen(cat_global.sendmail_cmd, stdin=subprocess.PIPE, universal_newlines=True)
					#proc.stdin.write(msg.as_string())	#send msg to sendmail stdin, non-blocking
					#proc.stdin.close()					#send EOF to sendmail stdin, non-blocking
					# Note, usage of proc.communicate() is blocking and can block the catinatord up to 10 seconds, ergo not used
					# The sending of the message is "fire and forget"...
					# If there are issues after this point, then its time to look at /var/log/mail.log ;-)

					# Log the process ID that was created/forked
					#logger.info("sendmail forked, pid: %s" % proc.pid)

				except Exception as err:
						logger.exception("Cannot send notification")
						return_value = 1
	
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return(return_value)


#The html_template_type is a derived sub-class of template_type
#It will create the same object as a template type, but with overridden
#send() method in order to handle html as opposed to plain text
class html_template_type(template_type):

#Method: send() - formats and sends an email based upon parameters
# from_addr, address_list object, condition to the template
# contained in the object
# this send() specically handles html emails
			def send(self, from_addr, address_list, cond, camera, logger):
				#Constants
				
				#Variables
				return_value = 0
				msg			 = None  #Buffer ptr to message buffer
				smtp		 = None  #ptr to the smtp object
				proc 		 = None  #ptr to a forked sub-process
				soup		 = None  #bs4 object
				foo			 = None  #file object ptr to image files
				image_type	 = ""    #string for type of image
				msgImage	 = None	 #buffer for raw image for encoding
				imageb64	 = None  #raw image base64 encoded
								
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("From: %s" % from_addr)
				logger.debug("To: %s" % address_list)
				logger.debug("Condition: %s" % cat_global.state_str[cond])				
				logger.debug("Camera Obj: %s" % camera)
				
				#Start function
				try:
					# Check our inputs, raise an exception if funky
					assert (from_addr != "")				# Check from is not empty
					assert isinstance(address_list, list)  	# Check our address list
					assert ((cond >= cat_global.CLOSED) and (cond <= cat_global.JAMMED)) #Make sure condition is within bounds
					
					#Build the MIME message
					logger.debug("Building message headers")
					msg = MIMEMultipart("alternative")  # <-- crucial for html
					msg['From'] = from_addr
					msg['To']	= COMMASPACE.join(address_list)  #create comma separated string of addresses
					msg['Date']	= formatdate(localtime=True)
					msg['Subject'] = self.template[cond][:self.template[cond].find("\n")] #Subject is first line of the template
					
					#The Text part of the message is found between the first subject line and the <!DOCTYPE html header
					logger.debug("Attaching plain text body of message")
					msg.attach(MIMEText(self.template[cond][(self.template[cond].find("\n")+1):self.template[cond].find(cat_global.html_header)], 
					"plain")) # attach as plain in MIME message					

					#now, parse the remaining HTML and get/replace the <img> tags using beautiful soup
					logger.debug("Starting image parse...")
					
					#create the soup (ie. parsed HTML object)
					soup = BeautifulSoup(self.template[cond][self.template[cond].find(cat_global.html_header):])
					
					#find all the images, encode into MIME msg
					for imgtag in soup.findAll('img'):
						#for each image tag in the html doc, open the image file, attach the file to the MIME msg,
						# and replace the path in the src attribute path with "cid:"
						logger.debug("For image tag src: %s" % imgtag['src'])
						
						if (imgtag['src'].find("data:") > -1):
							logger.debug("Image src is already encoded into tag")
						else:
							
							#Log the image type
							image_type = imghdr.what(imgtag['src'])
							logger.debug("Image is of type %s" % image_type)
							

							#Open the file						
							foo = open(imgtag['src'],"rb")  #open images as binary file object
							logger.debug("Opened image file: %s as Object: %s" % (imgtag['src'], foo))
																		
							#find the path and split off filename
							path, filename = os.path.split(imgtag['src'])
							logger.debug("Path: (%s) to filename: (%s)" % (path, filename))
						
							#read image into memory buffer
							logger.debug("Encoding image to base64 object")
							msgImage = foo.read()
						
							#base64 encode the image
							imageb64 = base64.b64encode(msgImage)
							#print("Base64 encoding of %s:\n %s" % (filename, imageb64)) #debug dump to stdout
						
							#change the tag include the newly base64 encoded image
							imgtag['src'] = "data:image/" + image_type + ";base64," + imageb64.decode("utf-8")
							#print("\nNew image tag:\n %s" % imgtag['src'])
						
							#close the file
							logger.debug("Closing the image file")
							foo.close()
					
					#now, new html exists where img tags for path/img have been switched to a base64 encoded image tags
					#attach the newly modified html as message content
					#print(soup.prettify())  #debug dump to stdout
					logger.debug("Attaching html body to message")
					msg.attach(MIMEText(soup.prettify(), "html"))			
									
					#Send the MIME message
					#print(msg)  #don't dump to log file; dump to stdout; for debug purposes only

					#Send the MIME message
					self.start_send_thread(msg, logger)
					
					# Call subprocess to quickly fork a sendmail command to send the notification; this is NON-BLOCKING
					#proc = subprocess.Popen(cat_global.sendmail_cmd, stdin=subprocess.PIPE, universal_newlines=True)
					#proc.stdin.write(msg.as_string())	#send msg to sendmail stdin, non-blocking
					#proc.stdin.close()					#send EOF to sendmail stdin, non-blocking
					# Note, usage of proc.communicate() is blocking and can block the catinatord up to 10 seconds, ergo not used
					# The sending of the message is "fire and forget"...
					# If there are issues after this point, then its time to look at /var/log/mail.log ;-)

					# Log the process ID that was created/forked
					#logger.info("sendmail forked, pid: %s" % proc.pid)

				except Exception as err:
						logger.exception("Cannot send notification")
						return_value = 1
	
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return(return_value)

#Place holder for smartphone notification class, which will be a completely different class
# of template
class smart_template_type(template_type):
			smart = True

#--address_list class
#--type <-- email, sms, or smartphone
#--address_list[] <-- list of strings
#--address_list_type.init(elem) <-- populate addresses
#--address_list_type.get_list_by_string() <-- return concatenated list of addresses


class address_list_type:

			#Class Members
			CLOSED_ID					= cat_global.state_str[cat_global.CLOSED].lower()
			ARMED_ID					= cat_global.state_str[cat_global.ARMED].lower()
			JAMMED_ID					= cat_global.state_str[cat_global.JAMMED].lower()
			email_ID					= cat_global.target_addr_str[cat_global.email]
			sms_ID						= cat_global.target_addr_str[cat_global.sms]
			smartphone_ID				= cat_global.target_addr_str[cat_global.smartphone]
			html_ID						= cat_global.target_type_str[cat_global.html]
			text_ID						= cat_global.target_type_str[cat_global.text]
			smart_ID					= cat_global.target_type_str[cat_global.smart]
			addr_list_ID				= "addr_list"
			type_ID						= "type"
			addr_ID						= "addr"
			list_type					= cat_global.target_addr_str[cat_global.email]
			addresses					= []  # list of address strings				
		
		
			#Class notify_type contructor	
			def __init__(self, config_tree, logger):
				#Constants
				
				#Variables
				return_value = 0
				self.addresses = []
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("XML Object: %s" % config_tree)
				
				#Start function
				
				#Capture the address list type
				if (config_tree.tag != self.addr_list_ID):
					logger.error("Bad root element tag; does not equal addr_list")
				else:
					#Iterate through the XML config tree and populate the config
					#This is just a big case statement that populates the class members
					# PS: look for a better way to do this one day... there has to be
					self.list_type = config_tree.attrib[self.type_ID]
					logger.debug("List: %s of type: %s" % (self, self.list_type))
					for elem in config_tree.iter():
						if 	(elem.tag == self.addr_ID):
							self.addresses.append(elem.text)
							logger.debug("Adding: %s" % elem.text)
					
					logger.debug("Full address list: %s" % self.addresses)
					#logger.debug("As a string: %s" % self.get_list_by_string(logger))
															
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

			#Class return a concatenated list of the strings
			def get_list_by_string(self, logger):
				#Constants
				
				#Variables
				return_value = ""
				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)

				
				#Start function
				for string in self.addresses:
					return_value += string + ","
												
				# range slice string to cut off trailing comma
				return_value = return_value[:(len(return_value)-1)]
																				
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return(return_value)


#--notification_type class  <-- root object; contains all notifications
#--from <-- member, passed to all sub constructors to build the templates
#--notifications_list[email, sms, smartphone] <-- list of notification_targets
#--nofity.init() 
#--notify.send(cond) <-- for all types, send(condition)

class notification_type:

			#Class Members
			notifications_ID			= "notifications"
			from_ID			    		= "from"
			condition_ID				= "condition"
			attach_ID					= "attach_token"
			CLOSED_ID					= cat_global.state_str[cat_global.CLOSED].lower()
			ARMED_ID					= cat_global.state_str[cat_global.ARMED].lower()
			JAMMED_ID					= cat_global.state_str[cat_global.JAMMED].lower()
			email_ID					= cat_global.target_addr_str[cat_global.email]
			sms_ID						= cat_global.target_addr_str[cat_global.sms]
			smartphone_ID				= cat_global.target_addr_str[cat_global.smartphone]
			addr_list_ID				= "addr_list"
			target_ID					= "target"
			html_ID						= cat_global.target_type_str[cat_global.html]
			text_ID						= cat_global.target_type_str[cat_global.text]
			smart_ID					= cat_global.target_type_str[cat_global.smart]			
			from_addr					= "catinator@cat.net"
			attach_token				= "Picture is attached"
			notify_on_condition_list  	= [True, False, False]  #boolean list of conditions to notify on (bit list)
			address_list				= []  #lists of address lists by email, sms, or smartphone
			notifications_target_list  	= []  #list of notification targets by html, txt, or smart
			

		
			#Class notify_type contructor	
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
				logger.debug("Building notifcations")
				
				#Capture the door number
				if (config_tree.tag != self.notifications_ID):
					logger.error("Bad root element tag; does not equal notifications")
				else:
					#Iterate through the XML config tree and populate the config
					#This is just a big case statement that populates the class members
					# PS: look for a better way to do this one day... there has to be
					for elem in config_tree.iter():
						if 	(elem.tag == self.from_ID):
							self.from_addr = elem.text
							logger.debug("from %s" % self.from_addr)
						elif(elem.tag == self.attach_ID):
							self.attach_token = elem.text
							logger.debug("Attachment token %s" % self.attach_token)
						elif(elem.tag == self.condition_ID):
							condition_children = elem
							for sub_elem in condition_children.iter():
								if (sub_elem.tag == self.CLOSED_ID):
									self.notify_on_condition_list[cat_global.CLOSED] = (sub_elem.text.upper() == "TRUE")
								elif (sub_elem.tag == self.ARMED_ID):
									self.notify_on_condition_list[cat_global.ARMED] =  (sub_elem.text.upper() == "TRUE")
								elif (sub_elem.tag == self.JAMMED_ID):
									self.notify_on_condition_list[cat_global.JAMMED] = (sub_elem.text.upper() == "TRUE")
							logger.debug("notification conditions: %s" % self.notify_on_condition_list)
						elif(elem.tag == self.addr_list_ID):
							logger.debug("Adding address_list: %s" % elem.attrib["type"])
							self.address_list.append(address_list_type(elem, logger))
						elif(elem.tag == self.target_ID):				
							logger.debug("Adding template to target list: address_list: %s type: %s" \
										% (elem.attrib["addr"],elem.attrib["type"]))
							#Add in discrinate on template type here: plain, html, or smart, spawns a different template object
							return_value = self.append_template_based_on_type(elem, self.attach_token, logger)
							
															
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				#don't return, because we're an __init__

#Method: append_template_based_on_type()
#Appends a template to the notifcations target list, but does it by type
#Checks the type of an incoming template and then assigns to the correct class object
#Can choose between html, plain, or smart
			def append_template_based_on_type(self, elem, token, logger):
				#Constants
				
				#Variables
				return_value = 0

				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("Elem: %s" % elem)
				logger.debug("Token: %s" % token)
							
				#Start function

				#Simple if/elif then takes care of the assignment
				if (elem.attrib["type"] == self.html_ID):
					self.notifications_target_list.append(html_template_type(elem, token, logger))
					logger.debug("Appending a html template")
				elif (elem.attrib["type"] == self.text_ID):
					self.notifications_target_list.append(template_type(elem, token, logger))
					logger.debug("Appending a plain text template")
				elif (elem.attrib["type"] == self.smart_ID):
					self.notifications_target_list.append(smart_template_type(elem, token, logger))
					logger.debug("Appending a smartphone template")
				else:
					logger.debug("Invalid template type; appending null")
					self.notifications_target_list.append(None)
					return_value = 1
					
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return (return_value)	



#Method: send() - find the template based upon type and use its send method to send an email
			def send(self, cond, camera, logger):
				#Constants
				
				#Variables
				return_value = 0
				target 	 	 = None	 #ptr to current template list
				address_list = []    #address list to send to...
				local_address_list_ptr = None #ptr for iteration

				
				#logging preamble
				logger.debug("Entering: %s" % inspect.stack()[0][3])
				
				#Function params
				logger.debug("Object: %s" % self)
				logger.debug("Condition: %s" % cat_global.state_str[cond])				

				#Start function
				if ((cond < cat_global.CLOSED) and (cond > cat_global.JAMMED)): #Make sure condition is within bounds
					logger.error("Condition out of range %s" % cond)
					return_value = 1
				elif (self.notify_on_condition_list[cond] != True):
					logger.debug("Condition %s is not enabled for notification" % cat_global.state_str[cond])
					return_value = 0
				else:
					#cond is OK and enabled, continue...
					
					#find the template based upon type
					logger.debug("Checking template targets to notify...")
					for target in self.notifications_target_list:
						if (target.enabled != True):  #If this target is not enable
							logger.debug("Target %s is not enabled for notification" % target)
					
						else:
							#Search target for address lists							
							logger.debug("Searching target: %s for address lists" % target)

							#find the address list for this target
							address_list = [] # Initialize address list
							for local_address_list_ptr in self.address_list:
								if (target.address_list_type == local_address_list_ptr.list_type):
									address_list += local_address_list_ptr.addresses #concatinate address list
									logger.debug("Found address list: %s for target %s" % (local_address_list_ptr.addresses, target))
									logger.debug("Concatenating...")
									
							logger.debug("Notification address list: %s" % address_list)

							#time to tell target to send the notifications
							logger.info("Sending from: %s to target: %s  condition: %s\naddresses: %s" % \
									(self.from_addr, target, cat_global.state_str[cond], address_list))
									
							if (target.send(self.from_addr, address_list, cond, camera, logger) != 0):
								logger.error("Error sending from: %s to target: %s condition: %s\naddresses: %s" % \
									(self.from_addr, target, cat_global.state_str[cond], address_list))
								return_value += 1
							else:
								logger.debug("Send successful...")
						
																								
				#Return from function
				logger.debug("Exiting: %s" % inspect.stack()[0][3])
				logger.debug("Return Value: %s" % return_value)
				return(return_value)




def main():
	
	return 0

if __name__ == '__main__':
	main()

