import os
import numpy as np
import skimage
from skimage.segmentation import quickshift
from skimage import exposure
import rasterio.drivers
from rasterio.mask import mask
from rasterio.features import shapes
from rasterio.plot import show, adjust_band, show_hist, plotting_extent, reshape_as_image, reshape_as_raster
import shapely
from shapely.geometry import shape, GeometryCollection, Point, mapping
from shapely import speedups
speedups.disable()
from shapely.geometry.polygon import Polygon
import fiona
from fiona import collection
from fiona.crs import from_epsg
import cv2
import matplotlib.pyplot as plt

#function to detect weeds in multi-band raster

#parameters:
        #image: str- Path for a 5-band raster with bands B,G,R,RE,NIR
        #target_layer: str- NDVI or NDRI layer to be computed out of 5-band raster. User can choose either of the values
        #target_layer_thresholD: int- Value of the target layer to be used to define weeds
        #seg_obj_area_threshold: int- Area of the contour object segemented to be used to define weeds
        #ROIshapefile- A boolean value (True when clipping is required with shapefile or False otherwise)
#returns:
        #empty_arr: array- Array over which segmented contours would be drawn over
        #bt: dict- Transformation factor of the rastor
        #crs: dict- Cooridnate reference system of the rastor
        #b: array- Blue band of the raster
        #g: array- Green band of the raster
        #r: array- Red band of the raster
        #target: str- NDVI or NDRI depending upon what was choosen by the user
        #cont_selected: list - A list of contours that passed the threshold. In other words, these contours are weed objects. 
        
def detect_weeds( image, target_layer,  target_layer_threshold, seg_obj_area_threshold,  ROIshapefile=None):

    ## Opening raster from the local directory
    raster=rasterio.open(os.path.join(os.getcwd(), image))
    print("raster loaded")

    ## Assigning variables to transform and crs factors
    bt=raster.transform
    crs=raster.crs

    ## Croping the area using the shapefile for the area of interest if needed. This code runs only when ROIshapefile arg set in function above.
    if ROIshapefile:
        with fiona.open(os.path.join(os.getcwd(), ROIshapefile), "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]
        rast, bt = rasterio.mask.mask(raster, shapes=shapes, crop=True)
        print("area clipped")

    ## Reading the whole raster when cropping is not required
    if not ROIshapefile:
        rast1=raster.read()
    else:
        rast1=rast

    ## Reading individual bands from the raster we loaded earlier
    b, g, r, re, nir = rast1[0, :, :], rast1[1, :, :], rast1[2, :, :], rast1[3, :, :], rast1[4, :, :]
        
    ## Computing ndri as this index is found to provide meaningful info for this project. You can try other indices and features
    if target_layer=="NDRE":
        target= (nir-re)/ (nir + re)
    if target_layer == "NDVI":
        target = (nir - r) / (nir + r)
        
   ## NDRI computed above may not be tuned. Stretching the histogram to add contrast in ndri
    target=adjust_band(target)
    target=target.astype("double")
    p2 = np.percentile(target, 2)
    p98 = np.percentile(target, 98)
    target = exposure.rescale_intensity(target, in_range=(p2, p98))

    print("starting segmentation process..........")
    segments = quickshift(target, kernel_size=7, max_dist=7, ratio=0.8, convert2lab=False)
    print("segmentation completed")

    ## Extracting contours from the segmented objects to be feeded into cordinate extract function
    print("preparing to draw segments in the imagery")

    ### creating an empty list to store features for each contours
    target_medianlist = []
    arealist = []

    ### creating an empty array to draw all the contours
    empty_arr = np.zeros(segments.shape)

    ### Iterating over each segments generated earlier and drawing segments on empty_arr when met criteria
    cont_selected=[]
    for (i, segVal) in enumerate(np.unique(segments)):
        mask = np.zeros(segments.shape, dtype="uint8")
        mask[segments == i] = 1
        cont, hier = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cont:
            for j in range(len(cont)):
                mask_draw = np.bool_(mask)

                #### extracting median values from ndri layer for the given contour
                target_median = np.median(target[mask_draw == True])
                target_medianlist.append(target_median)

                #### extracting area value for the given contour
                area = cv2.contourArea(cont[j])
                arealist.append(area)
                
                #### drawing a dot over the empty array as the centroid of the contour when conditions are met
                if target_median > target_layer_threshold and area > seg_obj_area_threshold:
                    M = cv2.moments(cont[j])
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    cv2.circle(empty_arr, (cX, cY), 3, 255, -1)
                    cont_selected.append(cont[j])
    print("drawing completed")

    return empty_arr, bt, crs, b,g,r, target, cont_selected 


#function to generate shapefiles for the segments drawn in the empty array
#parameters:    
            #results: obj- A python object containing output of 'detect-weed' function
            #outputfilename: str- Path where shapefile should be exported and saved
#returns:   #Saves shapefile in the path specified    

def export_shapefile(results, outputfilename):
    array, bt, crs, b,g,r, target, cont=results
    
    ## Converting contours that were drawn above in the emptyarray to shapes
    geometries = rasterio.features.shapes(array.astype("uint8"), transform=bt)
    
    ## Storing polygon coordinates 
    polygon_bounds = [geom[0]['coordinates'] for geom in geometries if "Polygon" in geom[0]["type"]]
    
    ## Finding centroid of the polygon shape derived from contour and exporting to shapefile
    schema = {'geometry': 'Point', 'properties': {'name': 'str'}}
    with collection(os.path.join(os.getcwd(), outputfilename), "w", "ESRI Shapefile", schema, crs=crs) as output:
        ids = 0
        for bounds in polygon_bounds:
            for bound in bounds:
                point = shapely.geometry.Polygon(bound).centroid
                output.write({"properties": {"name": str(ids)}, "geometry": mapping(point)})
                ids += 1
        print("coordinates exported and shapefile saved in directory")

#function to visualize shapefiles over various layers
#parameters:
        #results: A python object containing output of 'detect-weed' function
        #plot_over_rgb: boolean- True if user wants to plot results over original rgb layer
        #plot_over_target_layer: boolean -True if user wants to plot results over target layer
#returns: 
        #matplotlib plot that shows detected weeds overlaid on user-specified base layer
        
def plot_results(results, plot_over_rgb=False, plot_over_targt_layer=False):
    cont=results[7]
    b,g,r = results[3], results[4], results[5]
    target =results[6]
    if plot_over_rgb:
      layer= np.stack((r,g,b), axis=2)
      p2 = np.percentile(layer, 4)
      p98 = np.percentile(layer, 99)
      layer = exposure.rescale_intensity(layer, in_range=(p2, p98))
      cv2.drawContours(layer, cont, -1, color=(0, 255, 0), thickness=2)
    elif plot_over_targt_layer:
      layer=target
      cv2.drawContours(layer, cont, -1, color=(0, 55, 0), thickness=2)
    plt.imshow(layer)
    plt.show()







