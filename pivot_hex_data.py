"""
Name: pivot_hex_data.py
Created by: Mike Mertens, 06/2016
Maintained by: Ryan Hodges, 07/2016
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
		* the entire hex_template directory should be in the same directory as the .gdb directory
	* Open a project in ArcMap
	* Open gdb adding the 'gdb_poly' and 'gdb_data' files defined below
		*Add these layers to ArcMAP document ("Table of Contents -> Layers")
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
#shapefile_directory = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\Reporting_Data_GDB\\"
shapefile_directory = "E:\\GIS\\projects\\ODFWCompass2015\\Data\\Source\\ODFW\\CompassReportingTool_20160823\\"
# DEFINE the name of the GDB
#input_gdb = "ODFW_OCS_ReportingData.gdb"
input_gdb = "CompassReportingTool_20160823.gdb"
# DEFINE the name of the spatial layer in the GDB
#gdb_poly = "WV_Hexagons"
gdb_poly = "HexagonBaseData"
# DEFINE the name of the tabular data in the GDB
#gdb_data = "WV_ReportingData"
gdb_data = "OCS_RT_Data_201608"
#DEFINE the name of the created zip file - all shapefiles MUST have a specific name, but the zipped file can be more descriptive
output_zip_name = "PU_grid"

#DEFINE: for a sub-run of x hexes, set val to x (a number) - 0 for full run.
max_loops = 0 #0 for "run all"
hex_id_field = "AUSPATID"
template_layer = shapefile_directory + "hex_template\\PU_grid_template.shp"
input_pol = shapefile_directory + input_gdb + "\\" + gdb_poly
input_table = shapefile_directory + input_gdb + "\\" + gdb_data
output_name = "PU_grid"
hex_name = shapefile_directory + output_name
hex_pol = hex_name + ".shp"
workspace = shapefile_directory
arcpy.env.workspace = workspace
arcpy.env.overwriteOutput = True
common_name_field = "COMNAME"
#species_id = "TGTID"
species_id = "CompassID"

### END SETTINGS ###

### Edited from StacyR: http://gis.stackexchange.com/questions/31034/remove-lock-on-feature-class 
def clearWSLocks(inputWS):
  '''Attempts to clear locks on a workspace, returns stupid message.'''
  if all([
	arcpy.Exists(inputWS), arcpy.Delete_management(inputWS), arcpy.Exists(inputWS)]):
    return 'Workspace (%s) clear to continue...' % inputWS
  else:
    return '!!!!!!!! ERROR WITH WORKSPACE %s !!!!!!!!' % inputWS

#Create new shapefile:
#1. Delete old files
print("Delete old files")
clearWSLocks(hex_name)
clearWSLocks(shapefile_directory+output_name)
for match in glob.glob(hex_name+'.*'):
	os.remove(match)
	
#2. Set the correct output coordinate system
print("Set coord system")
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984 Web Mercator (Auxiliary Sphere)")
	
#3. Create the empty file from the template
print("Create target file from template")
workfiles = arcpy.CreateFeatureclass_management(shapefile_directory, output_name, "POLYGON", template_layer)


#4. Populate the unagregated rows from the input gdb
print("Populate target file rows")
clearWSLocks(shapefile_directory+output_name)
reportDict = {}
#fields = ['OBJECTID','SHAPE','Hex_ID','AUSPATID','ECOREGION','COA_Name']

inputCursor = arcpy.SearchCursor(input_pol)
hexInCursor = arcpy.InsertCursor(hex_pol)

for index,inputRow in enumerate(inputCursor):
	if (index in [0,100,500,1000,5000] or index%10000==0):
		print("Reading hex row: %d at time: %s" % (index,str(datetime.datetime.now().isoformat())))
	if max_loops > 0 and index > max_loops:
		print("Hit max number of iterations (%s). Breaking." % str(max_loops))
		break
	row = hexInCursor.newRow()
	row.setValue("OBJECTID", inputRow.getValue('OBJECTID'))
	row.setValue("SHAPE", inputRow.getValue('SHAPE'))
	row.setValue("Hex_ID", inputRow.getValue('Hex_ID'))
	row.setValue("AUSPATID", inputRow.getValue('Hex_ID'))
	row.setValue("ECOREGION", inputRow.getValue('ECOREGION'))
	row.setValue("COA_Name", inputRow.getValue('COA_RT'))
	hexInCursor.insertRow(row)
	
	# Be sure to have an entry for each hex id - otherwise we have problems later
	hexId = inputRow.getValue('Hex_ID')
	if hexId not in reportDict.keys():
		reportDict[hexId] = {
			"modField": [],
			"obsField": [],
			"habsField": [],
			"fishField": []
		}
		
del row
del hexInCursor
del inputCursor

#5. Pivot logic
print("Pivoting data into target file")
error_count = 0
error_max = 10

# the '.da' cursors were added in 10.1. If running an older Arc version, use the line without the '.da' instead
#dataCursor = arcpy.SearchCursor(dataTab, "AUSPATID = " + str(hex))
#dataCursor = arcpy.da.SearchCursor(dataTab,[common_name_field, species_id],"AUSPATID = " + str(hex))
dataCursor = arcpy.da.UpdateCursor(input_table,[common_name_field, "AUSPATID", species_id])

for index, row in enumerate(dataCursor):
	if (index in [0,100,500,1000,5000,10000] or index%50000==0):
		print("Reading data row: %d at time: %s" % (index,str(datetime.datetime.now().isoformat())))
	if max_loops > 0 and index > max_loops:
		print("Hit max number of iterations (%s). Breaking." % str(max_loops))
		break
	comName = row[0]
	hexId = str(row[1])
	specId = row[2]
	
	if hexId not in reportDict.keys():
		reportDict[hexId] = {
			"modField": [],
			"obsField": [],
			"habsField": [],
			"fishField": []
		}
		
	hex = reportDict[hexId]
	
	#now we need to determine how to handle the record and 
	splitNameList = comName.split("(")
	cleanComName = splitNameList[-1]  #this is now a list
	
	#need to test the length of the list (if there's no "(" there's only one element")
	if len(splitNameList) > 1:
		if cleanComName == "Modeled Habitat)":
			hex['modField'].append(specId)
		else:
			if cleanComName == "Observed)":
				hex['obsField'].append(specId)
			else:
				print("--- Clean Common Name not understood: %s ---" % cleanComName)
				error_count = error_count +1
				if error_count >= error_max:
					print("=== TOO MANY ERRORS. ABORTING. ===")
					print("comName: %s" % comName)
					print("cleanComName: %s" % str(cleanComName))
					print("splitNameList: %s" % str(splitNameList))
					quit()
	else:
		#first check to see if it's a habitat (starts with "OCS")
		habyes = comName[:3]
		if habyes == "OCS":
			hex['habsField'].append(specId)
		else:
			hex['fishField'].append(specId)
		
del dataCursor
	
hexCursor = arcpy.UpdateCursor(hex_pol)

for index, hexRow in enumerate(hexCursor):
	if (index in [0,100,500,1000,5000] or index%10000==0):
		print("Reading hex row: %d at time: %s" % (index,str(datetime.datetime.now().isoformat())))
	if max_loops > 0 and index > max_loops:
		print("Hit max number of iterations (%s). Breaking." % str(max_loops))
		break
	hex = hexRow.getValue(hex_id_field)
	try:
		hexDict = reportDict[str(hex)]
		
		modField = str(hexDict['modField']).replace(" ","")
		obsField = str(hexDict['obsField']).replace(" ","")
		habsField = str(hexDict['habsField']).replace(" ","")
		fishField = str(hexDict['fishField']).replace(" ","")
		if len(modField) > 254 or len(obsField) > 254 or len(habsField) > 254 or len(fishField) > 254:
			print("=== One of the fields for hex id %s is too long. Suggest shorter %s values ===" % (str(hex),species_id))
			print("Length of %s: %s" % ('modeled', str(len(modField))))
			print("Length of %s: %s" % ('observed', str(len(obsField))))
			print("Length of %s: %s" % ('habitats', str(len(habsField))))
			print("Length of %s: %s" % ('fish', str(len(fishField))))
			quit()
		hexRow.setValue("mod_spec", modField)
		hexRow.setValue("obs_spec", obsField)
		hexRow.setValue("habitat", habsField)
		hexRow.setValue("fish", fishField)
	except:
		print('Hex ID %s not found - skipping.' % str(hex))
		pass

	hexCursor.updateRow(hexRow)
	
del hexCursor

#6. zip up shapefile
print("Writing zip file")
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

shapezip = zipfile.ZipFile(shapefile_directory+output_zip_name+'.zip', mode='w')
zipcount = 0
for match in glob.glob(hex_name+'.*'):
	filename = match.split(shapefile_directory)[1]
	if 'lock' not in filename and 'zip' not in filename:
		print('writing %s, loop %s' % (filename, zipcount))
		shapezip.write(match, filename, compress_type=compression)
	zipcount = zipcount + 1
print("Closing zipfile")
shapezip.close()

del workfiles

