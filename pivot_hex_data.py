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
	
Running this script:
	* Update the 'DEFINE' sections of the 'SETTINGS' below
	* copy hex_template from this dir to 'shapefile_directory' as defined below
	* Open a project in ArcMap
	* Open gdb adding the 'gdb_poly' and 'gdb_data' files defined below
	* open Python Terminal
	* run `execfile(r'\\neoterra\GIS\projects\ODFWCompass2015\Util\Scripts_Models\Compass_Pivot\pivot_hex_data.py')`
	* NOTE: the location of the file will change in the above command.
"""

# Import arcpy module and check out extension
import arcpy
import os
import time
import datetime
import glob
import zipfile


### SETTINGS ###

# DEFINE where the spatial data (GDB file and template directory) is located
shapefile_directory = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\"
# DEFINE the name of the GDB
input_gdb = "ODFW_OCS_ReportingData.gdb"
# DEFINE the name of the spatial layer in the GDB
gdb_poly = "WV_Hexagons"
# DEFINE the name of the tabular data in the GDB
gdb_data = "WV_ReportingData"
# DEFINE the location of this dbf file. I think it was created by Mike from the tabular data in the gdb.
dataTab = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\reportingData.dbf"

hex_id_field = "AUSPATID"
template_layer = shapefile_directory + "hex_template\\PU_grid_template.shp"
input_shape = shapefile_directory + gdb_poly
input_pol = input_shape + ".shp"
output_name = "PU_grid_test"
hex_name = shapefile_directory + output_name
hex_pol = hex_name + ".shp"
workspace = shapefile_directory
arcpy.env.workspace = workspace
common_name_field = "COMNAME"
species_id = "MarxanID"

#init the field vars
modField = ""
obsField = ""
habsField = ""
fishField = ""

### END SETTINGS ###

#Create new shapefile:
#1. Delete old files
for match in glob.glob(hex_name+'.*'):
	os.remove(match)
		
for match in glob.glob(input_shape+'.*'):
	os.remove(match)

#2. Set the correct output coordinate system
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984 Web Mercator (Auxiliary Sphere)")
	
#3. Create the empty file from the template
arcpy.CreateFeatureclass_management(shapefile_directory, output_name, "POLYGON", template_layer)

#4. Populate the unagregated rows from the input gdb
arcpy.CopyFeatures_management(gdb_poly,input_shape)

# the '.da' cursors were added in 10.1. If running an older Arc version, use the lines without the '.da' instead
#inputCursor = arcpy.UpdateCursor(input_pol)
#hexInCursor = arcpy.InsertCursor(hex_pol)
fields = ['SHAPE','Hex_ID','AUSPATID','ECOREGION','COA_Name']
inputCursor = arcpy.da.UpdateCursor(input_pol, ['FID'] + fields)
hexInCursor = arcpy.da.InsertCursor(hex_pol, ['OBJECTID'] + fields)

for inputRow in inputCursor:
	#row = hexInCursor.newRow()
	#row.setValue("SHAPE", inputRow.getValue('SHAPE'))
	#row.setValue("Hex_ID", inputRow.getValue('Hex_ID'))
	#row.setValue("AUSPATID", inputRow.getValue('AUSPATID'))
	#row.setValue("ECOREGION", inputRow.getValue('ECOREGION'))
	#row.setValue("COA_Name", inputRow.getValue('COA_Name'))
	#row_values = (
	#	inputRow.getValue('SHAPE'), 
	#	inputRow.getValue('Hex_ID'), 
	#	inputRow.getValue('AUSPATID'), 
	#	inputRow.getValue('ECOREGION'), 
	#	inputRow.getValue('COA_Name')
	#)
	hexInCursor.insertRow(inputRow)
	
#del row
del hexInCursor
del inputCursor

#5. Pivot logic
# the '.da' cursors were added in 10.1. If running an older Arc version, use the line without the '.da' instead
hexCursor = arcpy.UpdateCursor(hex_pol)
#hexRowFields = [hex_id_field,"mod_spec","obs_spec","habitat","fish"]
#hexCursor = arcpy.da.UpdateCursor(hex_pol,'*')

for hexRow in hexCursor:
	#hex = hexRow[0]
	hex = hexRow.getValue(hex_id_field)

	# the '.da' cursors were added in 10.1. If running an older Arc version, use the line without the '.da' instead
	dataCursor = arcpy.SearchCursor(dataTab, "AUSPATID = " + str(hex))
	#dataCursor = arcpy.da.SearchCursor(dataTab,[common_name_field, species_id],"AUSPATID = " + str(hex))
	for row in dataCursor:
		t = row.getValue(common_name_field)
		I = row.getValue(species_id)
		#t = row[0]
		#I = row[1]
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
	
	hexRow.setValue("mod_spec", modField)
	hexRow.setValue("obs_spec", obsField)
	hexRow.setValue("habitat", habsField)
	hexRow.setValue("fish", fishField)
	#hexRow[1] = modField
	#hexRow[2] = obsField
	#hexRow[3] = habsField
	#hexRow[4] = fishField

	hexCursor.updateRow(hexRow)
del hexCursor

#6. zip up shapefile
with zipfile.ZipFile(output_name+'.zip', 'w') as shapezip:
	for match in glob.glob(hex_name+'.*'):
		shapezip.write(match)

