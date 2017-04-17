#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Door_State_Handler.py
#
#  Catinator
#  Copyright 2016 James M. Coulthard <james.m.coulthard@gmail.com>
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

#Imports
import RPi.GPIO as GPIO
from time import sleep
import time
import logging
import subprocess


# Constants
Button = 17

# Parse the config file


# Define a thread callback function to run in another thread when events are detected
def Read_GPIO(channel):
	#Read the channel
	value = GPIO.input(channel)

	#Evaluate and output
	if value:
		print "Rising edge detected on", channel

		# Need to fork a process here as a handler
		#smtpobj = smtplib.SMTP(localhost)
		#sender = "Catinator@catinator.net"
		#receivers = "james.coulthard

		# Call subprocess to quickly create a new shell with sendmail command to send an email & SMS alert
		proc=subprocess.Popen(["/usr/sbin/sendmail james.coulthard@amdocs.com 8043378104@txt.att.net < /home/pi/email.txt"], shell=True, stdout=subprocess.PIPE,)
		# Print the process ID that was created
		print "pid:",proc.pid

		#Create blocking call to wait on stdout and print it
		stdout_value=proc.communicate()[0]
		print "stdout:",repr(stdout_value)
	else:
		print "Falling edge detected on", channel

	return value

# Wait_for_Button_Press - simply sleeps while waiting for IO state change
# and outputs results.  Exceptions are caught to clean up.
def Wait_for_Button_Press(Button_Channel):

	#Initialize GPIO
	GPIO.setmode(GPIO.BCM)     # set up BCM GPIO numbering
	GPIO.setup(Button_Channel, GPIO.IN)    # set input (button)

	# when a changing edge is detected on Button channel, regardless of whatever
	# else is happening in the program, the function Read_GPIO will be run
	GPIO.add_event_detect(Button_Channel, GPIO.RISING, callback=Read_GPIO, bouncetime=200)

	try:
		print "When pressed, you'll see: Rising Edge detected on", Button_Channel
		print "When released, you'll see: Falling Edge detected on", Button_Channel

		#Wait around forever; can be used for cleanup processing
		while True:
			sleep(5)

	finally:                   # this block will run no matter how the try block exits
		GPIO.cleanup()         # clean up GPIO

	return 0

# Equivalent of main(); in C, but not necessary in Python.  Makes for nice programming.
def main():

	#Execute
	Wait_for_Button_Press(Button)

	return 0

if __name__ == '__main__':
	main()

