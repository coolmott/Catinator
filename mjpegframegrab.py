#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  mjpegframegrab.py
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
import requests			# "requests" connection processing library
import sys, getopt		# libs for processing cmd line arguments


#Constants
HTML_Frame_Header	 = "Content-Length"   #motion frame header
Read_Length = 1024	#number of bytes to read at once from server stream
start_of_jpeg_token  = b"\xFF\xD8"		# JPEG start token
end_of_jpeg_token    = b"\xFF\xD9"		# JPEG end token


# Function: html_jpeg_frame_grab()
# Input:  "link" - string that contains the URL to grab the frame from
#		  "Content_Identifier" - string that marks html frame header
#		  "Read_Len" - length of buffer to read from raw input file
#						at one time
#		  "start_of_jpeg_string" marks the start of a JPEG frame
#		  "end_of_jpeg_string" marks the end of a JPEG frame
#
# Output: "jpeg_frame"- a string (str) containing the grabbed jpeg image
#
# Purpose:
#
# FOR USE WITH "motion" webcam server by Kenneth Jahn Lavrsen
#
# This function opens a connection to the motion URL specified in "link"
# It then reads the raw data from the streaming connection until it
# detects at least one full jpeg frame.  It uses "Content-Length" and
# standard JPEG start/stop tokens in order to determine buffer length.
# It then returns the sub string that contains only the JPEG image.
# It closes the connection and tidies up.
#
# This function is standalone and can be imported from this module 
# into other python modules.
#
# Tested in Python 2.7.9 on "Jessie" Raspian 4.4.13-v7+ #894
# with Motion 3.2.12+git20140228
# Requires "requests" library
#
def html_jpeg_frame_grab(link, 
						 Content_Identifier,
						 Read_Len, 
						 start_of_jpeg_string,
						 end_of_jpeg_string):

	#Variables
	counter     = 0		 # counts the instances of html frame headers
	start = end = 0		 # initialize the buffer indexes
	jpeg_frame  = None	 # initialize the return buffer
	pic_buffer  = None 	 # initialize the working buffer
	
	# Validate input params
	if ((link == "") or (link == None)   or
		(len(Content_Identifier)   <= 0) or
		(len(start_of_jpeg_string) <= 0) or
		(len(end_of_jpeg_string)   <= 0) or
		(Read_Len <= 0)):
		
		#Oops, one of the input params is bad
		print("Error: invalid function input parameters")
	
	else:  #we have good params
		#open the connection for reading
		try:
			connection = requests.get(link, stream=True) #open the connection
		except Exception as err:
			print(err)  #Catch any connection exceptions and print error
		else:	
			#We have a valid stream, read the initial bytes into our byte buffer
			#Note, this function is implemented using bytes and bytearrays
			#All manipulations are with byte and bytearray methods
			pic_buffer = connection.raw.read(Read_Len)  #Fill the initial byte buffer
			
			if (len(memoryview(pic_buffer)) <= 0):  #if no data stream return Nothing
				print("Error: cannot read stream", link, pic_buffer)
			else:
				#start processing the buffer Read_Len chars at a time
				#find at least two instances of the content identifier in the
				#raw stream.  Between these two is the actual jpeg frame
				while (counter < 2):
					pic_buffer += connection.raw.read(Read_Len)
					counter = pic_buffer.count(bytes(Content_Identifier,'utf-8'))
				# Warning: This line will go into infinite loop if 
				# the connected stream doesn't contain a valid jpeg stream.
										
				# we know our jpeg frame is in the buffer
				# simply use find() with the JPEG begin and end tokens
				# to find the start and end indexes of the jpeg image.
				start = pic_buffer.find(start_of_jpeg_string)
				end   = pic_buffer.find(end_of_jpeg_string, start)+len(memoryview(end_of_jpeg_string))  # must look past the end token
				
				# test if we have anything worth returning
				if ((end - start) < 1):
					print("Error: index width is not 1 or greater")
				else:
					# We have something to send back! clip it!
					jpeg_frame = pic_buffer[start : end] #Clip the JPEG image
								
			connection.close()					#Clean up connection
			
	return 	(jpeg_frame)						#return the JPEG image



# Wrapper for standalone functional script implementation
#
# Usage: mjpegframegrab.py -l <url>
#		 mjpegframegrab.py -h
# Ex: <python> mjpegframegrab.py -l http://127.0.0.1:8081/ > foo.jpeg
#
# Command line options:
#		-l <url> - specifies the url to connect for a motion jpeg stream
#		-h       - help, outputs usage
#
# Return Value: 
#		0    Success
#		1    "-h" help input argument detected
#		2-5  Argument processing failure
#
# When used as a standalone script, this wrapper examines the command
# line arguments for the link to connect on, connects, and then 
# returns the raw jpeg image to stdout.  User can redirect to an 
# output file to capture a single frame of a "motion" jpeg stream.
#
# Connection errors are redirected to stdout instead of jpeg frame when
# connections are unsuccessful.
#
# Note1: This script will go into infinite loop if the connected stream
#        does not contain a valid jpeg stream.
#
# Note2: this wrapper script can either be invoked by calling python or
# by calling it directly from the shell if the script has execute 
# permissions.
#
# Tested in Python 2.7.9 on "Jessie" Raspian 4.4.13-v7+ #894
# with Motion 3.2.12+git20140228
# Requires "requests" library
#
def main(argv):
	
	#Constants
	Usage = "Usage: mjpegframegrab.py -l <url> > <output file>"
	
	#Variables
	link = ""        # String containing the URL
	frame = ""       # Return Buffer
	return_value = 0 # Return value assumes success

	#parse arguments
	if (len(argv) <= 0):   #Test to see if we have arguments...
		print("Not enough arguments")
		return_value = 2  #Not enough args
	else:    # Yes, we do have proper number of args
		try: #Try to get the options
			opts, args = getopt.getopt(argv,"hl:")
		except getopt.GetoptError as err:  #Print an error if occurs
			print("Argument Error: ", err)  
			return_value = 3
		else:
			if (not opts): #Any recognized opts present in argv?
				print("No recognized arguments")
				return_value = 4    # No, do not process
			else:  #We have valid options in argv
				for opt, arg in opts:	  #Test the options in the args
					if   (opt == "-h"):		#Help arg, just print usage
						return_value = 1
					elif (opt == "-l"):		#-l is the "link" arg
						link = arg          #URL is present, store it
					else:
						print("Unknown argument")
						return_value = 5	# unknown option
				
				if (return_value != 0):		#Argv processing not ok?
					frame = None			#Clear the frame
				else:
					#got valid options from arguments, grab the frame
					frame = html_jpeg_frame_grab(link,
												HTML_Frame_Header,
												Read_Length,
												start_of_jpeg_token,
												end_of_jpeg_token)
					
	#check if we have something in the frame & print it to stdout
	if ((return_value != 0) or (len(memoryview(frame)) <= 0)):
		print (Usage)			# Catch any errors and print Usage
	else:
		# length of frame is positive, write to std out, and return value is success
		sys.stdout.buffer.write(frame)  #instead of print(), write() binary data to sys.stdout
		
	return (return_value)

#if invoked from command line and this module is 'main', then call main
if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))

