#! /usr/bin/python3

'''
--------------------------------------------------------------------------------
GNU GENERAL PUBLIC LICENSE GPLv3

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
	GNU General Public License for more details.

	You should have a copy of the GNU General Public License
	in /usr/share/common-licenses/GPL-3. If not, 
	see <http://www.gnu.org/licenses/>.
	
--------------------------------------------------------------------------------
'''	

# Also depends on hugin_tools for align_image_stack.
import sys, os, shutil, shlex, glob, subprocess, multiprocessing

from PIL import Image, ImageOps, __version__
from PIL.ExifTags import TAGS

try:
	import gi
except:
	sys.exit('Failed to import gi')

try:
	gi.require_version('Gtk', '4.0')
except:
	print(gi.__version__)
	sys.exit('gi wrong version')


from gi.repository import Gtk, GdkPixbuf, Gio

#-------------------------------------------------------------------------------
# create global variables and set default values
version = '1.6.02'   					# formatted for "About"
firstrun = True

viewDim = 'All'								# which sort of images to show
viewType = 'ASCNP'						# which type of 3D images to show
viewlist = []									# list of images to view
viewind = 0										# index of image to view
infolist = ''

dummyfile = 'dummy.png'				# grey image to display when one is missing.
blankfile = 'blank.png'				# blank image to display for clearing.
preffile = 'popout3d.dat'			# user preference file
logofile = 'popout3d.png'			# logo for About
myfile = ''										# current file
myext = ''										# current extension
# myfold mustn't be defined
scope = 'folder'							# whether dealing with file set or folder

formatcode = 'A'							# first letter of format
stylecode = 'N'								# first letter of style
pairlist = []									# list of pairs to process
warnings = ''									# list of Processed warnings

okformat = ['A','S','C']			# Anaglyph/Side-by-Side/Crossover
okstyle	= ['N','P'] 					# Normal/Popout
okchar = ['0','1','2','3','4','5','6','7','8','9','L','R'] #last char in 2D filename
okext	= ['jpg','JPG','jpeg','JPEG','png','PNG','tif','TIF','tiff','TIFF']
tifext	= ['tif','TIF','tiff','TIFF']

processlist = False						# whether to show only recently processed files 32X 
blockfile = 'BLOCK'						# to show that multiprocessing is running
stopfile  = 'STOP'						# to tell multiprocessing to stop

# tooltips
tipDelete			= 'Delete a 3D image.'
tipQueue			= 'Make a queue of 3D images from the files selected by Folder or File.'
tipProcess		= 'Create the 3D images shown in the queue.'
tipReset			= 'Clear the list of processed images and show the list selected by Folder or File.'
tipNext				= 'Show next image.'
tipPrev				= 'Show previous image.'
tipOpen				= 'File: Select a 2D image file. View and possibly process related images.\nFolder: Select a folder. View and possibly process images in this folder.'
 
tip2D					= 'Show 2D images (with valid names).'
tipTriptych		= 'Show 3D images with the 2D images they came from below (with valid names).'
tip3D					= 'Show 3D images (with valid names).'
tipAll				= 'Show all images with valid names.'
tipAnaglyph		= '3D images with left image red, right image cyan.'
tipSidebyside	= '3D images with left image on the left, right on the right.'
tipCrossover	= '3D images with right image on the left, left image on the right.'
tipNormal 		= 'Normal 3D images.'
tipPopout			= '3D images which may appear to stand out in front of the screen.'

##image1 = Gtk.Picture.new(); imageL = Gtk.Picture.new(); imageR = Gtk.Picture.new()
##boxOuter1 = Gtk.Box(); boxOuterL = Gtk.Box(); boxOuterR = Gtk.Box()

#-------------------------------------------------------------------------------
'''
Added by 'exalm':
	$XDG_DATA_HOME defines the base directory relative to which user specific data files should be stored. 
	If $XDG_DATA_HOME is either not set or empty, a default equal to $HOME/.local/share should be used.
	Done.
	$XDG_CONFIG_HOME defines the base directory relative to which user specific configuration files should be stored. 
	If $XDG_CONFIG_HOME is either not set or empty, a default equal to $HOME/.config should be used.
	Not done.
'''

# home folder
homefold = os.getenv('XDG_HOME')
if homefold == None:
	homefold = os.getenv('HOME')
homefold = homefold + '/'

# work folder for processing files
workfold = homefold + '.popout3d/'
if os.path.isdir(workfold):
	shutil.rmtree(workfold, True)

result = os.system('mkdir '+ workfold)
if result != 0:
	print('Cannot create work directory')
	sys.exit(result)

# config folder for preference file
configfold = os.getenv('XDG_CONFIG_HOME')
if configfold == None:
	configfold = os.getenv('HOME') + '/.config/popout3d'
configfold = configfold + '/'
	
# project folder (read-only) for dummy image and blank image
if os.path.exists('/.flatpak-info'): #This is within the sandbox so can't be seen
	datafold = '/app/share/popout3d/'
else: # no package for testing
	datafold = '/home/chris/git/popout3d/'

#(os.getcwd())
#('homefold = ', homefold)
#('workfold = ', workfold)
#('configfold = ', configfold)
#('datafold = ', datafold)

# Basics
label0text = '''
Take two photos of a stationary subject, preferably in landscape format. Take the first, then move the camera about 60mm to the right, but point it at the same spot. Copy them to your PC, then rename them so that they have exactly the same name except that the left one has 'L' at the end and the right one has 'R'. For example photoL.JPG and photoR.JPG.

Open Popout3D then use Open>File to select either photo. Click Queue to see what 3D images will be created, the button will change to Process. Click it to begin processing. The button will change to Reset. If you use the < and > arrows you see a grey rectangle until the 3D image is complete when it will appear. It will take several seconds.

You will need 3D glasses to see anaglyph images or 3D Virtual Reality goggles to see side-by-side images. Some people can see side-by-side or crossover images without them.
'''
# Source Photographs
label1text = '''
You don't need a special camera, you can use an ordinary one or even a phone. Choose a subject that won't move between photos.

Take two photographs of the same subject, one for the left-hand image, and after moving the camera about 60mm to the right, take another for the right-hand image. Try to get exactly the same thing in the centre of both photos. If you find it difficult to get the spacing just  you can take 3 photos at different spacings. Don't take too many in the same set as this will result in a large number of 3D images which will take a long time to process. Always take them in sequence from left to right so you don't get them mixed up.

Each set of images (all those for the same subject) must be in the same format - .jpg, .tiff or .png, and the extensions must have the same case - all lowercase or all uppercase. They must be exactly the same size in pixels.

You may not be able to read/write image files on your camera or phone and the 3D images you create will need extra space, so it's best to copy your originals onto your PC.

When you have loaded them onto your PC, make sure that for all images intended for the same 3D image have the same filename followed by a digit that increases as the images were taken from left to right, for example:
DSCN0362.JPG - leftmost image
DSCN0363.JPG - middle image
DSCN0365.JPG - rightmost image
If you only took 2 you could end them with L and R.
Note that the Popout3D only lists and displays files with valid names.

Movement
Stationary objects like buildings or scenery give good results.

Pictures of people should work, provided they can keep still for a few seconds. Objects like trees and water may be work in the right circumstances, for example if there isn't too much wind, and the water is placid.

Moving vehicles or people, or fast-flowing water like a waterfall or waves won't work.

Quality of Effect
A picture with objects at varying distances results in a convincing effect. Distant scenery won't work well, as there is little perspective effect anyway.

Some images are too difficult for the aligning software, and the resulting image is unusable.

Notes
Images must have exactly the same width and height in pixels. This makes editing the original L and R images difficult, but it can be done with a photo editor like rawTherapee which shows you the size that the edited image will have so you can match them. It is easier to edit the 3D image, although you can't crop Side-By-Side or Crossover ones.

Avoid images with all red or all cyan objects as they only appear in one eye so look weird.

Strange effects from nearby objects might be caused by the camera's depth of field being high. A shorter exposure will reduce the depth of field.
'''
# File Selection
label2text = '''
File
To process a single set of images which are all for the same subject, first use Open>File to choose any file from the set.

scenery1.jpg
scenery2.jpg
scenery3.jpg

Selecting any of these files will prepare you to process all of them. The program will create a 3D image for each pair of originals, so you are able to choose the best combination of images for left and right. It is not recommended to use more than 3 originals as the number of output images goes up dramatically:

2 originals produce 1 3D image
3 originals produce 3 3D images
4 originals produce 6 3D images
5 originals produce 10 3D images

All the 3D images get the same filename (except the final character) and extension as the originals, plus two digits and a letter each for the format and style. These examples are 'Anaglyph' format with 'Normal' style:

scenery12AN.jpg was made with scenery1.jpg for the left image and scenery2.jpg for the right.
scenery13AN.jpg was made with scenery1.jpg for the left image and scenery3.jpg for the right.
With images ending in L and R you would get sceneryLRAN.jpg.

Folder:
To process all the image sets in a folder, first use Open>folder to choose the folder with the sets of images.
'''

