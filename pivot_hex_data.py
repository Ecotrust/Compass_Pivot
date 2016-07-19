"""
Name: pivot_hex_data.py
Created by: Mike Mertens, 06/2016
Description: Used to pivot the species table associated with
	marxan hexes so there is a one to one relationship with a list
	of species modeled or observed
process: iterates through a unique list of hex ids and uses
	a cursor to extract each field and return it to a text string
	which is ultimately used to join back to the hexes and calc out new
	item equal to that string
	
The data is kind of a mess where all modeled, observed species are thrown under the 
same attribute as OCS habitats and fish species.  There is no way to know however
which is which and each will need to be handled differently so we'll need
to do some fancy string parsing once the item is returned to a variable.
The output will use a unique species id (which is in the table as "MarxanID"
to ensure that field names don't get too long.  Each ID will be serated by a comma

What we can do is use a two different cursors, one to iterate through the hexes
and another to iterate through the report data, updating the hexCursor.field based on
the result of the string parse.  Update should look like setValue(fieldx, row.getValue(fieldx + "parsed string")

The hex polygon feature set should have the appropriate fields to store the result:
	obs_spec
	mod_spec
	habitats
	fish
"""


# Import arcpy module and check out extension
import arcpy
import os
import time
import datetime





#init the field vars
modField = ""
obsField = ""
habsField = ""
fishField = ""
#need to constrain it to just a few records at first
#this should be a cursor

#set the feature class name and data table name
hex_pol = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\wv_hex.shp"
# and the fields to update
field1 = "mod_spec"
field2 = "obs_spec"
field3 = "habitat"
field4 = "fish"

dataTab = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\reportingData.dbf"

hex_id_field = "AUSPATID"

hexCursor = arcpy.UpdateCursor(hex_pol)
for hexRow in hexCursor:
	hex = hexRow.getValue(hex_id_field)
	dataTab = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\reportingData.dbf"
	field = "COMNAME"
	sp_id = "MarxanID"
	
	dataCursor = arcpy.SearchCursor(dataTab, "AUSPATID = " + str(hex))
	for row in dataCursor:
		t = row.getValue(field)
		I = row.getValue(sp_id)
		#now we need to determine how to handle the record and 
		s = t.split("(", 1)  #this is now a list
		
		#need to test the length of the list (if there's no "(" there's only one element")
		if len(s) > 1:
			if s[1] == "Modeled Habitat)":
				modField = modField + "," + str(I)
			if s[1] == "Observed":
				obsField = obsField + "," + str(I)
		else:
			#first check to see if it's a habitat (starts with "OCS")
			habyes = t[:3]
			if habyes == "OCS":
				habsField = habsField + "," + str(I)
			else:
				fishField = fishField + "," + str(I)
			
		row = dataCursor.next()
		
	#print (str(hex) + ":" + modField + "\n")
	#print (str(hex) + ":" + obsField + "\n")
	#print (str(hex) + ":" + habsField + "\n")
	#print (str(hex) + ":" + fishField + "\n")
	
	#need to strip the , from beggining of each
	modField = modField.strip( ',' )
	obsField = obsField.strip( ',' )
	habsField = habsField.strip( ',' )
	fishField = fishField.strip( ',' )
	
	hexRow.setValue(field1, modField)
	hexRow.setValue(field2, obsField)
	hexRow.setValue(field3, habsField)
	hexRow.setValue(field4, fishField)

	hexCursor.updateRow(hexRow)
	#hexRow = hexCursor.next()

