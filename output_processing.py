"""
Authors: Isaac Misri, Sergio Drajner
Description: This script contains functions that are used to filter,
sort, display and output features and products.
"""

import pandas as pd
import web_scraper_config as CFG


def sort_result(features, products, **kwargs):
    """
    Given the dataframes with features and products, sort them according
    to the sorting parameters passed at kwargs.
    :param features: instance of Feature (info) object
    :param products: instance of Product (info) object
    :param kwargs: sorting parameters
    :return: features_df: sorted dataframe
    :return: products_df: sorted dataframe
    """
    try:
        is_in_ascending_order = True if kwargs['sort'][CFG.ORDER].lower() == 'a' else False
    except IndexError:
        is_in_ascending_order = True
    if kwargs['sort'][CFG.BY].lower() == 'n':
        if kwargs['break_down']:
            features.sort_features(is_in_ascending_order)
        else:
            products.sort_products('index', is_in_ascending_order)
    else:
        products.sort_products('value', is_in_ascending_order)


def output_result(features, products, **kwargs):
    """
    Displays the results to screen and writes them to a file or database
    according to the parameters received in kwargs.
    :param features: instance of Feature (info) object
    :param products: instance of Product (info) object
    :param kwargs: parameters to use for displaying and writing
    :return:
    """
    pd.set_option("max_rows", None)
    pd.set_option("max_colwidth", CFG.MAX_COLUMN_WIDTH)
    if kwargs['verbose']:
        if kwargs['break_down']:
            features.display_features(products)
        else:
            products.display_products()

    if kwargs['output'] is not None:

        if kwargs['output'].lower() == 'db':
            products.fill_products_df()
            features.fill_features_df()
        else:
            features.output_features(**kwargs)
            products.output_products(**kwargs)
