"""
Authors: Isaac Misri, Sergio Drajner
Description: This script contains all the functions that are used to extract
all product information for each product listed.
"""
import time
import pandas as pd
import web_scraper_config as CFG
import output_processing as op
import requests
from bs4 import BeautifulSoup
import logging


def process_input_file(products_df, features_and_products_df, **kwargs):
    """
    Gets the file products.csv that was previously created as an input.
    Therefore, no scraping is performed. Then filters the products
    according to the received parameters.
    :param products_df: dataframe
    :param features_and_products_df: dataframe with filtered features and
    their partly filtered products (flattened).
    :param kwargs: parameters to be used for filtering
    :return: products_df: dataframe
    """
    products_to_filter_df = pd.read_csv('products.csv')
    products_to_filter_df.fillna("", inplace=True)
    products_to_filter_df = op.filter_products(products_to_filter_df,
                                               features_and_products_df,
                                               **kwargs)
    products_df = products_df.append(products_to_filter_df)
    return products_df


def process_option(option_info, filter_product_name, options_types,
                   products_to_filter_df):
    """
    Processes the option of a product in the web site, and updates the
    dataframe that contains the products to filter with the product and
    the option's name, type, price and if it is sold out.
    :param option_info: raw information about the option of a product
    :param filter_product_name: string - names of the product with
    options to be updated
    :param options_types: string - types of the options of the product to
    be updated
    :param products_to_filter_df: dataframe of the products to filter
    :return: products_to_filter_df: updated dataframe
    """
    if option_info.find('sold_out') == CFG.NOT_FOUND:
        option_price = float(option_info[option_info.find(CFG.SEPARATOR)
                        + len(CFG.SEPARATOR + CFG.CURRENCY_SIGN):])
        option_is_sold_out = False
    else:
        option_price = float(CFG.NO_PRICE)
        option_is_sold_out = True

    products_to_filter_df = products_to_filter_df.\
        append([{'Name': filter_product_name,
                 'Type': options_types,
                 'Option': option_info[:option_info.find(CFG.SEPARATOR)],
                 'Price': option_price,
                 'Is Sold Out': option_is_sold_out}], ignore_index=True)
    return products_to_filter_df


def get_options_types(options):
    """
    :param options: raw information about the options of a product
    :return: a list of types of options of a product
    """
    options_types_raw = [option_type_raw.get_text()
                         for option_type_raw in options.select(".option-name")]
    return CFG.ANOTHER_SEPARATOR.join([option_type_raw[:option_type_raw.find(CFG.COLON)]
    if option_type_raw.find(CFG.COLON) != CFG.NOT_FOUND else option_type_raw
            for option_type_raw in options_types_raw])


def process_options(filter_product_name, filter_product_url, products_to_filter_df,
                    **kwargs):
    """
    Updates the products_to_filter dataframe by adding the options
    available to the products.
    :param filter_product_name: name of the product to be updated
    :param filter_product_url: url of the product to find its options
    :param products_to_filter_df: dataframe to be updated with
    products and their options
    :return: updated products_to_filter_df: dataframe
    """
    url = CFG.URL_FIRST_PART + filter_product_url
    logging.info(f'Processing product page {url} (with options)')
    attempts = CFG.ATTEMPTS if kwargs['iterations'] is None else kwargs['iterations']
    wait_time = CFG.WAIT_TIME if kwargs['wait_time'] is None else kwargs['wait_time']
    page_is_ok = False
    while attempts > 0:
        web_page = requests.get(url)
        if web_page.status_code == requests.codes.ok:
            page_is_ok = True
            soup = BeautifulSoup(web_page.content, 'html.parser')
            options = soup.find(id="shopify-section-static-product")
            options_types = get_options_types(options)
            options_info = [option_info.get_text()
                                .strip(CFG.CHARACTERS_TO_STRIP).split(CFG.NEW_LINE)
                            for option_info in options.select("select", name="id")]
            for index in range(CFG.FIRST, len(options_info[CFG.FIRST]), CFG.IGNORE):
                option_info = options_info[CFG.FIRST][index].strip()
                products_to_filter_df = \
                    process_option(option_info, filter_product_name, options_types,
                                   products_to_filter_df)
            break

        else:
            attempts -= 1
            if attempts > 0:
                logging.info(f"\tAttempting {attempts} more time"
                             f"{'s' if attempts > 1 else ''}"
                             f" in {wait_time} second"
                             f"{'s' if wait_time != 1 else ''}"
                             )
                time.sleep(wait_time)
            else:
                logging.error(f"Could not download product page {url}. ")
    if not page_is_ok:
        logging.error(f'Product {filter_product_name} disregarded')
    return products_to_filter_df


