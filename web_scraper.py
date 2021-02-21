"""
Authors: Isaac Misri, Sergio Drajner
Description: This script scrapes a web site for the data mining project.
"""

import features_functions as FF
import product_info_functions as PIF


def main():
    """
    This is the main function of the script which will scrape through the webpage and
    return two .csv files
    """
    FF.get_additional_information()
    products_names = []
    products_urls = []
    have_options = []
    products_prices = []
    products_are_sold_out = []
    PIF.process_pages(products_names,
                  products_urls,
                  have_options,
                  products_prices,
                  products_are_sold_out)
    PIF.output_products(products_names, products_prices, products_are_sold_out)


if __name__ == '__main__':
    main()
