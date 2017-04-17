import RPi.GPIO as GPIO
import time
import os
import logging


#adjust for where your switch is connected
buttonPin = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(buttonPin,GPIO.IN)

#define Button States
Button_Down = 1
Button_Up = 0

#Initialize blocking IO counters
Debouncing_This_Button_Press = True

#initialise a previous input variables to 0 (assume button not pressed last)
prev_input = 0
prev_last_stable_input = 0

#initialise bounce counters
stable_count = 0
max_stable_count = 5

#Initial report
#take a reading of GPIO pin
input = GPIO.input(buttonPin)
#Print the Button State
def Print_Button_State(state):
	if (state == Button_Down):
		print("Button was pressed Down!")
	elif (state == Button_Up):
		print("Button was let Up!")
	else:
		print("Undefined Value: ", state)

#Start polling the input pin forever
try:
	while GPIO.wait_for_edge(buttonPin, GPIO.BOTH):
		while Debouncing_This_Button_Press:
		  #take a reading of GPIO pin
		  input = GPIO.input(buttonPin)

		  #Looking at pin and figure out if bouncing...
		  if (prev_input != input):
			#input still bouncing, need to wait longer...
			#Reset the stable counter
			stable_count = 0
			print("Bouncing!!")
		  else:
			#Well, looks stable, but let's check if we're really stable...
			#print("Check if stable...")
			if(stable_count < max_stable_count):
				#input not bouncing, waiting for stability...
				stable_count += 1  #count up to max stable count and hold
				# print("No, wait for stable signal...")
			else:
				#We're sure we're stable, now let's record it as last stable input...
				#print("Yes, Stable...")
				#Alright, now that it's stable, did the input state change from last stable input?
				if (prev_last_stable_input != input):
					#Hey!  After we finished bouncing, the final signal was different from prior
					#Meaning, the button was either pressed or released, time to call our script
					print("Button changed State!")
					Print_Button_State(input)
					#Go in to blocking IO for next button press
					DeBouncing_This_Button_Press = False
					#Call the external shell script; will be called (as root); and output button state
					# os.system("python ./Button_Service_Routine.py")
				else:
					DeBouncing_This_Button_Press = True
					#print("No change in state...")
				# Track the change in state
				prev_last_stable_input = input

		  #always update previous input
		  prev_input = input
		  #slight pause to help debounce
		  time.sleep(0.0005)
finally:
	GPIO.cleanup()



