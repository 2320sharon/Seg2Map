import os
import re
import random
import string
import glob
import shutil
import json
import math
from datetime import datetime
import logging
from typing import Union, List
import json
import math
import logging
import os, json, shutil
from glob import glob
import concurrent.futures
from datetime import datetime

# Internal dependencies imports
from src.seg2map import exception_handler

from tqdm.auto import tqdm
import requests
import zipfile
from area import area
import geopandas as gpd
import numpy as np
import geojson
import matplotlib
from leafmap import check_file_path
import pandas as pd
from osgeo import gdal


from ipywidgets import ToggleButton
from ipywidgets import HBox
from ipywidgets import VBox
from ipywidgets import Layout
from ipywidgets import HTML


logger = logging.getLogger(__name__)


def group_files(files: List[str], size: int = 2) -> List[List[str]]:
    """
    Groups a list of file paths into sublists of a specified size.

    This function takes a list of file paths and groups them into sublists of a specified size. The default size is 2. The function returns a list of sublists, where each sublist contains up to `size` file paths.

    Parameters:
    - files (List[str]): A list of file paths to be grouped.
    - size (int): The size of each sublist. Defaults to 2.

    Returns:
    - A list of sublists, where each sublist contains up to `size` file paths.
    """
    grouped_files = [files[n : n + size] for n in range(0, len(files), size)]
    return grouped_files


def merge_files(src_files: str, dest_path: str, create_jpg: bool = True) -> str:
    """Merge a list of GeoTIFF files into a single JPEG file.

    Args:
    src_files (List[str]): A list of file paths to be merged.
    dest_path (str): The path to the output JPEG file.

    Returns:
    str: The path to the output JPEG file.
    """
    # Check if path to source exists
    for file in src_files:
        if not os.path.exists(file):
            raise FileNotFoundError(f"{file} not found.")
    try:
        ## create vrt(virtual world format) file
        # Create VRT file
        vrt_options = gdal.BuildVRTOptions(
            resampleAlg="average", srcNodata=0, VRTNodata=0
        )
        # creates a virtual world file using all the tifs and overwrites any pre-existing .vrt
        virtual_dataset = gdal.BuildVRT(dest_path, src_files, options=vrt_options)
        # flushing the cache causes the vrt file to be created
        virtual_dataset.FlushCache()
        # reset the dataset object
        virtual_dataset = None

        # create geotiff (.tiff) from merged vrt file
        tif_path = dest_path.replace(".vrt", ".tif")
        virtual_dataset = gdal.Translate(
            tif_path,
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
            srcDS=dest_path,
        )
        virtual_dataset.FlushCache()
        virtual_dataset = None

        if create_jpg:
            # convert .vrt to .jpg file
            virtual_dataset = gdal.Translate(
                dest_path.replace(".vrt", ".jpg"),
                creationOptions=["WORLDFILE=YES", "QUALITY=100"],
                srcDS=dest_path.replace(".vrt", ".tif"),
            )
            virtual_dataset.FlushCache()
            virtual_dataset = None

        return dest_path
    except Exception as e:
        print(e)
        logger.error(e)
        raise e


def delete_files(pattern, path):
    """
    Deletes all files in the directory tree rooted at `path` that match the given `pattern`.

    Args:
        pattern (str): Regular expression pattern to match against file names.
        path (str): Full path to the root of the directory tree to search for files.

    Returns:
        list: A list of full paths to the files that were deleted.

    Raises:
        ValueError: If the `path` does not exist.

    Example:
        >>> delete_files(r'\.txt$', '/path/to/directory')
        ['/path/to/directory/file1.txt', '/path/to/directory/subdir/file2.txt']
    """
    if not os.path.exists(path):
        raise ValueError(f"Path {path} does not exist")

    deleted_files = []
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if re.match(pattern, filename):
                full_path = os.path.join(dirpath, filename)
                os.remove(full_path)
                deleted_files.append(full_path)

    return deleted_files


# def merge_tifs(src_dir: str, dest_dir: str) -> str:
#     # Check if path to destination directory exists
#     if not os.path.exists(dest_dir):
#         raise FileNotFoundError(f"{dest_dir} not found.")
#     # Check if path to source exists
#     if not os.path.exists(src_dir):
#         raise FileNotFoundError(f"{src_dir} not found.")
#     try:

#         # Create a list of tif files in source directory
#         tif_files = glob(os.path.join(src_dir, "*.tif"))
#         if not tif_files:
#             raise FileNotFoundError(f"No tif files found in {src_dir}.")

#         vrt_path = os.path.join(dest_dir, "merged_multispectral.vrt")
#         logger.info(f"vrt_path: {vrt_path}")

