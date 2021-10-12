# References 
- Collection 1: https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1?qt-science_support_page_related_con=1#qt-science_support_page_related_con

- Collection 2: https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2?qt-science_support_page_related_con=1#qt-science_support_page_related_con

- Generation Timeline: https://www.usgs.gov/media/images/landsat-collection-2-generation-timeline

# USGS Landsat Collection 2
It was released early 2021 and offers improved processing, geometric accuracy, and radiometric calibration compared to previous Collection 1 products. So the date before or after will only work for recent data. Before that, we will need to use specific dates without certainity or logic to understand-it yet. Maybe theres a timeline dependind on the month and year of the original data!

# Product id
https://prd-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/styles/full_width/public/thumbnails/image/ProductID-only.PNG

- In Level 1 = LC08_L1TP_026027_20200827_20200905_01_T1 | current database
- In level 2 = LC08_L2SP_026027_20200827_20200906_02_T1 | To transform processing level: L2SP(Level-2 Science Product), collection number: 02 and processing date is different, It can be 1 day after, the same day or one day before.

# To test links:
 aws s3 ls s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/026/027/LC08_L2SP_026027_20200827_20200906_02_T1/LC08_L2SP_026027_20200827_20200906_02_T1_SR_B1.TIF/  --request-payer requester

