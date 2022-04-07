# Demo gist from jotony https://gist.github.com/jotonyguerra/3772f721b4e85fd8323e8d4994f08a83

import os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
#Very quick and plain example of using PIL.save() to save an image as a pdf.

#Initialize a Pillow Image Object
im = Image.open('PATH-TO-IMAGE') #optional .convert('RGB')
#save

#storing the resized image in x
x = im.resize( tuple(int,int) ) 
#getting the path name of the file excluding the extension
name, ext = os.path.splittext('PATH-TO-IMAGE')

#saving the image with the same name as a pdf, setting the DPI or resolution to 300.0 dots per inch.
x.save(name + '.pdf', resolution=300.0)

#Closing the image, not entirely necessary
im.close()