#         ## create vrt(virtual world format) file
#         vrtoptions = gdal.BuildVRTOptions(
#             resampleAlg="average", srcNodata=0, VRTNodata=0
#         )
#         # creates a virtual world file using all the tifs and overwrites any pre-existing .vrt
#         virtual_dataset = gdal.BuildVRT(vrt_path, tif_files, options=vrtoptions)
#         # flushing the cache causes the vrt file to be created
#         virtual_dataset.FlushCache()
#         # reset the dataset object
#         virtual_dataset = None

#         # create geotiff (.tiff) from merged vrt file
#         virtual_dataset = gdal.Translate(
#             vrt_path.replace(".vrt", ".tif"),
#             creationOptions=["COMPRESS=LZW", "TILED=YES"],
#             srcDS=vrt_path,
#         )
#         virtual_dataset.FlushCache()
#         virtual_dataset = None

#         # convert .vrt to .jpg file
#         virtual_dataset = gdal.Translate(
#             vrt_path.replace(".vrt", ".jpg"),
#             creationOptions=["WORLDFILE=YES", "QUALITY=100"],
#             srcDS=vrt_path.replace(".vrt", ".tif"),
#         )
#         virtual_dataset.FlushCache()
#         virtual_dataset = None
#         return vrt_path
#     except Exception as e:
#         print(e)
#         logger.error(e)
#         raise e


def gdal_translate_png_to_tiff(
    files: List[str],
    translateoptions: str = "-of JPEG -co COMPRESS=JPEG -co TFW=YES -co QUALITY=100",
):
    """Convert TIFF files to JPEG files using GDAL.

    Args:
        files (List[str]): List of file paths to TIFF files to be converted.
        translateoptions (str, optional): GDAL options for converting TIFF files to JPEG files. Defaults to "-of JPEG -co COMPRESS=JPEG -co TFW=YES -co QUALITY=100".

    Returns:
        List[str]: List of file paths to the newly created JPEG files.
    """
    new_files = []
    for file in files:
        new_file = file.replace(".png", ".tif")
        if os.path.exists(new_file):
            logger.info(f"File: {new_file} already exists")
            print(f"File: {new_file} already exists")
        else:
            dst = gdal.Translate(new_file, file, options=translateoptions)
            new_files.append(new_file)
            dst = None  # close and save ds
    return new_files


def gdal_translate_jpeg(
    files: List[str],
    translateoptions: str = "-of JPEG -co COMPRESS=JPEG -co TFW=YES -co QUALITY=100",
):
    """Convert TIFF files to JPEG files using GDAL.

    Args:
        files (List[str]): List of file paths to TIFF files to be converted.
        translateoptions (str, optional): GDAL options for converting TIFF files to JPEG files. Defaults to "-of JPEG -co COMPRESS=JPEG -co TFW=YES -co QUALITY=100".

    Returns:
        List[str]: List of file paths to the newly created JPEG files.
    """
    new_files = []
    for f in files:
        jpg_file = f.replace(".tif", ".jpg")
        if os.path.exists(jpg_file):
            print(f"File: {jpg_file} already exists")
        else:
            dst = gdal.Translate(f.replace(".tif", ".jpg"), f, options=translateoptions)
            new_files.append(f.replace(".tif", ".jpg"))
            dst = None  # close and save ds
    return new_files


def rename_files(directory: str, pattern: str, new_name: str, replace_name: str):
    """Rename all files in a directory that match a glob pattern

    Args:
        directory (str): the path to the directory containing the files to be renamed
        pattern (str): the glob pattern to match the files to be renamed
        new_name (str): the new prefix for the renamed files
    """
    # Get a list of files that match the pattern
    files = glob(os.path.join(directory, pattern))
    logger.info(f"Files to rename: {files}")

    for file in files:
        # Get the base name of the file
        base_name = os.path.basename(file)

        # Construct the new file name
        new_file_name = base_name.replace(replace_name, new_name)
        new_file_path = os.path.join(directory, new_file_name)

        # Rename the file
        os.rename(file, new_file_path)


def copy_files(src_files: List[str], dst_dir: str, avoid_names: List[str] = []) -> None:
    """Copy files from a list of source files to a destination directory, while avoiding files with specific names.

    Args:
    src_files (List[str]): A list of file paths to be copied.
    dst_dir (str): The path to the destination directory.
    avoid_names (List[str], optional): A list of substrings to avoid in filenames. Defaults to [].

    Returns:
    None
    """
    logger.info(f"Copying files to {dst_dir}. Files: {src_files}")
    os.makedirs(dst_dir, exist_ok=True)
    for src_file in src_files:
        filename = os.path.basename(src_file)
        if any(name in filename for name in avoid_names):
            continue
        dst_file = os.path.join(dst_dir, filename)
        shutil.copy(src_file, dst_file)


