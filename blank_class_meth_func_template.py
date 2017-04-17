#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  blank_class_meth_func_template.py
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


def minghi(self, logger):
			#Constants
			
			#Variables
			return_value = 0

			#logging preamble
			logger.debug("Entering: %s" % inspect.stack()[0][3])
			
			#Function params
			logger.debug("Object: %s" % self)
						
			#Start function

			#Return from function
			logger.debug("Exiting: %s" % inspect.stack()[0][3])
			logger.debug("Return Value: %s" % return_value)
			return (return_value)			

def main():
	
		
	return 0

if __name__ == '__main__':
	main()