def process_products(products, products_df, features_and_products_df, **kwargs):
    """
    Updates the products_df dataframe with all the products of a page
    :param products: bs4 object - raw information of products of a page
    to be used as input
    :param products_df: dataframe of products to be updated
    :param features_and_products_df: dataframe with filtered features and
    their partly filtered products (flattened).
    :param kwargs: parameters to be used for filtering
    :return: updated dataframe products_df
    """
    filter_products_names = [name.get_text().strip(CFG.CHARACTERS_TO_STRIP)
                       for name in products.select(".productitem--title")]
    filter_products_urls = [product_url["href"]
                      for product_url in products.select(".productitem--title a")]
    filter_products_prices_or_options_raw = [price_raw.get_text()
                                          .strip(CFG.CHARACTERS_TO_STRIP)
                                      for position, price_raw in
                                      enumerate(products.select(".price--main"))
                                      if position % 2 == 0]  # remove duplicates
    filter_have_options = [False
                     if price_raw.find(CFG.HAS_OPTIONS) == CFG.NOT_FOUND
                     else True
                     for price_raw in filter_products_prices_or_options_raw]
    filter_products_prices = [float(price_raw[price_raw.rfind(CFG.CURRENCY_SIGN) + 1::])
                        for price_raw in filter_products_prices_or_options_raw]
    filter_products_items = [product_item.get_text()
                      for product_item in products.select(".productitem")]
    filter_products_are_sold_out = [False
                              if check_if_sold_out.find('Sold out') == CFG.NOT_FOUND
                              else True
                              for check_if_sold_out in filter_products_items]
    products_to_filter_df = \
        pd.DataFrame(data={'Name': filter_products_names,
                           'Price': filter_products_prices,
                           'Is Sold Out': filter_products_are_sold_out},
                     columns=['Name', 'Type', 'Option', 'Price', 'Is Sold Out'])
    products_to_filter_df.drop(products_to_filter_df[filter_have_options].index, inplace=True)

    for product in range(len(filter_have_options)):
        if filter_have_options[product]:
            products_to_filter_df = process_options(filter_products_names[product],
                                                    filter_products_urls[product],
                                                    products_to_filter_df,
                                                    **kwargs)
    products_to_filter_df = op.filter_products(products_to_filter_df,
                                               features_and_products_df,
                                               **kwargs)
    products_df = products_df.append(products_to_filter_df, ignore_index=True)
    products_df.fillna("", inplace=True)
    return products_df


def get_next_url_second_part(products):
    """
    :param products: bs4 object - raw information to extract the second part
    of the url of the next page
    :return url_second_part: string - second part of the url of the next page
    """
    url_second_part = None
    next_pages_section = products.select("a.pagination--item")
    pages = [page.get_text() for page in next_pages_section]
    if pages[CFG.LAST].strip() == 'Next':
        url_second_part = [page["href"]
                           for page in next_pages_section][CFG.LAST]
    return url_second_part


def process_pages(products_df, features_and_products_df, **kwargs):
    """
    Processes the pages of the web site to scrape information, returns
    the information scraped in a dataframe
    :param products_df: dataframe products to scrape
    :param kwargs: parameters to be used for filtering
    :return: updated products_df: dataframe
    """
    url_second_part = CFG.URL_SECOND_PART_FIRST_TIME
    attempts = CFG.ATTEMPTS if kwargs['iterations'] is None else kwargs['iterations']
    wait_time = CFG.WAIT_TIME if kwargs['wait_time'] is None else kwargs['wait_time']
    while True and attempts > 0:
        url = CFG.URL_FIRST_PART + url_second_part
        logging.info(f'Processing page {url}')
        web_page = requests.get(url)
        if web_page.status_code == requests.codes.ok:
            soup = BeautifulSoup(web_page.content, 'html.parser')
            products = soup.find(id="shopify-section-static-collection")
            products_df = process_products(products, products_df,
                                           features_and_products_df, **kwargs)
            url_second_part = get_next_url_second_part(products)
            if url_second_part is None:
                break

            else:
                attempts = CFG.ATTEMPTS if kwargs['iterations'] is None else kwargs['iterations']
                wait_time = CFG.WAIT_TIME if kwargs['wait_time'] is None else kwargs['wait_time']
        else:
            attempts -= 1
            if attempts > 0:
                logging.info(f"\tAttempting {attempts} more time{'s' if attempts > 1 else ''}"
                             f" in {wait_time} second"
                             f"{'s' if wait_time != 1 else ''}")
                time.sleep(wait_time)
            else:
                logging.error(f"Could not download page {url}. ")
    return products_df
