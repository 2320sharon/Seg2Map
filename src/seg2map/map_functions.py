import os
from typing import Set, Tuple, Union, List
from base64 import b64encode
from PIL import Image
from io import BytesIO
from base64 import encodebytes
from ipyleaflet import ImageOverlay
from PIL import Image

from seg2map import common

# convert greyscale tif to png files that can be rendered on the map
# file =r'C:\1_USGS\4_seg2map\seg2map\data\fresh_downloads\ID_NVBbrh_dates_2010-01-01_to_2013-12-31\multiband\2010\Mosaic.tif'
# save_path=r'C:\1_USGS\4_seg2map\seg2map'

def get_class_masks_overlay(tif_file:str, mask_output_dir:str, classes:List[str],year:str) -> List:
    """
    Given a path to a TIFF file, create binary masks for each class in the file and
    return a list of image overlay layers that can be used to display the masks over
    the original image.

    Args:
        tif_file (str): The path to the input TIFF file.
        mask_output_dir (str): The path to the directory where the output mask images
            will be saved.
        classes (List[str]): A list of class names to include in the masks.
        year(str): year that tif was created

    Returns:
        A list of image overlay layers, one for each class mask.
    """
    # get bounds of tif 
    bounds = common.get_bounds(tif_file)
    
    # get class names to create class mapping
    class_mapping = get_class_mapping(classes)
    
    # generate binary masks for each class in tif as a separate PNG in mask_output_dir
    class_masks = generate_class_masks(tif_file, class_mapping, mask_output_dir)
    
    # for each class mask PNG, create an image overlay
    layers = []
    for filename in class_masks:
        file_path = os.path.join(mask_output_dir, filename)
        new_filename=filename.split(".")[0] + "_"+year
        # combine mask name with save path
        image_overlay=get_overlay_for_image(file_path, bounds,new_filename,file_format='png')
        layers.append(image_overlay)
        
    return layers


def get_class_mapping(names:List[str])->dict:
    """Create a mapping of class names to integer labels.

    Given a list of class names, this function creates a dictionary that maps each
    class name to a unique integer label starting from 1.

    Parameters
    ----------
    names : list of str
        A list of class names to map to integer labels.

    Returns
    -------
    dict
        A dictionary mapping class names to integer labels.

    Ex:
      get_class_mapping(['water','sand'])
    {
        1:'water',
        2:'sand'
    }
    """
    class_mapping = {}
    for i, name in enumerate(names, start=1):
        class_mapping[i] = name
    return class_mapping

def generate_color_map(num_colors: int) -> dict:
    """
    Generate a color map for the specified number of colors.

    Args:
        num_colors (int): The number of colors needed.

    Returns:
        A dictionary containing a color map for the specified number of colors.
    """
    import colorsys

    # Generate a list of equally spaced hues
    hues = [i / num_colors for i in range(num_colors)]

    # Convert each hue to an RGB color tuple
    rgb_colors = [colorsys.hsv_to_rgb(h, 1.0, 1.0) for h in hues]

    # Scale each RGB value to the range [0, 255] and add to the color map
    color_map = {}
    for i, color in enumerate(rgb_colors):
        color_map[i] = tuple(int(255 * c) for c in color)

    return color_map


def generate_class_masks(file:str,class_mapping:dict,save_path:str)->List:
    """
    Create binary masks for each class in an input grayscale image and save them as PNG files
    in the specified directory.

    Args:
        file (str): The path to the input grayscale image file.
        class_mapping (dict): A dictionary mapping unique color values to class names.
        save_dir_path (str): The path to the directory where the output mask images will be saved.

    Returns:
        A list of filenames of the saved mask images.

    Raises:
        OSError: If there was an error accessing or saving the image files.
    """
    img_gray=Image.open(file)
    # unique colors: [(count,unique_color_value)....]
    # each pixel's color in img_gray can be one of the values 0,1,2,3....
    unique_colors=img_gray.getcolors()
    # create a color for each class
    color_map = generate_color_map(len(unique_colors))
    # for each unique color in file create a mask with the rest of the pixels being transparent
    files_saved=[]
    for i, (count, color) in enumerate(unique_colors):
        filename = class_mapping[color]
        image_name=f"{filename}.png"
        mask = img_gray.point(lambda x: 255 * (x == color))
        mask_img = Image.new("RGBA", (img_gray.width, img_gray.height), (0, 0, 0, 0))
        mask_img.putdata([(color_map[i] + (255,) if pixel == 255 else (0, 0, 0, 0)) for pixel in mask.getdata()])
        # Save the mask image to disk with a unique filename
        img_path = os.path.join(save_path,image_name)
        mask_img.save(img_path)
        files_saved.append(image_name)
    return files_saved

def get_uri(data: bytes,scheme: str = "image/png") -> str:
    """Generates a URI (Uniform Resource Identifier) for a given data object and scheme.

    The data is first encoded as base64, and then added to the URI along with the specified scheme.
    
    Works for both RGB and RGBA imagery
    
    Scheme : string of character that specifies the purpose of the uri
    Available schemes for imagery:
    "image/jpeg"
    "image/png"

    Parameters
    ----------
    data : bytes
        The data object to be encoded and added to the URI.
    scheme : str, optional (default="image/png")
        The URI scheme to use for the generated URI. Defaults to "image/png".

    Returns
    -------
    str
        The generated URI, as a string.
    """
    return f"data:{scheme};base64,{encodebytes(data).decode('ascii')}"

def get_overlay_for_image(image_path: str, bounds: Tuple, name: str, file_format: str) -> ImageOverlay:
    """Create an ImageOverlay object for an image file.

    Args:
        image_path (str): The path to the image file.
        bounds (Tuple): The bounding box for the image overlay.
        name (str): The name of the image overlay.
        file_format (str): The format of the image file, either 'png', 'jpg', or 'jpeg'.

    Returns:
        An ImageOverlay object.
    """
    if file_format.lower() not in ['png', 'jpg', 'jpeg']:
        raise ValueError(f"{file_format} is not recognized. Allowed file formats are: png, jpg, and jpeg.")

    if file_format.lower() == 'png':
        file_format='png'
        scheme ="image/png"
    elif file_format.lower() == 'jpg' or file_format.lower() == 'jpeg':
        file_format='jpeg'
        scheme ="image/jpeg"

    # use pillow to open the image
    img_data = Image.open(image_path)
    # convert image to bytes
    img_bytes=convert_image_to_bytes(img_data,file_format)
    # create a uri from bytes
    uri = get_uri(img_bytes,scheme)
    # create image overlay from uri
    return ImageOverlay(url=uri, bounds=bounds, name=name)

def convert_image_to_bytes(image,file_format:str='png'):
    file_format = "PNG" if file_format.lower() == 'png' else "JPEG"
    f = BytesIO()
    image.save(f, file_format)
    # get the bytes from the bytesIO object
    return f.getvalue()
