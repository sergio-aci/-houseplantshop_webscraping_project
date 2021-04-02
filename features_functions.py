"""
Authors: Isaac Misri, Sergio Drajner
Description: This file contains all the functions that are used to extract
the feature options from the url.
"""

import web_scraper_config as CFG
import grequests
import requests
from bs4 import BeautifulSoup
import re
import csv
import json


def get_feature(feature, additional_features_and_urls):
    """
    Given the html script of a particular feature, this function
    extracts the name and the url from the html script
    of that feature
    """
    try:
        additional_features_and_urls. \
            append([feature.attrs['data-handle'],
                    CFG.URL_FIRST_PART + feature.find('a', href=True)['href']
                    + CFG.URL_PAGE_TAG])
    except KeyError:
        pass


def get_features(url):
    """
    Given a url, this function extracts the html script of the features
    by which products can be filtered.
    For each feature's html script, the function then calls
    get_feature() and finally returns a list
    of all available features along with their urls
    """
    additional_features_and_urls = []

    features_soup = make_soup(url)
    features_soup_list = features_soup.find_all('li', class_='filter-item')

    for feature in features_soup_list:
        get_feature(feature, additional_features_and_urls)

    return additional_features_and_urls


def make_soup(url):
    """
    Given a url, this function uses requests to access the html script
    of the url and then uses BeautifulSoup
    to create and return a BeautifulSoup object to be parsed
    """
    try:
        source_code = requests.get(url).text
        return BeautifulSoup(source_code, 'html.parser')
    except Exception:
        print('could not retrieve source code from url')


def get_num_pages(soup):
    """
    Given a soup object, this function will extract and return the
    total number of pages to process.
    If no 'pagination--item' tag exists, an IndexError is raised. The
    error is caught and the value
    of 1 is returned meaning there is only one page to check.
    """
    try:
        return int(soup.find_all('a', class_='pagination--item')
                   [CFG.PAGES_INDICATOR_INDEX].text.strip())
    except IndexError:
        return 1


def find_all_products(soup_mix):
    """
    Given a BeautifulSoup object, this function extracts and returns
    the html script for all products on that page
    """
    product_space = soup_mix.find(
        'ul', class_="productgrid--items products-per-row-4")
    sale_product_info = product_space.find_all(
        'li', class_="productgrid--item imagestyle--natural "
                     "productitem--sale productitem--emphasis "
                     "show-actions--mobile")
    non_sale_product_info = product_space.find_all(
        'li', class_='productgrid--item imagestyle--natural '
                     'productitem--emphasis '
                     'show-actions--mobile')
    return sale_product_info + non_sale_product_info


def process_first_page_product(all_product_info, product_names):
    """
    This function scrapes the first page of a feature and extracts the
    product names. Once the product names
    have been extracted, they are appended to a list corresponding to
    the particular feature
    """
    for product in all_product_info:
        product_name = product.find('h2', class_='productitem--title')
        clean_name = product_name.a.text.strip()
        product_names.append(clean_name)


def process_product(all_product_info, product_names, feature_and_url):
    """
    This function is called if there is more than 1 page for a feature.
    It performs exactly the same task as
    process_first_page_product() but also extracts the current page
    number and returns it
    """
    for product in all_product_info:
        product_name = product.find('h2', class_='productitem--title')
        clean_name = product_name.a.text.strip()
        product_names.append(clean_name)
        current_page = int(re.search('page=(\d)',
                                     feature_and_url[CFG.URL_INDEX]).group(1))
    return current_page


def process_additional_page_products(num_pages, feature_and_url, product_names, current_page):
    """
    This function processes all features that have more than 1 page. It iterates through all the pages of
    a feature and appends product names to a list for a given feature
    """
    for page_num in range(2, num_pages + 1):
        # print(f'Now extracting from Page {page_num} of Feature: '
        #       f'{feature_and_url[CFG.FEATURE_INDEX]} ')
        new_url = feature_and_url[CFG.URL_INDEX] \
            .replace(f'page={current_page}', f'page={page_num}')
        new_page_soup = make_soup(new_url)
        all_product_info = find_all_products(new_page_soup)
        current_page = process_product(all_product_info, product_names,
                                       feature_and_url)


def process_feature(rs, index, unavailable_pages, feature_and_url,
                    feature_dict):
    """
    This function calls various functions to process a feature found
    in the html script.
    It uses other functions to append product names to lists of
    features. Once all the pages of a feature have been scrapped and
    all product names have been added to that feature, the information
    is stored in a dictionary with key = features and value = list of
    products corresponding to that feature.
    """
    product_names = []

    if rs[index] is None:
        print('webpage unavailable')
        unavailable_pages += 1
    else:
        soup = BeautifulSoup(rs[index].text, 'html.parser')
        num_pages = get_num_pages(soup)
        current_page = int(re.search('page=(\d)',
                                     feature_and_url[CFG.URL_INDEX]).group(1))
        # print(f'Now extracting from Page 1 of Feature: '
        #       f'{feature_and_url[CFG.FEATURE_INDEX]}')

        all_product_info = find_all_products(soup)
        process_first_page_product(all_product_info, product_names)

        if num_pages > 1:
            process_additional_page_products(num_pages, feature_and_url,
                                             product_names, current_page)

        feature_and_url.append(product_names)
        feature_dict[feature_and_url[CFG.FEATURE_INDEX]] = product_names
        # print(feature_and_url)
        # print(f'products in {feature_and_url[CFG.FEATURE_INDEX]} feature: '
        #       f'{len(feature_and_url[CFG.PRODUCT_INDEX])}')


def process_features(feature_url_list):
    """
    This function uses grequests to request html scripts of all
    features. After iterating through every feature and all pages of
    each feature, it returns a finalized dictionary with each feature
    and a list of products corresponding to that feature
    """
    rs = (grequests.get(feature_and_url[CFG.URL_INDEX])
          for feature_and_url in feature_url_list)
    rs = grequests.map(rs, size=CFG.BATCH_SIZE)

    unavailable_pages = 0
    feature_dict = {}

    for index, feature_and_url in enumerate(feature_url_list):
        process_feature(rs, index, unavailable_pages, feature_and_url,
                        feature_dict)
    print('*******************************************************')
    print(f'scraper encountered {unavailable_pages} unavailable features pages')
    print('*******************************************************')

    return feature_dict

def get_additional_information():
    """
    This function is the top level function for executing all other
    feature functions. It calls get_features() to extract all features
    from the homepage html script. It then calls process_features()
    to extract all products corresponding to every feature. Once
    completed, it will create a csv file with the features and
    corresponding products
    """
    features_and_urls = get_features(CFG.URL_FIRST_PART
                                     + CFG.URL_SECOND_PART_FIRST_TIME
                                     + CFG.URL_PAGE_TAG)
    features_info = process_features(features_and_urls)
    dict_file = open('features.csv', 'w')
    writer = csv.writer(dict_file)
    for feature, plants in features_info.items():
        # print(feature, plants)
        writer.writerow([feature, plants])
    dict_file.close()


def output_json():
    """
    This function creates a json formated file with all the features on the webshop and the products
    that correspond to that feature.
    """
    features_and_urls = get_features(CFG.URL_FIRST_PART
                                     + CFG.URL_SECOND_PART_FIRST_TIME
                                     + CFG.URL_PAGE_TAG)
    features_info = process_features(features_and_urls)

    with open('features.txt', 'w') as outfile:
        json.dump(features_info, outfile, indent=4)