# 3D Image Options
label3text = '''
The format of the 3D image to be created may be:

Anaglyph
A red/cyan colour 3D image viewed with coloured spectacles. These are available very cheaply on the Web.

Side-by-side
A side-by-side 3D image viewed straight ahead. Left hand image on the left, right hand on the right. Some people can see these without a viewer, some can't.

Crossover
A side-by-side 3D image viewed with eyes crossed. Right hand image on the left, left hand on the right. Some people can see these without a viewer, some can't.

There are two styles available:

Normal
A normal 3D image with the front of the picture level with the screen.

Popout
A 'popout' image. In some cases the effect is startling, as the front of the 3D image will popout in front of the screen. In most cases there is little or no difference from "Normal".
'''
# Processing
label4text = '''
For the 3D effect to work it is essential that each pair of images is prefectly aligned vertically and rotationally. This is a vital step and it is very difficult to achieve when holding the camera and even when using image editing software. The program does this for you, it may take about 20 seconds per 3D image.

Note that an existing 3D image file will not be overwritten, so if you create a 3D file from a pair of images, then for some reason want to create a new 3D image from them, you will need to move, rename or delete the existing 3D image file first.

To start processing the selected images, click on "Queue", this will show a list of the images to be created in the panel to the left and the button will change to "Process". If you don't like the list, choose another File/Folder or Format/Style.
If you are happy with this list, press "Process", the button will change to "Reset". You can use the < and > buttons to look for completed 3D images. Only the recently processed images are shown. When you have finished checking them, press "Reset" to clear them and go back to the Files or Folder that you selected earlier - includes the new images. Using the Open menu or the Delete or process buttons will also reset the list.
 


Notes
Portrait images from a phone may be landscape photos with a rotation tag, the program rotates them to portrait for processing, but it doesn't change the originals.

Mobile phones from one manufacturer are suspected of producing 16:9 photos which do not conform to JPG standards.

The 3D images won't have valid EXIF tags.

Preferences from previous versions of the program are not loaded.

If you can't remember which of a pair of images was left and which was right, create a 3D image as usual. If it doesn't look right with your anaglyph glasses on normally, try with them on upside down, so the lenses swap sides. If the image now works you had the images the wrong way round - just rename them and create a new 3D image.

You can run Hugin yourself to experiment with other settings, it is available as a Flatpak.
'''
# View
label5text = '''
Scroll backwards and forwards through the images using < and >.

All
All the images in the chosen folder or set which follow the naming rules will be shown.

2D
Only 2D images in the chosen folder or set which follow the naming rules will be shown.

3D
Only 3D images in the chosen folder or set which follow the naming rules will be shown.

Triptych
3D images will be shown at the top with the 2D images they were made from shown beneath.

3D Image Types
These selections only affect 3D/Triptych views (see Processing for explanations). If you have created more than one type of 3D image, you won't want to have to keep swapping viewing devices as you go through the images, these buttons allow you to restrict which image types are shown.

Delete
If a 3D image is being displayed you may delete it. To ensure that you don't lose original images, 2D images cannot be deleted from within Popout3D. You could of course delete them using your file manager.

Note
You may need to view 3D images from further away than you might expect.
'''