def move_files(src_dir: str, dst_dir: str, delete_src: bool = False) -> None:
    """
    Moves every file in a source directory to a destination directory, and has the option to delete the source directory when finished.

    The function uses the `shutil` library to move the files from the source directory to the destination directory. If the `delete_src` argument is set to `True`, the function will delete the source directory after all the files have been moved.

    Args:
    - src_dir (str): The path of the source directory.
    - dst_dir (str): The path of the destination directory.
    - delete_src (bool, optional): A flag indicating whether to delete the source directory after the files have been moved. Default is `False`.

    Returns:
    - None
    """
    logger.info(f"Moving files from {src_dir} to dst_dir. Delete Source:{delete_src}")
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)
        dst_file = os.path.join(dst_dir, filename)
        shutil.move(src_file, dst_file)
    if delete_src:
        os.rmdir(src_dir)


def get_matching_dirs(dir_path: str, pattern: str = r"^\d{4}$") -> List[str]:
    """
    Returns a list of directories that match the specified pattern.

    The function searches the specified directory and its subdirectories for
    directories that have names that match the specified pattern.

    Args:
    - dir_path (str): The directory to search for matching directories.
    - pattern (str, optional): The pattern to match against the directory names. Default is "^\d{4}$".

    Returns:
    - List[str]: A list of the full paths of the matching directories.
    """
    matching_dirs = []
    for root, dirs, files in os.walk(dir_path):
        folder_name = os.path.basename(root)
        if re.match(pattern, folder_name):
            matching_dirs.append(root)
    return matching_dirs


# def delete_empty_directories(directory):
#     for root, dirs, files in os.walk(directory, topdown=False):
#         for dir in dirs:
#             dir_path = os.path.join(root, dir)
#             try:
#                 os.rmdir(dir_path)
#                 print(f"Deleted empty directory: {dir_path}")
#             except OSError:
#                 # If the directory is not empty, skip it
#                 pass


def remove_zip_files(paths):
    # Create a thread pool with a fixed number of threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit a remove_zip task for each directory
        futures = [executor.submit(remove_zip, path) for path in paths]

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)


def get_subdirs(parent_dir: str):
    # Get a list of all the subdirectories in the parent directory
    subdirectories = []
    for root, dirs, files in os.walk(parent_dir):
        for d in dirs:
            subdirectories.append(os.path.join(root, d))
    return subdirectories


def remove_zip(path) -> None:
    # Get a list of all the zipped files in the directory
    zipped_files = [
        os.path.join(path, f) for f in os.listdir(path) if f.endswith(".zip")
    ]
    # Remove each zip file
    for zipped_file in zipped_files:
        os.remove(zipped_file)


def unzip(path) -> None:
    # Get a list of all the zipped files in the directory
    zipped_files = [
        os.path.join(path, f) for f in os.listdir(path) if f.endswith(".zip")
    ]
    # Unzip each file
    for zipped_file in zipped_files:
        with zipfile.ZipFile(zipped_file, "r") as zip_ref:
            zip_ref.extractall(path)


def unzip_files(paths):
    # Create a thread pool with a fixed number of threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit a unzip task for each directory
        futures = [executor.submit(unzip, path) for path in paths]

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)




def get_yearly_ranges(date_range):
    """
    Returns a list of start and end dates for each year in the specified date range.

    Parameters:
    - date_range (list): A list of two dates in the format ['YYYY-MM-DD', 'YYYY-MM-DD'].

    Returns:
    - A list of tuples, where each tuple contains the start and end date for a single year in the range.
    """
    start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
    end_date = datetime.strptime(date_range[1], '%Y-%m-%d')
    year_ranges = []
    for year in range(start_date.year, end_date.year + 1):
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31)
        if year == start_date.year:
            year_start = start_date
        if year == end_date.year:
            year_end = end_date
        year_ranges.append((year_start, year_end))
    return year_ranges

def unzip_data(parent_dir: str):
    logger.info(f"Parent directory to find zip files: {parent_dir}")
    subdirs = get_subdirs(parent_dir)
    logger.info(f"Subdirectories to unzip: {parent_dir}")
    unzip_files(subdirs)
    remove_zip_files(subdirs)


def create_dir(dir_path: str, raise_error=True) -> str:
    dir_path = os.path.abspath(dir_path)
    if os.path.exists(dir_path):
        if raise_error:
            raise FileExistsError(dir_path)
    else:
        os.makedirs(dir_path)
    return dir_path


