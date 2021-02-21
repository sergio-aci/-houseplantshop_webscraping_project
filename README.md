# House Plant Shop Webscraping Project
February, 2021 (v1.0)

This webscraper is currently being developed by Sergio Drajner and
Isaac Misri as part of the ITC Data Science Fellows Program 

### Description
Plants and plant products are sold in many different varieties. Even
with filtering capabilities provided by web shops, often times it
can be difficult to sort through all products in an organized manner with
customized filters. The webscraper being developed is meant to extract 
all relevant data about products and plants sold by House Plant Shop,
a large houseplant webshop located at 
https://houseplantshop.com/collections/all-products

![](.README_images/houseplants.png)


### Setup
The webscraper is being developed using python and several packages
which can be found in the requirements.txt file. To run the webscraper,
simply:
1. Download python or ensure that you have python installed
2. Open the terminal or command line interface
3. Go to the directory where the webscraper project is saved 
4. Use the package manager pip to install packages using 
requirements.txt
    ```console
    pip install -r requirements.txt
    ```
5. Run the webscraper using the terminal or command line interface
by opening the web_scraper.py file
    ```console
    python3 web_scraper.py
    ```


### Usage
Running web_scraper.py will produce two .csv files. 
1. The features.csv file contains a list of product features along with 
the products that contain or correspond to each feature. Some features 
include air purifier, pet friendly, genus/family of plant etc... 
Along with each of these features, a list of products that fall into 
these categories is generated.

2. The products.csv file contains a list of the name, price, options and
availability of all the products being sold on the webpage. 


### Problems encountered
While testing the program, few issues were encountered.
Occasionally when attempting to request the html code for the 
product features, a None response was returned when using grequests. 
The program was modified to continue running even when encountering this 
issue. If for whatever reason, the html code of a particular features page 
cannot be accessed, the user will be notified and the code will 
continue running without scraping through the inaccessible data.

Another similar issue was encountered when trying to access the html
code of each product. If the first request is unsuccessful,
the program will attempt to request the html code two more times. If
these requests are unsuccessful, the program will exit and only the
data extracted until the point will be returned.  