#===============================================================================
def on_activate(app):
	global viewind
	##global image1, imageL, imageR, boxOuter1, boxImageL, boxImageR

	win = Gtk.ApplicationWindow(application=app)
	win.maximize()
	win.header = Gtk.HeaderBar()
	win.set_titlebar(win.header)
	win.present()

	#-----------------------------------------------------------------------------
	def ask(widget, response, param):
		global viewind
		if response == Gtk.ResponseType.OK:
			if param == 'preferences':
				with open(configfold + preffile, 'w') as fn:
					try:
						fn.write(version+'\n')
						fn.write(myfold+'\n')
						fn.write(myfile+'\n')
						fn.write(myext+'\n')
						fn.write(formatcode+'\n')
						fn.write(stylecode+'\n')
						fn.write(viewDim+'\n')
						fn.write(viewType+'\n')
					except:
						print('Failed to write preference file.')
			elif param == 'delete':
				ok = True 
				try: 
					os.remove(myfold + viewlist[viewind][0]+'.'+viewlist[viewind][1])
				except:
					ok = False
					showInfo('File not found.')
				if ok:
					makeviewlist(False); viewind = 0; findNext('<'); showImage() 			
					GbuttonProcess.set_label('Queue')
		widget.destroy()
		
	#-----------------------------------------------------------------------------
	def showInfo(messtext):
		message = Gtk.MessageDialog(title = 'Information', text = messtext)
		message.add_buttons('OK', Gtk.ResponseType.OK)
		message.set_transient_for(win); message.set_modal(win)
		message.set_default_response(Gtk.ResponseType.OK)
		message.connect('response', ask, None)
		message.show()

	#-----------------------------------------------------------------------------
	def showDelete():
		message = Gtk.MessageDialog(title = 'Are you sure?', 
			text = 'This will delete ' + viewlist[viewind][0]+'.'+viewlist[viewind][1])
		message.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'OK', Gtk.ResponseType.OK)
		message.set_transient_for(win); message.set_modal(win)		
		message.set_default_response(Gtk.ResponseType.OK)
		message.connect('response', ask, 'delete')
		message.show()
	
	#-----------------------------------------------------------------------------
	def showPreferences(action, button):
		message = Gtk.MessageDialog(title = 'Are you sure?', text = 'This will save your current settings as the defaults.')
		message.set_transient_for(win); message.set_modal(win)
		message.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'OK', Gtk.ResponseType.OK)
		message.set_default_response(Gtk.ResponseType.OK)
		message.connect('response', ask, 'preferences')
		message.show()
		
	#-----------------------------------------------------------------------------
	def showAbout(action, button):
		message = Gtk.AboutDialog(transient_for=win, modal=True)
		message.set_logo_icon_name('com.github.PopoutApps.popout3d')
		message.set_program_name('Popout3D')
		message.set_version(version)
		message.set_comments('Create 3D images from photographs taken with an ordinary camera. ')
		message.set_website_label('Popout3D on GitHub')
		message.set_website('https://github.com/PopoutApps/popout3d')
		message.set_copyright('Copyright 2022, 2023 Chris Rogers')
		message.set_license_type(Gtk.License.GPL_3_0)
		message.set_authors(['PopoutApps'])
		message.add_credit_section(section_name='Image Alignment', people=['Hugin'])
		message.add_credit_section(section_name='Flatpak', people=['Alexander Mikhaylenko', 'Hubert Figuière', 'Bartłomiej Piotrowski','Nick Richards.'])
		message.show()

	#-----------------------------------------------------------------------------
	def	showHelp(action, button):
		message = Gtk.Window()
		message.set_title('How to use Popout3D')
		message.set_default_size(1000, 700)
		message.set_child(notebook)
		message.set_transient_for(win); message.set_modal(win)
		message.show()
	
	#-----------------------------------------------------------------------------
	def readpreferences():
		global version, myfold, myfile, myext, formatcode, stylecode, viewDim, scope, viewType, firstrun
		# local okpref, okcol, ver, i
		# Preference file is not present when program is installed, so shows whether this is the first run.
	
		# create preferences array
		prefdata = []
		for i in range(8):
			prefdata.append('')

		# load preferences file, if file not found or is wrong version skip to end
		# if any fields are bad, replace with default
		okpref = True
		try:
			with open(configfold + preffile, 'r') as infile:
				ver = infile.readline()[:-1]
				#prefdata[i] = prefdata[i][:-1] # remove linefeed
				if ver != version:
					okpref = False				
		except:
			okpref = False
	
		if okpref:
			try:
				with open(configfold + preffile, 'r') as infile:
					for i in range(0, 8):
						prefdata[i] = infile.readline()
						prefdata[i] = prefdata[i][:-1]
			except:
				okpref = False

		if okpref:					
			if os.path.exists(prefdata[1]):
				myfold = prefdata[1]
			else:
				myfold = homefold #1.5.31
		
			myfile = prefdata[2] ; myext = prefdata[3]; scope = 'File'
			#153 note this doesn't check the ? character is valid, but it shouldn't be possible
			# to save an invalid one. Should only occur if preference file was edited
			if not glob.glob(myfold+'/'+myfile+'?.'+myext): 
				myfile == ''; myext == ''; scope = 'Folder' #1.5.31
		
			if prefdata[4] in ['A', 'S', 'C']: # Anaglyph/Side-by-Side/Crossover
				formatcode = prefdata[4]
			else:
				formatcode = 'A'

			if prefdata[5] in ['N','P']: # Normal (Level)/Popout
				stylecode = prefdata[5]
			else:
				stylecode = 'N'

			if prefdata[6] in ['All', '2D', '3D', 'Triptych']:
				viewDim = prefdata[6]
			else:
				viewDim = 'All'
		
			if (prefdata[7][0] in 'A-' and prefdata[7][1] in 'S-' and prefdata[7][2] in 'C-' 
				and	prefdata[7][3] in 'N-' and prefdata[7][4] in 'P-'):
				viewType = prefdata[7]
			else:
				viewType = 'ASCNP'

		if okpref:
			firstrun = False
		else: # defaults
			#version already set
			myfold = homefold #1.5.31
			myfile = '' #1.5.31
			myext = '' #1.5.31
			formatcode = 'A'
			stylecode = 'N'
			viewDim = 'All'
			viewType = 'ASCNP'
		
			# write pref file anyway in case mydir/myfile have been deleted or any other problem
			with open(configfold + preffile, 'w') as fn:			
				fn.write(version+'\n')
				fn.write(myfold+'\n')
				fn.write(myfile+'\n')
				fn.write(myext+'\n')
				fn.write(formatcode+'\n')
				fn.write(stylecode+'\n')
				fn.write(viewDim+'\n')
				fn.write(viewType+'\n')

	#-----------------------------------------------------------------------------		 
	def exif(newfilename, newext):
		'''
		Open file, get tags, if processing turn and save the image.
		Returns orientation, except 'notfound' if file missing and 'tagerror' if exif flags not available.
		'''
		global pixbuf, error
		# local orientationTag

		orientationTag = 'None'
		if os.path.isfile(myfold+newfilename+'.'+newext):
			try:
				image = Image.open(myfold+newfilename+'.'+newext)
			except:
				return 'notfound'
		else:		
			return 'notfound'
	
		try:
			image_exif = image.getexif()
		except AssertionError as error:
			print('image.exif() error: ', error)
			image.close
			return 'tagerror'

		for tag_id in image_exif:
			tag=TAGS.get(tag_id,tag_id)
			data=image_exif.get(tag_id)
			if isinstance(data,bytes):
				try:
					data=data.decode()
				except:
					image.close
					return 'tagerror'	
			#print(f'{tag:20}:{data}')
			if tag == 'Orientation':
				orientationTag = str(data)

		image.close
		return orientationTag

	#-----------------------------------------------------------------------------
	def findMatch():
		global viewind # local searchlength, char1, char2, charN, viewindL, viewindR, viewindN

		if len(viewlist) > 0 and viewDim != 'All': # Can use same image if switching viewDim to All
			searchfilename = viewlist[viewind][0]; searchlength = -1 
			searchext = viewlist[viewind][1]; dimensions = viewlist[viewind][2]
			char1 = char2 = ''; viewindL = viewindR = viewindN = -1

			if not (viewDim == 'All' or viewDim == dimensions or (viewDim == 'Triptych' and dimensions == '3D')):		
				# switching viewDim to 2D
				# get basic filename, length and 2 characters
				if viewDim == '2D' and dimensions == '3D':
					searchname = searchfilename[:-4];	searchlength = len(searchname)
					char1 = searchfilename[-4]; char2 = searchfilename[-3]

					# search through list
					viewindL = viewindR = viewindN = -1
					for record in viewlist:
						if record[1] == searchext and record[2] == '2D':					
							if viewindL < 0 and searchname+char1 in record[0][:searchlength+1]:
								viewindL = viewlist.index(record) # L of 3D image matches a 2D image
							elif viewindR < 0 and searchname+char2 in record[0][:searchlength+1]:
								viewindR = viewlist.index(record) # R of 3D image matches a 2D image
							elif viewindN < 0 and searchname in record[0][:searchlength]:
								viewindN = viewlist.index(record) # match for basic name
	
				# switching viewDim to 3D
				# get basic filename and 1 character
				elif viewDim in ('3D', 'Triptych') and dimensions == '2D':
					searchname = searchfilename[:-1];	searchlength = len(searchname)
					char1 = searchfilename[-1]; char2 = ''
			
					# search through list
					viewindL = viewindR = viewindN = -1
					for record in viewlist:
						if (record[1] == searchext and record[2] == '3D'
							and record[0][-2] in viewType and record[0][-1] in viewType):
							if viewindL < 0 and searchname+char1 in record[0][:searchlength+1]:
								viewindL = viewlist.index(record) # char of 2D image matches 1st char of a 3D image
							elif viewindR < 0 and searchname+char1 in record[0][:searchlength]+record[0][-3]:
								viewindR = viewlist.index(record) # char of 2D image matches 2nd char of a 3D image
							elif viewindN < 0 and searchname in record[0][:searchlength]:
								viewindN = viewlist.index(record) # match for basic name

				if viewindL > -1:
					viewind = viewindL
				elif viewindR > -1:
					viewind = viewindR
				elif viewindN > -1:
					viewind = viewindN
				else:
					viewind = 0

	#-----------------------------------------------------------------------------
	def findNext(direction):
		global viewind
		#local found

		newviewind = viewind
		if direction == '>':
			newviewind = newviewind +1
		else:
			newviewind = newviewind -1

		found = False
		while found == False and len(viewlist) > 0 and newviewind > -1 and newviewind < len(viewlist): 
			if ((viewDim in ('All', '3D', 'Triptych') and viewlist[newviewind][2] == '3D'
				and viewlist[newviewind][0][-2] in viewType and viewlist[newviewind][0][-1] in viewType)			
			 or (viewDim in ('All', '2D') and viewlist[newviewind][2] == '2D')
					):
				found = True	
				viewind = newviewind
				return
			elif direction == '>':
				newviewind = newviewind +1
			else:
				newviewind = newviewind -1

	# if a further image wasn't found, leave viewind as it is.
		 
	#-----------------------------------------------------------------------------
	def makepairlist(newfile, newformatcode, newstylecode, newext):
		global warnings, pairlist, infolist, viewDim
		# local imagestodo, imagesok

		# find out how many images there are in this set
		imagestodo = 0 ; imagesok = False

		# check for one with a digit at end
		for i in range (0, 10):
			if os.path.isfile(myfold+newfile+str(i)+'.'+newext):
				imagestodo = imagestodo + 1

		if imagestodo > 1:
			imagesok = True

		# check for pair with L at end and R at end

		if os.path.isfile(myfold+newfile+'L'+'.'+newext) and os.path.isfile(myfold+newfile+'R'+'.'+newext):
			imagesok = True

		if imagesok:
			# loop through all valid image pairs

			# digits at the end
			leftn = 0 ; rightn = 1
			while leftn < 9: # only single digits

				# look for images ending in 1-9
				rightn = leftn + 1
				while rightn < 10: # top number is 9
					# if left and right images exist and there is no existing 3D one
					if (os.path.isfile(myfold+newfile+str(leftn)+'.'+newext) and os.path.isfile(myfold+newfile+str(rightn)+'.'+newext)
 					and not os.path.isfile(myfold+newfile+str(leftn)+str(rightn)+newformatcode+newstylecode+'.'+newext)) and [newfile, str(leftn), str(rightn), newformatcode, newstylecode, newext] not in pairlist:
						tagL = exif(newfile+str(leftn), newext)
						tagR = exif(newfile+str(rightn), newext)
						pairlist.append([newfile, str(leftn), str(rightn), newformatcode, newstylecode, newext, tagL, tagR])
					rightn = rightn + 1
				leftn = leftn + 1

			# look for images ending in L and R
			if (os.path.isfile(myfold+newfile+'L'+'.'+newext) and os.path.isfile(myfold+newfile+'R'+'.'+newext)
 		 and not os.path.isfile(myfold+newfile+'LR'+newformatcode+newstylecode+'.'+newext)) and [newfile, 'L', 'R', newformatcode, newstylecode, newext] not in pairlist:
				tagL = exif(newfile+str(leftn), newext)
				tagR = exif(newfile+str(rightn), newext)
				pairlist.append([newfile, 'L', 'R', newformatcode, newstylecode, newext, tagL, tagR])

