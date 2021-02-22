"""
Authors: Isaac Misri, Sergio Drajner
Description: This script scrapes a web site for the data mining project.
"""

import features_functions as ff
import product_info_functions as pif


def main():
    """
    This is the main function of the script which will scrape through the webpage and
    return two .csv files
    """
    ff.get_additional_information()
    products_names = []
    products_urls = []
    have_options = []
    products_prices = []
    products_are_sold_out = []
    pif.process_pages(products_names,
                  products_urls,
                  have_options,
                  products_prices,
                  products_are_sold_out)
    pif.output_products(products_names, products_prices, products_are_sold_out)


if __name__ == '__main__':
    main()