def create_directory(file_path: str, name: str) -> str:
    new_directory = os.path.join(file_path, name)
    # If the directory named 'name' does not exist, create it
    if not os.path.exists(new_directory):
        os.makedirs(new_directory)
    return new_directory


def generate_random_string(avoid_list=[]):
    alphanumeric = string.ascii_letters + string.digits
    random_string = "".join(random.choice(alphanumeric) for i in range(6))
    if random_string in avoid_list:
        return generate_random_string(avoid_list)
    return random_string


def merge_tifs(multiband_path: str, roi_path: str) -> str:
    # Check if path to ROI directory exists
    if not os.path.exists(roi_path):
        raise FileNotFoundError(f"{roi_path} not found.")
    # Check if path to multiband exists
    if not os.path.exists(multiband_path):
        raise FileNotFoundError(f"{multiband_path} not found.")
    try:

        # Create a list of tif files in multiband_path
        tif_files = glob(os.path.join(multiband_path, "*.tif"))
        if not tif_files:
            raise FileNotFoundError(f"No tif files found in {multiband_path}.")

        vrt_path = os.path.join(roi_path, "merged_multispectral.vrt")
        logger.info(f"vrt_path: {vrt_path}")

        ## create vrt(virtual world format) file
        vrtoptions = gdal.BuildVRTOptions(
            resampleAlg="average", srcNodata=0, VRTNodata=0
        )
        # creates a virtual world file using all the tifs and overwrites any pre-existing .vrt
        virtual_dataset = gdal.BuildVRT(vrt_path, tif_files, options=vrtoptions)
        # flushing the cache causes the vrt file to be created
        virtual_dataset.FlushCache()
        # reset the dataset object
        virtual_dataset = None

        # create geotiff (.tiff) from merged vrt file
        virtual_dataset = gdal.Translate(
            vrt_path.replace(".vrt", ".tif"),
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
            srcDS=vrt_path,
        )
        virtual_dataset.FlushCache()
        virtual_dataset = None

        # convert .vrt to .jpg file
        virtual_dataset = gdal.Translate(
            vrt_path.replace(".vrt", ".jpg"),
            creationOptions=["WORLDFILE=YES", "QUALITY=100"],
            srcDS=vrt_path.replace(".vrt", ".tif"),
        )
        virtual_dataset.FlushCache()
        virtual_dataset = None
        return vrt_path
    except Exception as e:
        print(e)
        logger.error(e)
        raise e


def delete_empty_dirs(dir_path: str):
    """
    Recursively delete all empty directories within a directory.

    Parameters
    ----------
    dir_path : str
        The path to the directory where the search for empty directories begins.

    Returns
    -------
    None
    """
    subdirs = get_subdirs(dir_path)
    remove_dirs = [subdir for subdir in subdirs if len(os.listdir(subdir)) == 0]
    for remove_dir in remove_dirs:
        os.removedirs(remove_dir)


def create_year_directories(start_year: int, end_year: int, base_path: str) -> None:
    """Create directories for each year in between a given start and end year.

    Args:
        start_year (int): The start year.
        end_year (int): The end year.
        base_path (str): The base path for the directories.

    Returns:
        None
    """
    for year in range(start_year, end_year + 1):
        year_path = os.path.join(base_path, str(year))
        if not os.path.exists(year_path):
            os.makedirs(year_path)


def create_subdirectory(name: str, parent_dir: str = None) -> str:
    """Returns full path to a directory named name created in the parent directory.
    If the parent directory is not given then the data directory is created in the current working directory

    Args:
        parent_dir (str, optional): parent directory to create name directory within. Defaults to None.

    Returns:
        str: full path to a directory named name
    """
    if parent_dir == None:
        parent_dir = os.getcwd()
    new_dir = os.path.join(parent_dir, name)
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
    return new_dir


def create_warning_box(title: str = None, msg: str = None):
    padding = "0px 0px 0px 5px"  # upper, right, bottom, left
    # create title
    if title is None:
        title = "Warning"
    warning_title = HTML(f"<b>⚠️<u>{title}</u></b>")
    # create msg
    if msg is None:
        msg = "Something went wrong..."
    warning_msg = HTML(
        f"____________________________________________________________________________________________\
                   </br>⚠️{msg}"
    )
    # create vertical box to hold title and msg
    warning_content = VBox([warning_title, warning_msg])
    # define a close button
    close_button = ToggleButton(
        value=False,
        tooltip="Close Warning Box",
        icon="times",
        button_style="danger",
        layout=Layout(height="28px", width="28px", padding=padding),
    )

    def close_click(change):
        if change["new"]:
            warning_content.close()
            close_button.close()

    close_button.observe(close_click, "value")
    warning_box = HBox([warning_content, close_button])
    return warning_box