#-------------------------------------------------------------------------------
	def makeviewlist(queuing):
		global viewlist, viewind, pairlist
		#local variables newfile, newext, infolist, tag
		tag = 'TAG'
		viewlist = []

		if queuing:
			# add all relevant images to viewlist
			for record in pairlist:
				#viewlist.append([record[0]+record[1], record[5], '2D', record[6]])		
				viewlist.append([record[0]+record[1]+record[2]+record[3]+record[4], record[5], '3D', ''])	
				#viewlist.append([record[0]+record[2], record[5], '2D', record[7]])		
		else:
			# 2D
			for newfile in os.listdir(myfold):			 
				newfile, newext = os.path.splitext(newfile) ; newext = newext[1:]		
				if len(newfile) > 1:
					if newext in okext and newfile[-1] in okchar:
						# set: only add files in set to viewlist

						# file
						if scope == 'File':
							if len(newfile) == len(myfile) +1:
								if newfile[0:-1] == myfile and newext == myext:
									tag = exif(newfile, newext)
									viewlist.append([newfile, newext, '2D', tag])

						# folder
						elif scope == 'Folder':
							tag = exif(newfile, newext)
							viewlist.append([newfile, newext, '2D', tag])

			# 3D
			for newfile in os.listdir(myfold):
				newfile, newext = os.path.splitext(newfile) ; newext = newext[1:]
				if len(newfile) > 4:
					if (newext in okext
					and newfile[-4] in okchar and newfile[-3] in okchar 
					and newfile[-2] in okformat and newfile[-1] in okstyle
					and newfile[-2] in viewType and newfile[-1] in viewType):

						# file
						if scope == 'File':
							if len(newfile) == len(myfile) +4:												 
								if newfile[0:-4] == myfile and newext == myext:
									tag = exif(newfile, newext)
									viewlist.append([newfile, newext, '3D', tag])

						# folder
						elif scope == 'Folder':
							tag = exif(newfile, newext)						
							viewlist.append([newfile, newext, '3D', tag])

			viewlist = sorted(viewlist)

		# make infolist
		infolist = ''
		for i in viewlist:
			if (i[2] == '2D' and not GbuttonProcess.get_label() == 'Reset') or i[2] == '3D':
				infolist = infolist+i[0]+'.'+i[1]+'\n'
		labelInfo.set_text(infolist)
		
	#-----------------------------------------------------------------------------	
	def showImage():
		global image1, imageL, imageR, boxOuter1, boxOuterL, boxOuterR
		#local newfilename1, newfilenameL, newfilenameR, newext1, newextL, newextR

		labelImage1.set_text('')
		labelImageL.set_text('')
		labelImageR.set_text('')
		
		for i in boxImage1:
			boxImage1.remove(i)
		for i in boxImageL:
			boxImageL.remove(i)
		for i in boxImageR:
			boxImageR.remove(i)

		if len(viewlist) > 0 and viewind > -1 and (
				(viewDim in ('All', '3D', 'Triptych') and viewlist[viewind][2] == '3D'
				and viewlist[viewind][0][-2] in viewType and viewlist[viewind][0][-1] in viewType
				)
			or
				(viewDim in ('All', '2D') and viewlist[viewind][2] == '2D')   
			):

			# two 2D images for triptych	
			if viewDim == 'Triptych':
				
				# Left 2D image
				newfilenameL = viewlist[viewind][0][:-4]+viewlist[viewind][0][-4]; newextL = viewlist[viewind][1]
				labelImageL.set_markup('<b>'+newfilenameL+'.'+newextL+'</b>')

				if os.path.isfile(myfold+newfilenameL+'.'+newextL):
					orientationL = viewlist[viewind][3]				
					if orientationL == '3': # upside down, so rotate 180 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameL+'.'+newextL), 180)
					elif orientationL == '6': # top at right so rotate 270 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameL+'.'+newextL), 270)
					elif orientationL == '8': #top pointing left so rotate 90 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameL+'.'+newextL), 90)
					elif orientationL == 'notfound':
						pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)
					else:
						pixbuf = GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameL+'.'+newextL)
				else:
					pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)

				imageL = Gtk.Picture.new_for_pixbuf(pixbuf)
				imageL.props.hexpand = True	
				imageL.props.content_fit = Gtk.ContentFit.CONTAIN
				boxImageL.append(imageL)

				# Right 2D image
				newfilenameR = viewlist[viewind][0][:-4]+viewlist[viewind][0][-3]; newextR = viewlist[viewind][1]
				labelImageR.set_markup('<b>'+newfilenameR+'.'+newextR+'</b>')

				if os.path.isfile(myfold+newfilenameR+'.'+newextR):
					orientationR = viewlist[viewind][3]
					if orientationR == '3': # upside down, so rotate 180 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from__file_at_scale(myfold+newfilenameR+'.'+newextR), 180)
					elif orientationR == '6': # top at right so rotate 270 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameR+'.'+newextR), 270)
					elif orientationR == '8': #top pointing left so rotate 90 clockwise
						pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameR+'.'+newextR), 90)
					elif orientationR == 'notfound':
						pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)
					else:
						pixbuf = GdkPixbuf.Pixbuf.new_from_file(myfold+newfilenameR+'.'+newextR)
				else:
					pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile) 

				imageR = Gtk.Picture.new_for_pixbuf(pixbuf)
				imageR.props.hexpand = True	
				imageR.props.content_fit = Gtk.ContentFit.CONTAIN
				boxImageR.append(imageR)
				
			# image 1 must be last so it doesn't take all the space in a Triptych
			newfilename1 = viewlist[viewind][0]; newext1 = viewlist[viewind][1]
			labelImage1.set_markup('<b>'+newfilename1+'.'+newext1+'</b>')

			if os.path.isfile(myfold+newfilename1+'.'+newext1):
				orientation1 = viewlist[viewind][3]
				if orientation1 == '3': # upside down, so rotate 180 clockwise
					pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilename1+'.'+newext1), 180)
				elif orientation1 == '6': # top at right so rotate 270 clockwise
					pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilename1+'.'+newext1), 270)
				elif orientation1 == '8': #top pointing left so rotate 90 clockwise
					pixbuf = GdkPixbuf.Pixbuf.rotate_simple(GdkPixbuf.Pixbuf.new_from_file(myfold+newfilename1+'.'+newext1), 90)
				elif orientation1 == 'notfound': # file missing #redundant
					pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)
				else: #already upright or could not be determined
					pixbuf = GdkPixbuf.Pixbuf.new_from_file(myfold+newfilename1+'.'+newext1)
			else: # not found
				pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)

		else:
			pixbuf = GdkPixbuf.Pixbuf.new_from_file(datafold+dummyfile)

		image1 = Gtk.Picture.new_for_pixbuf(pixbuf)
		image1.props.hexpand = True; image1.props.vexpand = True
		image1.props.content_fit = Gtk.ContentFit.CONTAIN
		boxImage1.append(image1)

	#-----------------------------------------------------------------------------
	def checkpairlist():
		global pairlist
		#local warnings, existsLeft, existsRight, imageLeftFormat, imageRightFormat, imageLeftSize, imageRightSize
		warnings = ''

		for i in pairlist: # open images and get image type and size
			try:
				image = Image.open(myfold+i[0]+i[1]+'.'+i[5])
				imageLeftFormat = image.format ; imageLeftSize = image.size
				existsLeft = True
				image.close
			except:
				warnings = warnings +'Unable to load left image '+myfold+i[0]+i[1]+'.'+i[5]+'.\n'
				existsLeft = False
				pairlist.remove(i)				
			try:
				image = Image.open(myfold+i[0]+i[2]+'.'+i[5])
				imageRightFormat = image.format ; imageRightSize = image.size
				existsRight = True
				image.close
			except:
				warnings = warnings +'Unable to load right image '+myfold+i[0]+i[2]+'.'+i[5]+'.\n'
				existsRight = False
				pairlist.remove(i)
					
			if existsLeft and existsRight:
				if imageLeftFormat != imageRightFormat:
					warnings = warnings +i[0]+i[1]+'.'+i[5]+' and '+i[0]+i[2]+'.'+i[5]+' can not be used as they have different filetypes.\n'
					pairlist.remove(i)
				if imageLeftSize != imageRightSize:
					warnings = warnings +i[0]+i[1]+'.'+i[5]+' '+str(imageLeftSize)+' and '+i[0]+i[2]+'.'+i[5]+' '+str(imageRightSize)+' can not be used as their dimensions do not match.\n'
					pairlist.remove(i)
							
		if warnings != '':		
			showInfo(warnings)

	#-----------------------------------------------------------------------------
	def processPairlist(pairlist):
		#global warnings
		#local tagL, tagR, foldL, foldR
	
		with open(workfold + blockfile, 'w') as fn:			
			fn.write('BLOCK'+'\n')
			fn.close()

		for record in pairlist:
			if os.path.isfile(workfold+stopfile):
				break
			
			newfile = record[0]; leftn = record[1]; rightn = record[2]; newformatcode = record[3]; newstylecode = record[4]; newext = record[5]; tagL = record[6]; tagR = record[7]
		
			# make filenames then call align_image_stack
			fileout	= newfile+leftn+rightn+newformatcode+newstylecode+'.'+newext
			fileleft	= newfile+leftn+'.'+newext
			fileright = newfile+rightn+'.'+newext

			# turn image if needed and put into workfold
			foldL = foldR = myfold	
			if tagL in ['3', '6', '8']: # rotate image	
				if os.path.isfile(myfold+fileleft):
					try:
						image = Image.open(myfold+fileleft)
						image = ImageOps.exif_transpose(image)
						#image.save(workfold+fileleft, quality=95, subsampling='4:4:4')
						if newext in tifext:
							image.save(workfold+fileleft) 
						else:
							image.save(workfold+fileleft, quality=95, subsampling='4:4:4')
						foldL = workfold
					except:
						pass	

			if tagR in ['3', '6', '8']: # rotate image	
				if os.path.isfile(myfold+fileright):
					try:
						image = Image.open(myfold+fileright)
						image = ImageOps.exif_transpose(image)
						#image.save(workfold+fileright, quality=95, subsampling='4:4:4')
						if newext in tifext:
							image.save(workfold+fileright) 
						else:
							image.save(workfold+fileright, quality=95, subsampling='4:4:4')
						foldR = workfold	
					except:
						pass	
		
			#replace A and P with styleAIS
			if stylecode == 'N':		
				styleAIS = 'A'
			else:
				styleAIS = 'P'

			#command	 = 'align_image_stack -a "'+workfold+fileout+'" -m -i -P -C "'+workfold+'right.'+newext+'" "'+workfold+'left.'+newext+'"' 
			#command	 = 'align_image_stack -a "'+workfold+fileout+'" -m -i --use-given-order -"'+styleAIS+'" -C "'+foldR+fileright+'" "'+foldL+fileleft+'"' #-v {verbose}
			command	 = 'align_image_stack -a "'+workfold+fileout+'" -"'+styleAIS+'" -C "'+foldR+fileright+'" "'+foldL+fileleft+'"' #-v {verbose} #-i favour centre of images

			args = shlex.split(command) 
		
			print('Aligning ', workfold+fileout) # For checking which files cause the problem
			result = os.system(command)
 		
			# remove turned images if they exist
			if os.path.isfile(workfold+fileleft):
				os.remove(workfold+fileleft)
			if os.path.isfile(workfold+fileright):
				os.remove(workfold+fileright)

			# align_image_stack has worked
			if result == 0: 
				# load left and right images
				image_left = Image.open(workfold+fileout+'0001.tif')
				image_right = Image.open(workfold+fileout+'0000.tif')

				# merge the files, put result in myfold
				if formatcode == 'A': # Anaglyph			
					Lred	 = image_left.getchannel('R')
					Rgreen = image_right.getchannel('G')
					Rblue	 = image_right.getchannel('B')
					# merge the 3 colours
					image_new = Image.merge('RGB', (Lred, Rgreen, Rblue))
			
				elif formatcode == 'S': # Side-by-Side
					image_width = int(image_left.size[0]) ; image_height = int(image_left.size[1])
					# create double-width blank new image
					image_new = Image.new('RGB', (image_width * 2, image_height), color=0)
					# paste left image into new image on the left
					image_new.paste(image_left, (0, 0, image_width, image_height))
					# paste right image into new image on the right
					image_new.paste(image_right, (image_width, 0, 2 * image_width, image_height))

				else : # Crossover
					image_width = int(image_left.size[0]) ; image_height = int(image_left.size[1])
					# create double-width blank new image
					image_new = Image.new('RGB', (image_width * 2, image_height), color=0)
					# paste right image into new image on the left
					image_new.paste(image_right, (0, 0, image_width, image_height))
					# paste left image into new image on the right
					image_new.paste(image_left, (image_width, 0, 2 * image_width, image_height))

				# attempt to avoid fringing but subsampling doesn't work for TIF files
				if newext in tifext:
					image_new.save(myfold+fileout) 
				else:
					image_new.save(myfold+fileout, quality=95, subsampling='4:4:4')

				# close delete input and delete intermediate files 
				image_left.close ; image_right.close
					 
				if os.path.isfile(workfold+fileout+'0001.tif'):
					os.remove(workfold+fileout+'0001.tif')
				if os.path.isfile(workfold+fileout+'0000.tif'):
					os.remove(workfold+fileout+'0000.tif') 
			else:
				pass # warnings = warnings + 'It was not possible to align '+fileout+'.\n'
		
		if os.path.isfile(workfold+blockfile):
				os.remove(workfold+blockfile)

	#-----------------------------------------------------------------------------			
	def buttonPrev(button):
		findNext('<')		
		showImage()
		if GbuttonProcess.get_label() == 'Reset':
			if os.path.isfile(workfold+blockfile):
				labelInfoTitle.set_markup('<b>Processing 3D Images</b>')
			else:
				labelInfoTitle.set_markup('<b>Completed 3D Images</b>')
	
	def buttonNext(button):
		findNext('>')	
		showImage()
		if GbuttonProcess.get_label() == 'Reset':
			if os.path.isfile(workfold+blockfile):
				labelInfoTitle.set_markup('<b>Processing 3D Images</b>')
			else:
				labelInfoTitle.set_markup('<b>Completed 3D Images</b>')

	#-----------------
	def tickViewAll(menuitem): 
		global viewDim
		if menuitem.get_active():	
			viewDim = 'All'
			if not startup:
				findMatch(); showImage()
					
	def tickView2D(menuitem):
		global viewDim
		if menuitem.get_active():
			viewDim = '2D'
			if not startup:
				findMatch(); showImage()
			
	def tickView3D(menuitem):
		global viewDim
		if menuitem.get_active():
			viewDim = '3D'
			if not startup:
				findMatch(); showImage()
	
	def tickViewTriptych(menuitem):
		global viewDim
		if menuitem.get_active():
			viewDim = 'Triptych'
			if not startup:
				findMatch(); showImage()
				
	#-----------------		
	def tickViewAnaglyph(menuitem):
		global viewType
		if menuitem.get_active():	
			if not startup:
				findMatch(); showImage()
			viewType = viewType[:0] + 'A' + viewType[1:]
		else:
			viewType = viewType[:0] + '-' + viewType[1:]
									
	def tickViewSidebyside(menuitem):
		global viewType
		if menuitem.get_active():	
			if not startup:
				findMatch(); showImage()
			viewType = viewType[:1] + 'S' + viewType[2:]
		else:
			viewType = viewType[:1] + '-' + viewType[2:]
										
	def tickViewCrossover(menuitem):
		global viewType
		if menuitem.get_active():	
			if not startup:
				findMatch(); showImage()
			viewType = viewType[:2] + 'C' + viewType[3:]
		else:
			viewType = viewType[:2] + '-' + viewType[3:]

	def tickViewNormal(menuitem):
		global viewType
		if menuitem.get_active():	
			if not startup:
				findMatch(); showImage()
			viewType = viewType[:3] + 'N' + viewType[4:]
		else:
			viewType = viewType[:3] + '-' + viewType[4:]

	def tickViewPopout(menuitem):
		global viewType
		if menuitem.get_active():	
			if not startup:
				findMatch(); showImage()
			viewType = viewType[:4] + 'P' + viewType[5:]
		else:
			viewType = viewType[:4] + '-' + viewType[5:]

	#-----------------			
	def tickAnaglyph(menuitem):
		global formatcode, pairlist
		if menuitem.get_active():
			formatcode = 'A'
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			pairlist = []						
			makeviewlist(False)#; viewind = 0; findNext('<'); showImage()

	def tickSidebyside(menuitem):
		global formatcode, pairlist
		if menuitem.get_active():
			formatcode = 'S'
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			pairlist = []						
			makeviewlist(False)#; viewind = 0; findNext('<'); showImage()
							
	def tickCrossover(menuitem):
		global formatcode, pairlist
		if menuitem.get_active():
			formatcode = 'C'
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			pairlist = []						
			makeviewlist(False)#; viewind = 0; findNext('<'); showImage()

	def tickNormal(menuitem):
		global stylecode, pairlist
		if menuitem.get_active():
			stylecode = 'N'
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			pairlist = []						
			makeviewlist(False)#; viewind = 0; findNext('<'); showImage()

	def tickPopout(menuitem):
		global stylecode, pairlist
		if menuitem.get_active():
			stylecode = 'P'
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			pairlist = []						
			makeviewlist(False)#; viewind = 0; findNext('<'); showImage()

	#-----------------------------------------------------------------------------			
	def buttonProcess(button):
		global warnings, viewDim, pairlist, infolist, viewind
		global viewlist
		# local okleft, okright
		# pairlist filename style is name less last digit		

		# DO NOTHING Still processing
		if os.path.isfile(workfold+blockfile):
			showInfo('Please wait for the current processing to finish.')

		# QUEUE empty pairlist - make the list
		elif GbuttonProcess.get_label() == 'Queue': #not reset and pairlist == []:
			setlist = [];	warnings = ''

			# viewlist record ['DONEtestL', 'png', '2D', '8']
			# setlist record  ['DONEtest', 'A', 'N', 'jpg']
			# pairlist record ['DONEtest', 'L', 'R', 'A', 'N', 'jpg', '8', '8']
						
			# put one filename for each set into setlist
			for record in viewlist:
				if [record[0][:-1], formatcode, stylecode, record[1]] not in setlist:
					setlist.append([record[0][:-1], formatcode, stylecode, record[1]])				
			setlist = sorted(setlist)		

			# setlist record ['DONEtest', 'A', 'N', 'jpg']
			for record in setlist:
				makepairlist(record[0], record[1], record[2], record[3])
			setlist = []	
			
			checkpairlist() # remove any which don't match format and size.

			# pairlist record ['DONEtest', 'L', 'R', 'A', 'N', 'jpg', '8', '8']
			# viewlist record ['DONEtestL', 'png', '2D', '8']
		
			# make infolist and templist of projected images
			if pairlist != []:
				makeviewlist(True); viewind = 0; findNext('<'); showImage()
				labelInfoTitle.set_markup('<b>Queue</b>')
				GbuttonProcess.set_label('Process'); GbuttonProcess.props.tooltip_text = tipProcess
				GtickView3D.set_active(True)
			else: # empty list - warn nothing to process
				makeviewlist(False); viewind = 0; findNext('<'); showImage()
				showInfo('Nothing to process.')
			

		# RESET Button on Reset empty pairlist
		elif GbuttonProcess.get_label() == 'Reset': # and pairlist == []
			GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
			labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
			makeviewlist(False); findMatch(); showImage()

		# PROCESS
		else: # Process as list is not empty
			multi = multiprocessing.Process(target = processPairlist, args=(pairlist,))				
			multi.start()
						
			pairlist = []
			GbuttonProcess.set_label('Reset'); GbuttonProcess.props.tooltip_text = tipReset
			GtickView3D.set_active(True)
			viewDim = '3D'; viewind = 0; findNext('<'); showImage()		
			labelInfoTitle.set_markup('<b>Processing 3D Images</b>')

		warnings = ''			

	def buttonDelete(button): # was (self, button)
		global viewind
		#local ok
		if len(viewlist) > 0:
			if os.path.isfile(myfold+viewlist[viewind][0]+'.'+viewlist[viewind][1]):
				if viewlist[viewind][2] == '3D':
					GbuttonProcess.set_label('Queue'); labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
					showDelete()
				else:
					showInfo('Only 3D images can be deleted.')							
			else:
				showInfo('Image does not exist.')							
		else:
			showInfo('No 3D images to delete.')
				
	def show_open_dialog_file(win, anything):
		GbuttonProcess.set_label('Queue'); labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
		open_dialog_file.show()	
		
	def show_open_dialog_folder(win, anything):
		GbuttonProcess.set_label('Queue'); labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
		open_dialog_folder.show()	
				
	def open_response_file(dialog, response): #was menuItemSet(self, menuitem)
		global myfold, myfile, myext, scope, pairlist, viewind
		#local okfile
				
		if response == Gtk.ResponseType.ACCEPT:		
			file = dialog.get_file()
			newfile = file.get_path()
		else: # answered No or closed window
			return

		newfold, newfile = os.path.split(newfile)
		newfile, newext = os.path.splitext(newfile)				

		okfile = True			
		if len(newfile) > 1:
			if newfile[-1] in okchar:
				myfold = newfold +'/' ; myfile = newfile[:-1]; myext = newext[1:]
			elif len(newfile) > 4:
				if (newfile[-4] in okchar and newfile[-3] in okchar and newfile[-2] in okformat and newfile[-1] in okstyle):
					myfold = newfold +'/' ; myfile = newfile[:-4]; myext = newext[1:] 
				else:
					showInfo('Filename must follow rules in Help on File Selection.')
					return
			else:
				showInfo('Filename must follow rules in Help on File Selection.')
				return

			win.set_title(myfold + myfile + '*.' + myext)
			
		os.chdir(newfold)
		pairlist = []; GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue
		scope = 'File'; labelInfoTitle.set_markup('<b>' + scope + ' Selection</b>')
		
		makeviewlist(False); viewind = 0; findNext('<')
		if len(viewlist) > 0: #1.5.31
			if not  (
							(viewDim in('All', '3D', 'Triptych') and viewlist[viewind][2] == '3D')
							or
							(viewDim in ('All', '2D') and viewlist[viewind][2] == '2D')
							):
				findNext('>')

		showImage()
			
	def open_response_folder(dialog, response): #was menuItemFolder(self, menuitem)
		global myfold, myfile, myext, scope, pairlist, viewind
		
		if response == Gtk.ResponseType.ACCEPT:
			file = dialog.get_file()
			newfold = file.get_path()

			newfold = newfold+'/'	
			myfold = newfold; os.chdir(myfold) 
			myfile = ''; myext = ''
			pairlist = []; GbuttonProcess.set_label('Queue'); GbuttonProcess.props.tooltip_text = tipQueue

			scope = 'Folder'
			makeviewlist(False); viewind = 0; findNext('<')
			if len(viewlist) > 0:
				if not  (
								(viewDim in('All', '3D', 'Triptych') and viewlist[viewind][2] == '3D')
								or
								(viewDim in ('All', '2D') and viewlist[viewind][2] == '2D')
								):
					findNext('>')

			win.set_title(myfold)
			showImage()
			
	#============================================================================= 
	# notebook
	notebook = Gtk.Notebook()
	notebook.set_tab_pos(Gtk.PositionType.LEFT)
	
	label0 = Gtk.Label.new(label0text)
	label0.props.justify = Gtk.Justification.LEFT; label0.props.yalign = 0#; label0.props.xalign = .5
	label0.set_wrap(True)
	page0 = Gtk.ScrolledWindow()
	page0.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page0.set_child(label0)
	notebook.append_page(page0)
	notebook.set_tab_label_text(page0, 'Basics')

	label1 = Gtk.Label.new(label1text)
	label1.props.justify = Gtk.Justification.LEFT; label1.props.yalign = 0#; label1.props.xalign = .5
	label1.set_wrap(True)
	page1 = Gtk.ScrolledWindow()
	page1.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page1.set_child(label1)
	notebook.append_page(page1)
	notebook.set_tab_label_text(page1, 'Source Photographs')
		
	label2 = Gtk.Label.new(label2text)
	label2.props.justify = Gtk.Justification.LEFT; label2.props.yalign = 0#; label2.props.xalign = .5
	label2.set_wrap(True)
	page2 = Gtk.ScrolledWindow()
	page2.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page2.set_child(label2)
	notebook.append_page(page2)
	notebook.set_tab_label_text(page2, 'File Selection')
		
	label3 = Gtk.Label.new(label3text)
	label3.props.justify = Gtk.Justification.LEFT; label3.props.yalign = 0#; label3.props.xalign = .5
	label3.set_wrap(True)
	page3 = Gtk.ScrolledWindow()
	page3.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page3.set_child(label3)
	notebook.append_page(page3)
	notebook.set_tab_label_text(page3, '3D Image Options')
	
	label4 = Gtk.Label.new(label4text)
	label4.props.justify = Gtk.Justification.LEFT; label4.props.yalign = 0#; label4.props.xalign = .5
	label4.set_wrap(True)
	page4 = Gtk.ScrolledWindow()
	page4.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page4.set_child(label4)
	notebook.append_page(page4)
	notebook.set_tab_label_text(page4, 'Process')
	
	label5 = Gtk.Label.new(label5text)
	label5.props.justify = Gtk.Justification.LEFT; label5.props.yalign = 0#; label5.props.xalign = .5
	label5.set_wrap(True)
	page5 = Gtk.ScrolledWindow()
	page5.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
	page5.set_child(label5)
	notebook.append_page(page5)
	notebook.set_tab_label_text(page5, 'View')

	# BOXES-----------------------------------------------------------------------
	separatorView = Gtk.Separator(); separatorProcess = Gtk.Separator(); separatorInfo = Gtk.Separator()
	separatorDisplay = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

	for i in (separatorView, separatorProcess, separatorInfo, separatorDisplay):
	  i.set_margin_top(5); i.set_margin_bottom(10)
	separatorDisplay.set_margin_end(10)

  # create boxes and images
	boxWindow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
	boxOptions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxDisplay = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)  

	boxView = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxViewT = Gtk.CenterBox()
	boxViewT3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxViewButton = Gtk.CenterBox()

	boxProcess = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxProcessT = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
	boxProcessL = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxProcessR = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxProcessButton = Gtk.CenterBox()

	# put boxes within boxes
	win.set_child(boxWindow)  # Horizontal box to window
	boxWindow.append(boxOptions) # Put vert box in that box
	boxWindow.append(boxDisplay)
	boxOptions.append(boxView)
	
	labelView = Gtk.Label.new(); labelView.set_markup('<b>View</b>')
	boxView.append(labelView)
	boxView.append(boxViewT)
	labelViewtype = Gtk.Label.new(); labelViewtype.set_markup('<b>3D Image Types</b>')
	boxView.append(labelViewtype)

	boxOptions.append(boxProcess)
	boxProcess.append(separatorProcess)
	labelProcess = Gtk.Label.new(); labelProcess.set_markup('<b>Process</b>')
	boxProcess.append(labelProcess)
	boxProcess.append(boxProcessT)
	boxProcessT.append(boxProcessL)
	boxProcess.append(boxProcessButton)
	
	labelFormat = Gtk.Label.new(); labelFormat.set_markup('<b>Format</b>')
	labelFormat.props.xalign = 0
	boxProcessL.append(labelFormat)
	boxProcessT.append(boxProcessR)

	labelStyle = Gtk.Label.new(); labelStyle.set_markup('<b>Style</b>')
	labelStyle.props.xalign = 0
	boxProcessR.append(labelStyle)

	boxInfo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxOptions.append(boxInfo)
	boxInfo.append(separatorInfo)

	# These need renaming to Info so fixed ones above can be changed to something more relevant.
	labelInfoTitle = Gtk.Label.new(); boxInfo.append(labelInfoTitle)

	# This is the list of files
	labelInfoScroll = Gtk.ScrolledWindow()
	labelInfoScroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
	boxInfo.append(labelInfoScroll)

	labelInfoScroll.props.vexpand = True
	labelInfoScroll.props.valign = Gtk.Align.FILL

	labelInfo = Gtk.Label.new('{None}')
	labelInfoScroll.set_child(labelInfo)

	labelInfo.props.valign = Gtk.Align.START
	labelInfo.props.halign = Gtk.Align.START

	# display---------------------------------------------------------------------	
	boxPrev = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)  
	boxImages = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxOuter1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxImagesLR = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)  
	boxOuterL = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxOuterR = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  
	boxNext = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)  
	boxLabelImage1 = Gtk.Box(); boxLabelImageL = Gtk.Box(); boxLabelImageR = Gtk.Box()
	boxImage1 = Gtk.Box(); boxImageL = Gtk.Box(); boxImageR = Gtk.Box()

	labelImage1 = Gtk.Label.new('Image1'); labelImageL = Gtk.Label.new('ImageL'); labelImageR = Gtk.Label.new('ImageR')
	boxLabelImage1.props.halign = Gtk.Align.CENTER; boxLabelImageL.props.halign = Gtk.Align.CENTER; boxLabelImageR.props.halign = Gtk.Align.CENTER
	image1 = Gtk.Picture(); imageL = Gtk.Picture(); imageR = Gtk.Picture()

	boxDisplay.append(separatorDisplay)
	boxDisplay.append(boxPrev)
	boxDisplay.append(boxImages)
	boxImages.append(boxOuter1)
	boxImages.append(boxImagesLR)
	boxImagesLR.append(boxOuterL); boxImagesLR.append(boxOuterR)
	boxOuter1.append(boxLabelImage1); boxOuterL.append(boxLabelImageL); boxOuterR.append(boxLabelImageR)
	boxOuter1.append(boxImage1); boxOuterL.append(boxImageL); boxOuterR.append(boxImageR)
	boxLabelImage1.append(labelImage1); boxLabelImageL.append(labelImageL); boxLabelImageR.append(labelImageR)	
	boxImage1.append(image1); boxImageL.append(imageL); boxImageR.append(imageR)	
	boxDisplay.append(boxNext)
	
	# margins---------------------------------------------------------------------
	for i in (boxView,	boxProcess,	boxInfo, boxImages):
	  i.set_margin_start(10); i.set_margin_end(10); i.set_margin_top(10)
	boxImages.set_margin_bottom(10)
	boxImagesLR.set_margin_top(5)
	
	# buttons---------------------------------------------------------------------
	# create
	GtickView2D = Gtk.CheckButton(label='2D'); GtickView2D.props.tooltip_text = tip2D
	GtickViewTriptych = Gtk.CheckButton(label='Triptych'); GtickViewTriptych.props.tooltip_text = tipTriptych
	GtickView3D = Gtk.CheckButton(label='3D'); GtickView3D.props.tooltip_text = tip3D
	GtickViewAll = Gtk.CheckButton(label='All'); GtickViewAll.props.tooltip_text = tipAll
	
	GtickViewAnaglyph = Gtk.CheckButton(label='Anaglyph'); GtickViewAnaglyph.props.tooltip_text = tipAnaglyph
	GtickViewSidebyside = Gtk.CheckButton(label='Side-By-Side'); GtickViewSidebyside.props.tooltip_text = tipSidebyside
	GtickViewCrossover = Gtk.CheckButton(label='Crossover'); GtickViewCrossover.props.tooltip_text = tipCrossover
	GtickViewNormal = Gtk.CheckButton(label='Normal'); GtickViewNormal.props.tooltip_text = tipNormal
	GtickViewPopout = Gtk.CheckButton(label='Popout'); GtickViewPopout.props.tooltip_text = tipPopout
	
	GtickAnaglyph = Gtk.CheckButton(label='Anaglyph'); GtickAnaglyph.props.tooltip_text = tipAnaglyph
	GtickSidebyside = Gtk.CheckButton(label='Side-By-Side'); GtickSidebyside.props.tooltip_text = tipSidebyside
	GtickCrossover = Gtk.CheckButton(label='Crossover'); GtickCrossover.props.tooltip_text = tipCrossover
	GtickNormal = Gtk.CheckButton(label='Normal'); GtickNormal.props.tooltip_text = tipNormal
	GtickPopout = Gtk.CheckButton(label='Popout'); GtickPopout.props.tooltip_text = tipPopout

	GbuttonDelete = Gtk.Button(label='Delete'); GbuttonDelete.props.tooltip_text = tipDelete	
	GbuttonProcess = Gtk.Button(label='Queue'); GbuttonProcess.props.tooltip_text = tipQueue

	GbuttonPrev = Gtk.Button(); GbuttonPrev.set_icon_name('go-previous-symbolic-symbolic'); GbuttonPrev.props.tooltip_text = tipPrev
	GbuttonNext = Gtk.Button(); GbuttonNext.set_icon_name('go-next-symbolic-symbolic'); GbuttonNext.props.tooltip_text = tipNext; GbuttonNext.props.valign = Gtk.Align.CENTER

	boxViewButton.set_center_widget(GbuttonDelete)
	boxProcessButton.set_center_widget(GbuttonProcess)
		
	boxViewT3.append(GtickViewTriptych)
	boxViewT3.append(GtickView3D)

	boxViewT.set_start_widget(GtickView2D)
	boxViewT.set_center_widget(boxViewT3)
	boxViewT.set_end_widget(GtickViewAll)
	
	boxViewType= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
	boxViewTypeL = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
	boxViewTypeR = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

	boxView.append(boxViewType)
	boxViewType.append(boxViewTypeL)
	boxViewType.append(boxViewTypeR)
	
	boxViewTypeL.append(GtickViewAnaglyph)	
	boxViewTypeL.append(GtickViewSidebyside)		
	boxViewTypeL.append(GtickViewCrossover)
	boxViewTypeR.append(GtickViewNormal)
	boxViewTypeR.append(GtickViewPopout)
	boxView.append(boxViewButton)

	boxProcessL.append(GtickAnaglyph)	
	boxProcessL.append(GtickSidebyside)		
	boxProcessL.append(GtickCrossover)
	boxProcessR.append(GtickNormal)
	boxProcessR.append(GtickPopout)

	boxPrev.set_center_widget(GbuttonPrev)
	boxNext.set_center_widget(GbuttonNext)

	# connect
	GtickViewAll.connect('toggled', tickViewAll)
	GtickView2D.connect('toggled', tickView2D)
	GtickView3D.connect('toggled', tickView3D)
	GtickViewTriptych.connect('toggled', tickViewTriptych)

	GtickViewAnaglyph.connect('toggled', tickViewAnaglyph)
	GtickViewSidebyside.connect('toggled', tickViewSidebyside)
	GtickViewCrossover.connect('toggled', tickViewCrossover)
	GtickViewNormal.connect('toggled', tickViewNormal)	
	GtickViewPopout.connect('toggled', tickViewPopout)

	GtickAnaglyph.connect('toggled', tickAnaglyph)
	GtickSidebyside.connect('toggled', tickSidebyside)
	GtickCrossover.connect('toggled', tickCrossover)
	GtickNormal.connect('toggled', tickNormal)	
	GtickPopout.connect('toggled', tickPopout)

	GbuttonPrev.connect('clicked', buttonPrev)
	GbuttonNext.connect('clicked', buttonNext)
	GbuttonDelete.connect('clicked', buttonDelete)
	GbuttonProcess.connect('clicked', buttonProcess)
	
	# group
	GtickView2D.set_group(GtickViewAll)
	GtickView3D.set_group(GtickViewAll)
	GtickViewTriptych.set_group(GtickViewAll)
	GtickSidebyside.set_group(GtickAnaglyph)
	GtickCrossover.set_group(GtickAnaglyph)
	GtickPopout.set_group(GtickNormal)

	#-----------------
	# open menu
	menu1 = Gio.Menu.new()
	menu1.append('Folder', 'win.menuitemFolder')
	menu1.append('File', 'win.menuitemFile')
	popover1 = Gtk.PopoverMenu() # Create a new popover menu
	popover1.set_menu_model(menu1)

	# Create open menu button
	menuOpen = Gtk.MenuButton(label='Open'); menuOpen.props.tooltip_text = tipOpen
	menuOpen.set_popover(popover1)
	win.header.pack_start(menuOpen)

	# add options to open menu
	action = Gio.SimpleAction.new('menuitemFolder') #, None)
	action.connect('activate', show_open_dialog_folder)
	win.add_action(action)	

	action = Gio.SimpleAction.new('menuitemFile') #, None)
	action.connect('activate', show_open_dialog_file)
	win.add_action(action)

	# file
	open_dialog_file = Gtk.FileChooserNative.new(title='Select any file from a set of images', parent=win, action=Gtk.FileChooserAction.OPEN)
	
	open_dialog_file.connect('response', open_response_file)
	
	f = Gtk.FileFilter()
	f.set_name('Image files')
	f.add_mime_type('image/jpeg')
	f.add_mime_type('image/tiff')
	f.add_mime_type('image/png')
	open_dialog_file.add_filter(f)

	# folder
	open_dialog_folder = Gtk.FileChooserNative.new(title='Select the Folder where the images are', parent = win, action=Gtk.FileChooserAction.SELECT_FOLDER)
	open_dialog_folder.connect('response', open_response_folder)
	
	#-----------------------------------------------------------------------------	
	# main stripey menu
	menu2 = Gio.Menu.new()
	menu2.append('Preferences', 'win.menuitemPreferences')
	menu2.append('Help', 'win.menuitemHelp')
	menu2.append('About Popout3D', 'win.menuitemAbout')

	# create Main menu menuStripey style
	# Create a popover
	popover2 = Gtk.PopoverMenu()
	popover2.set_menu_model(menu2)

	# Create a menu button
	menuStripey = Gtk.MenuButton()
	menuStripey.set_popover(popover2)
	menuStripey.set_icon_name('open-menu-symbolic')
	win.header.pack_end(menuStripey)
	
	# add options to main menu
	# preferences
	action = Gio.SimpleAction.new('menuitemPreferences')
	action.connect('activate', showPreferences)
	win.add_action(action)
	
	# help
	action = Gio.SimpleAction.new('menuitemHelp')
	action.connect('activate', showHelp)#, win)
	win.add_action(action)
	
	# about
	action = Gio.SimpleAction.new('menuitemAbout')
	action.connect('activate', showAbout)
	win.add_action(action)
	
	#-----------------------------------------------------------------------------
	readpreferences()

	if scope == 'Folder':
		#win.set_title(version + '			Folder: ' + myfold)
		win.set_title(myfold)
	else:
		#win.set_title(version + '			Set: ' + myfold + myfile + '*.' + myext)
		win.set_title(myfold + myfile + '*.' + myext)

	startup = True
	if viewDim == '2D':
		GtickView2D.set_active(True)
	elif viewDim == '3D':
		GtickView3D.set_active(True)
	elif viewDim == 'Triptych':
		GtickViewTriptych.set_active(True)
	else: # All
		GtickViewAll.set_active(True)		

	if 'A' in viewType:
		GtickViewAnaglyph.set_active(True)
		
	if 'S' in viewType:
		GtickViewSidebyside.set_active(True)
		
	if 'C' in viewType:
		GtickViewCrossover.set_active(True)
		
	if 'N' in viewType:
		GtickViewNormal.set_active(True)
		
	if 'P' in viewType:
		GtickViewPopout.set_active(True)

	if formatcode == 'S': # Side-by-Side
		GtickSidebyside.set_active(True)
	elif formatcode == 'C': # Crossover
		GtickCrossover.set_active(True)
	else:
		GtickAnaglyph.set_active(True)
		
	if stylecode == 'P': # Popout
		GtickPopout.set_active(True)
	else: # Normal
		GtickNormal.set_active(True)
	startup = False

	if firstrun:
		message = Gtk.MessageDialog(title = 'How to use Popout3D', text = label0text)
		message.set_modal(win); message.set_transient_for(win)
		message.add_buttons('OK', Gtk.ResponseType.OK)		
		response = message.connect('response', ask, None)
		message.show()
	
	makeviewlist(False); viewind = 0
	if len(viewlist) > 0:
		if not  (
						(viewlist[viewind][0][-2] in viewType and viewlist[viewind][0][-1] in viewType
						and viewDim in('All', '3D', 'Triptych') and viewlist[viewind][2] == '3D'
						)
						or
						(viewDim in ('All', '2D') and viewlist[viewind][2] == '2D')
						):
			findMatch()
	showImage()

	
app = Gtk.Application(application_id='com.github.PopoutApps.popout3d')
app.connect('activate', on_activate)
app.run(None)
