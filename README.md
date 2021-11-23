This package can be used to detect weed escapes in fallow lands and acquire the GPS coordinates for those detected weeds. User can clip the imagery using shapefiles for their ROI. Users can also choose to view the results as well.

This package utilizes advanced computer vision technqiues such as object segmentation and countour processing for segmenting the weed boundary in the digital images.

**Requirements**

The package currently supports only five-band multispectral imagery.

**Limitations:**

Only multispectral imagery (5 bands) is supported at this time. In addition, only NDVI & NDRE are avaiable for user to choose for the layers.

**How to use:**

**step1** ```Goto your desired google drive directory and create a new google colaboratory file```

**step2** Open the collab file and mount your google drive by typing 

```from google.colab import drive```

```drive.mount("/content/gdrive")```

**step3** Type the following command after mounting the file ```git clone https://github.com/BishwaBS/WEDIF.git ```

**step4** Change the working directory to the clone directory by typing ```cd "WEDIF" ```

**step5** Type the following

```!pip install -r requirements.txt```

```import os``` 

```import wedif```

**Start using the package**

**step 1**

**detect the weeds and store in a variable**

```detect_weeds( image, num_bands, target_layer,  target_layer_threshold, seg_obj_area_threshold,  ROIshapefile=None)```
e.g. ```results=wedif.detect_weeds("path/to/imagery", 5,  "NDVI", 0.88, 100, "path/to/shapefile_for_ROI")```

You can choose either NDVI or NDRE depending on your use case. If you have a shapefile for your ROI, you can use as shown above. If you don't need to clip the area, you don't have to provide any value to this argument.

target_layer_threshold: Any objects with values less than target_layer_threshold value will be ignore or removed.

seg_obj_threshold: Any objects with area less than seg_obj_threshold value will be ignore or removed.

0.88 & 100 are the arbitrary threshold I used for example. You may want to test the script with different values and visualize the results to evaluate (shown below).

**step 2**

**visulaize the results**

```wedif.plot_results(results, plot_over_rgb=False, plot_over_targt_layer=False)```
e.g. ```wedif.plot_results(results, True, False)```
This script will overlay the detected weed boundaries over the layer that you specify. Here, in the example above, RGB layer was chosen for the base layer for results overlay.

**step 3**

**export the GPS coordinates**
Once you are satisfied with the detection results after a few rounds of trial and error with the values, you can export the coordinates

```wedif.export_shapefile(results, outputfilename)```
e.g. ```wedif.export_shapefile(results, "path/to/outputfilename.shp")

Yay!! you just detected weeds and exported the GPS coordinates without proprietary softwares. Enjoy the package!