def clear_row(row: HBox):
    """close widgets in row/column and clear all children
    Args:
        row (HBox)(VBox): row or column
    """
    for index in range(len(row.children)):
        row.children[index].close()
    row.children = []


def save_to_geojson_file(out_file: str, geojson: dict, **kwargs) -> None:
    """save_to_geojson_file Saves given geojson to a geojson file at outfile
    Args:
        out_file (str): The output file path
        geojson (dict): geojson dict containing FeatureCollection for all geojson objects in selected_set
    """
    # Save the geojson to a file
    out_file = check_file_path(out_file)
    ext = os.path.splitext(out_file)[1].lower()
    if ext == ".geojson":
        out_geojson = out_file
    else:
        out_geojson = os.path.splitext(out_file)[1] + ".geojson"
    with open(out_geojson, "w") as f:
        json.dump(geojson, f, **kwargs)


def download_url(url: str, save_path: str, filename: str = None, chunk_size: int = 128):
    """Downloads the data from the given url to the save_path location.
    Args:
        url (str): url to data to download
        save_path (str): directory to save data
        chunk_size (int, optional):  Defaults to 128.
    """
    with requests.get(url, stream=True) as r:
        if r.status_code == 404:
            logger.error(f"DownloadError: {save_path}")
            raise exceptions.DownloadError(os.path.basename(save_path))
        # check header to get content length, in bytes
        total_length = int(r.headers.get("Content-Length"))
        with open(save_path, "wb") as fd:
            with tqdm(
                total=total_length,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Downloading {filename}",
                initial=0,
                ascii=True,
            ) as pbar:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    fd.write(chunk)
                    pbar.update(len(chunk))


def is_list_empty(main_list: list) -> bool:
    all_empty = True
    for np_array in main_list:
        if len(np_array) != 0:
            all_empty = False
    return all_empty


def get_center_rectangle(coords: list) -> tuple:
    """returns the center point of rectangle specified by points coords
    Args:
        coords list[tuple(float,float)]: lat,lon coordinates
    Returns:
        tuple[float]: (center x coordinate, center y coordinate)
    """
    x1, y1 = coords[0][0], coords[0][1]
    x2, y2 = coords[2][0], coords[2][1]
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
    return center_x, center_y


def get_epsg_from_geometry(geometry: "shapely.geometry.polygon.Polygon") -> int:
    """Uses geometry of shapely rectangle in crs 4326 to return the most accurate
    utm code as a string of format 'epsg:utm_code'
    example: 'espg:32610'

    Args:
        geometry (shapely.geometry.polygon.Polygon): geometry of a rectangle

    Returns:
        int: most accurate epsg code based on lat lon coordinates of given geometry
    """
    rect_coords = geometry.exterior.coords
    center_x, center_y = get_center_rectangle(rect_coords)
    utm_code = convert_wgs_to_utm(center_x, center_y)
    return int(utm_code)


def convert_wgs_to_utm(lon: float, lat: float) -> str:
    """return most accurate utm epsg-code based on lat and lng
    convert_wgs_to_utm function, see https://stackoverflow.com/a/40140326/4556479
    Args:
        lon (float): longitude
        lat (float): latitude
    Returns:
        str: new espg code
    """
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == "1":
        utm_band = "0" + utm_band
    if lat >= 0:
        epsg_code = "326" + utm_band  # North
        return epsg_code
    epsg_code = "327" + utm_band  # South
    return epsg_code


def get_colors(length: int) -> list:
    # returns a list of color hex codes as long as length
    cmap = matplotlib.pyplot.get_cmap("plasma", length)
    cmap_list = [matplotlib.colors.rgb2hex(i) for i in cmap.colors]
    return cmap_list


def get_area(polygon: dict) -> float:
    "Calculates the area of the geojson polygon using the same method as geojson.io"
    logger.info(f"get_area: {polygon}")
    return round(area(polygon), 3)


def read_json_file(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as input_file:
        data = json.load(input_file)
    return data


def get_ids_with_invalid_area(
    geometry: gpd.GeoDataFrame, max_area: float = 98000000, min_area: float = 0
) -> set:
    if isinstance(geometry, gpd.GeoDataFrame):
        geometry = json.loads(geometry.to_json())
    if isinstance(geometry, dict):
        if "features" in geometry.keys():
            rows_drop = set()
            for i, feature in enumerate(geometry["features"]):
                roi_area = get_area(feature["geometry"])
                if roi_area >= max_area or roi_area <= min_area:
                    rows_drop.add(i)
            return rows_drop
    else:
        raise TypeError("Must be geodataframe")


def find_config_json(search_path: str) -> str:
    """Searches for a `config.json` file in the specified directory

    Args:
        search_path (str): the directory path to search for the `config.json` file

    Returns:
        str: the file path to the `config.json` file

    Raises:
        FileNotFoundError: if a `config.json` file is not found in the specified directory
    """
    logger.info(f"searching directory for config.json: {search_path}")
    config_regex = re.compile(r"config.*\.json", re.IGNORECASE)

    for file in os.listdir(search_path):
        if config_regex.match(file):
            logger.info(f"{file} matched regex")
            file_path = os.path.join(search_path, file)
            return file_path

    raise FileNotFoundError(f"config.json file was not found at {search_path}")


def config_to_file(config: Union[dict, gpd.GeoDataFrame], file_path: str):
    """Saves config to config.json or config_gdf.geojson
    config's type is dict or geodataframe respectively

    Args:
        config (Union[dict, gpd.GeoDataFrame]): data to save to config file
        file_path (str): full path to directory to save config file
    """
    if isinstance(config, dict):
        filename = f"config.json"
        save_path = os.path.abspath(os.path.join(file_path, filename))
        write_to_json(save_path, config)
        logger.info(f"Saved config json: {filename} \nSaved to {save_path}")
    elif isinstance(config, gpd.GeoDataFrame):
        filename = f"config_gdf.geojson"
        save_path = os.path.abspath(os.path.join(file_path, filename))
        logger.info(f"Saving config gdf:{config} \nSaved to {save_path}")
        config.to_file(save_path, driver="GeoJSON")


def create_json_config(input_settings: dict, settings: dict) -> dict:
    """returns config dictionary with the settings, currently selected_roi ids, and
    each of the input_settings specified by roi id.
    sample config:
    {
        'roi_ids': ['17','20']
        'settings':{ 'dates': ['2018-12-01', '2019-03-01'],
                    'sitename':'sitename1'}
        '17':{
            'sat_list': ['L8'],
            'landsat_collection': 'C01',
            'dates': ['2018-12-01', '2019-03-01'],
            'sitename':'roi_17',
            'filepath':'C:\\Home'
        }
        '20':{
            'sat_list': ['L8'],
            'landsat_collection': 'C01',
            'dates': ['2018-12-01', '2019-03-01'],
            'sitename':'roi_20',
            'filepath':'C:\\Home'
        }
    }

    Args:
        input_settings (dict): json style dictionary with roi ids at the keys with input_settings as values
        settings (dict):  json style dictionary containing map settings
    Returns:
        dict: json style dictionary, config
    """
    roi_ids = list(input_settings.keys())
    config = {**input_settings}
    config["roi_ids"] = roi_ids
    config["settings"] = settings
    return config


def create_config_gdf(
    rois: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Returns a new geodataframe with new column "type" that contains feature name.
        feature name is one of the following: "roi"

    Args:
        rois (gpd.GeoDataFrame,): geodataframe of rois

    Returns:
        gpd.GeoDataFrame: new geodataframe with new column "type" that contains feature name.
        feature name is one of the following: "roi"
    """
    # create new column 'type' to indicate object type
    rois["type"] = "roi"
    new_gdf = gpd.GeoDataFrame(rois)
    return new_gdf


def write_to_json(filepath: str, settings: dict):
    """ "Write the  settings dictionary to json file"""
    with open(filepath, "w", encoding="utf-8") as output_file:
        json.dump(settings, output_file)


def read_geojson_file(geojson_file: str) -> dict:
    """Returns the geojson of the selected ROIs from the file specified by geojson_file"""
    with open(geojson_file) as f:
        data = geojson.load(f)
    return data


def read_gpd_file(filename: str) -> gpd.GeoDataFrame:
    """
    Returns geodataframe from geopandas geodataframe file
    """
    if os.path.exists(filename):
        logger.info(f"Opening \n {filename}")
        with open(filename, "r") as f:
            gpd_data = gpd.read_file(f)
    else:
        raise FileNotFoundError
    return gpd_data


def create_roi_settings(
    settings: dict,
    selected_ids: set,
    filepath: str,
) -> dict:
    """returns a dict of settings for each roi with roi id as the key.
    Example:
    "2": {
            "dates": ["2018-12-01", "2019-03-01"],
            "sitename": "roi",
            "roi_name": "ID_2_dates_2010-01-01_to_2010-12-31",
            "filepath": "C:\\CoastSeg\\data",
            "roi_id": "2",
        },
    "3": {
            "dates": ["2018-12-01", "2019-03-01"],
            "sitename": "sitename1",
            "roi_name": "ID_3_dates_2010-01-01_to_2010-12-31"
            "filepath": "C:\\CoastSeg\\data",
            "roi_id": "3",
        },

    Args:
        settings (dict): currently loaded settings for the map
        selected_ids (set): set of selected ROI ids
        filepath (str): full path to data directory
    Returns:
        dict: settings for each roi with roi id as the key
    """

    roi_settings = {}
    sitename = settings["sitename"]
    dates = settings["dates"]
    for roi_id in list(selected_ids):
        roi_name = f"ID_{roi_id}_dates_{dates[0]}_to_{dates[1]}"
        roi_info = {
            "dates": dates,
            "roi_id": roi_id,
            "roi_name": roi_name,
            "sitename": sitename,
            "filepath": filepath,
        }
        roi_settings[roi_id] = roi_info
    return roi_settings


def do_rois_filepaths_exist(roi_settings: dict, roi_ids: list) -> bool:
    """Returns true if all rois have filepaths that exist
    Args:
        roi_settings (dict): settings of all rois on map
        roi_ids (list): ids of rois selected on map
    Returns:
        bool: True if all rois have filepaths that exist
    """
    # by default assume all filepaths exist
    does_filepath_exist = True
    for roi_id in roi_ids:
        filepath = str(roi_settings[roi_id]["filepath"])
        if not os.path.exists(filepath):
            # if filepath does not exist stop checking
            does_filepath_exist = False
            logger.info(f"filepath did not exist{filepath}")
            print("Some ROIs contained filepaths that did not exist")
            break
    logger.info(f"{does_filepath_exist} All rois filepaths exist")
    return does_filepath_exist


def do_rois_dirs_exist(roi_settings: dict, roi_ids: list) -> bool:
    """Returns true if all rois have directories that exist
    Args:
        roi_settings (dict): settings of all rois on map
        roi_ids (list): ids of rois selected on map
    Returns:
        bool: True if all rois have filepaths that exist
    """
    # by default assume all filepaths exist
    does_filepath_exist = True
    for roi_id in roi_ids:
        if "filepath" not in roi_settings[roi_id].keys():
            does_filepath_exist = False
            logger.info(f"roi_path did not exist because no filepath found")
            print("Some ROIs contained directories that did not exist")
            break
        if "sitename" not in roi_settings[roi_id].keys():
            does_filepath_exist = False
            logger.info(f"roi_path did not exist because no sitename found")
            print("Some ROIs contained directories that did not exist")
            break
        filepath = os.path.abspath(roi_settings[roi_id]["filepath"])
        sitename = roi_settings[roi_id]["sitename"]
        roi_name = roi_settings[roi_id]["roi_name"]
        roi_path = os.path.join(filepath, sitename, roi_name)
        if not os.path.exists(roi_path):
            # if filepath does not exist stop checking
            does_filepath_exist = False
            logger.info(f"roi_path did not exist{roi_path}")
            print("Some ROIs contained directories that did not exist")
            break
    logger.info(f"{does_filepath_exist} All rois directories exist")
    return does_filepath_exist


def do_rois_have_sitenames(roi_settings: dict, roi_ids: list) -> bool:
    """Returns true if all rois have "sitename" with non-empty string
    Args:
        roi_settings (dict): settings of all rois on map
        roi_ids (list): ids of rois selected on map
    Returns:
        bool: True if all rois have "sitename" with non-empty string
    """
    # by default assume all sitenames are not empty
    is_sitename_not_empty = True
    for roi_id in roi_ids:
        if roi_settings[roi_id]["sitename"] == "":
            # if sitename is empty means user has not downloaded ROI data
            is_sitename_not_empty = False
            break
    logger.info(f"{is_sitename_not_empty} All rois have non-empty sitenames")
    return is_sitename_not_empty


def were_rois_downloaded(roi_settings: dict, roi_ids: list) -> bool:
    """Returns true if rois were downloaded before. False if they have not
    Uses 'sitename' key for each roi to determine if roi was downloaded.
    And checks if filepath were roi is saved is valid
    If each roi's 'sitename' is not empty string returns true
    Args:
        roi_settings (dict): settings of all rois on map
        roi_ids (list): ids of rois selected on map
    Returns:
        bool: True means rois were downloaded before
    """
    # by default assume rois were downloaded
    is_downloaded = True
    if roi_settings is None:
        # if rois do not have roi_settings this means they were never downloaded
        is_downloaded = False
    elif roi_settings == {}:
        # if rois do not have roi_settings this means they were never downloaded
        is_downloaded = False
    elif roi_settings != {}:
        all_sitenames_exist = do_rois_have_sitenames(roi_settings, roi_ids)
        all_filepaths_exist = do_rois_filepaths_exist(roi_settings, roi_ids)
        all_roi_dirs_exist = do_rois_dirs_exist(roi_settings, roi_ids)
        logger.info(
            f"all_filepaths_exist: {all_filepaths_exist} all_sitenames_exist{all_sitenames_exist}"
        )
        is_downloaded = (
            all_sitenames_exist and all_filepaths_exist and all_roi_dirs_exist
        )
    # print correct message depending on whether ROIs were downloaded
    if is_downloaded:
        logger.info(f"Located previously downloaded ROI data.")
    elif is_downloaded == False:
        print(
            "Did not locate previously downloaded ROI data. To download the imagery for your ROIs click Download Imagery"
        )
        logger.info(
            f"Did not locate previously downloaded ROI data. To download the imagery for your ROIs click Download Imagery"
        )
    return is_downloaded


def get_site_path(settings: dict) -> str:
    """
    Create a subdirectory with the name `settings["sitename"]` within a "data" directory in the current working
    directory to hold all downloads. If the subdirectory already exists, raise an error.

    Args:
    - settings: A dictionary containing the key `"sitename"`, which specifies the name of the subdirectory to be created.

    Returns:
    - The absolute file path of the newly created subdirectory.
    """
    # create data directory in current working directory to hold all downloads if it doesn't already exist
    data_path = create_subdirectory("data")
    # create sitename directory if it doesn't already exist
    site_path = os.path.join(data_path, settings["sitename"])
    # exception_handler.check_path_already_exists(site_path, settings["sitename"])
    if not os.path.exists(site_path):
        os.makedirs(site_path)
    return site_path


def generate_datestring() -> str:
    """Returns a datetime string in the following format %m-%d-%y__%I_%M_%S
    EX: "ID_0__01-31-22_12_19_45"""
    date = datetime.now()
    return date.strftime("%m-%d-%y__%I_%M_%S")


def mk_new_dir(name: str, location: str):
    """Create new folder with name_datetime stamp at location
    Args:
        name (str): name of folder to create
        location (str): full path to location to create folder
    """
    if os.path.exists(location):
        new_folder = location + os.sep + name + "_" + generate_datestring()
        os.mkdir(new_folder)
        return new_folder
    else:
        raise Exception("Location provided does not exist.")


def get_RGB_in_path(current_path: str) -> str:
    """returns full path to RGB directory relative to current path
    or raises an error

    Args:
        current_path (str): full path to directory of images to segment

    Raises:
        Exception: raised if no RGB directory is found or
        RGB directory is empty

    Returns:
        str: full path to RGB directory relative to current path
    """
    rgb_jpgs = glob(current_path + os.sep + "*RGB*")
    logger.info(f"rgb_jpgs: {rgb_jpgs}")
    if rgb_jpgs != []:
        return current_path
    elif rgb_jpgs == []:
        # means current path is not RGB directory
        parent_dir = os.path.dirname(current_path)
        logger.info(f"parent_dir: {parent_dir}")
        dirs = os.listdir(parent_dir)
        logger.info(f"child dirs: {dirs}")
        if "RGB" not in dirs:
            raise Exception(
                "Invalid directory to run model in. Please select RGB directory"
            )
        RGB_path = os.path.join(parent_dir, "RGB")
        logger.info(f"returning path:{RGB_path}")
        return RGB_path


def scale(matrix: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """returns resized matrix with shape(rows,cols)
        for 2d discrete labels
        for resizing 2d integer arrays
    Args:
        im (np.ndarray): 2d matrix to resize
        nR (int): number of rows to resize 2d matrix to
        nC (int): number of columns to resize 2d matrix to

    Returns:
        np.ndarray: resized matrix with shape(rows,cols)
    """
    src_rows = len(matrix)  # source number of rows
    src_cols = len(matrix[0])  # source number of columns
    tmp = [
        [
            matrix[int(src_rows * r / rows)][int(src_cols * c / cols)]
            for c in range(cols)
        ]
        for r in range(rows)
    ]
    return np.array(tmp).reshape((rows, cols))


def rescale_array(dat, mn, mx):
    """
    rescales an input dat between mn and mx
    Code from doodleverse_utils by Daniel Buscombe
    source: https://github.com/Doodleverse/doodleverse_utils
    """
    m = min(dat.flatten())
    M = max(dat.flatten())
    return (mx - mn) * (dat - m) / (M - m) + mn
