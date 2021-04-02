"""
Authors: Isaac Misri, Sergio Drajner
Description: This script contains functions that are used to filter,
sort, display and output features and products.
"""
import sys
import web_scraper_config as CFG
import pandas as pd
import db_func as dbf


def filter_features(features_to_filter_df, **kwargs):
    """
    Given the dataframe with features to filter, filter them according
    to the filtering parameters passed at kwargs. Also returns an
    additional dataframe necessary for filtering.
    :param features_to_filter_df: dataframe
    :param kwargs: filtering parameters
    :return: features_df: filtered dataframe
    :param features_and_products_df: dataframe with filtered features and
    their partly filtered products (flattened).
    """
    if kwargs['feature'] is None:
        kwargs['feature'] = ''
    if kwargs['product'] is None:
        kwargs['product'] = ''
    filter = (features_to_filter_df['Feature'].str.contains(kwargs['feature'], case=False, regex=False))
    features_to_filter_df = features_to_filter_df[filter]
    features_copy_df = features_to_filter_df.copy()
    features_copy_df['Products'] = features_copy_df['Products'].apply(
            lambda product_list: [clean_product(product) for product in product_list
                                  if kwargs['product'].upper() in product.upper()])
    features_df = features_copy_df[features_copy_df['Products'].str.len() > 0]
    features_and_products_df = pd.DataFrame(features_df['Products'].to_list(),
                                       index=[features_df['Feature']]).stack()
    features_and_products_df = features_and_products_df.reset_index('Feature')
    features_and_products_df.columns = ['Feature', 'Products']
    return features_df, features_and_products_df


def filter_products(products_to_filter_df, features_and_products_df, **kwargs):
    """
    Given the dataframe with products to filter, filter them according
    to the filtering parameters passed at kwargs.
    :param products_to_filter_df: dataframe
    :param kwargs: filtering parameters
    :return: products_df: filtered dataframe
    """
    if kwargs['product'] is None:
        kwargs['product'] = ''
    if not kwargs['price']:
        price_inferior_limit = 0
        price_superior_limit = sys.maxsize
    else:
        price_inferior_limit = kwargs['price'][CFG.LOWER]
        price_superior_limit = kwargs['price'][CFG.HIGHER]
    if kwargs['sold_out'] is None:
        boolean_to_compare_1 = False
        boolean_to_compare_2 = True
    else:
        boolean_to_compare_1 = boolean_to_compare_2 = kwargs['sold_out']
    if not(kwargs['feature'] is None and not kwargs['break_down']):
        products_to_filter_df = \
            features_and_products_df.merge(products_to_filter_df,
                                           how='inner', left_on='Products',
                                           right_on='Name')
        products_to_filter_df.drop(['Feature', 'Products'], axis=1, inplace=True)
        products_to_filter_df.drop_duplicates(inplace=True)
    filter = (products_to_filter_df['Name']
              .str.contains(kwargs['product'], case=False, regex=False, na=False)) \
    & (products_to_filter_df['Price']
       .between(price_inferior_limit, price_superior_limit)) \
    & (products_to_filter_df['Is Sold Out']
       .between(boolean_to_compare_1, boolean_to_compare_2))
    return products_to_filter_df[filter]


def sort_result(features_df, products_df, **kwargs):
    """
    Given the dataframes with features and products, sort them according
    to the sorting parameters passed at kwargs.
    :param features_df: dataframe
    :param products_df: dataframe
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
            features_df.sort_values(by='Feature', ascending=is_in_ascending_order, inplace=True)
            features_df['Products'] = features_df['Products']\
                .sort_values()\
                .apply(lambda product_list: sorted(product_list, reverse=not is_in_ascending_order))
        else:
            products_df.sort_index(ascending=is_in_ascending_order, inplace=True)
    else:
        products_df.sort_values(by='Price', ascending=is_in_ascending_order, inplace=True)


def clean_product(element):
    """
    Given an element in the list of products of a feature, returns the
    name of a product clean of extra characters.
    :param element: string
    :return: product: string
    """
    product = element.strip('"')
    product = product.replace("\\", "")
    while (product.find("'") == 0 and product.rfind("'") == len(product) - 1) \
            or (product.find('"') == 0 and product.rfind('"') == len(product) - 1):
        product = product[CFG.BEGINNING:CFG.END]
    return product


def output_result(features_df, products_df, **kwargs):
    """
    Displays the results to screen and writes them to a file or database
    according to the parameters received in kwargs.
    :param features_df: dataframe of features
    :param products_df: dataframe of products
    :param kwargs: parameters to use for displaying and writing
    :return:
    """
    pd.set_option("max_rows", None)
    pd.set_option("max_colwidth", CFG.MAX_COLUMN_WIDTH)
    if kwargs['screen']:
        if kwargs['break_down']:
            for row in features_df.itertuples():
                print('Feature:', row[CFG.FEATURE])
                print()
                print('Product/s:')
                for element in row[CFG.PRODUCT]:
                    product = clean_product(element)
                    try:
                        product_info = products_df.loc[product]
                        print(product)
                        print()
                        print(product_info)
                        print()
                        print('-' * CFG.PRODUCT_DIVIDER_LENGTH)
                    except KeyError:
                        continue
                                # ignoring inconsistencies between features and products in case
                                # the scraping process happened in the middle of an web page update.
                print('-' * CFG.FEATURE_DIVIDER_LENGTH)
        else:
            print('Product/s:')
            print(products_df.to_string())

    if kwargs['output'] is not None:
        if kwargs['output'].lower() == 'csv':
            features_df.to_csv('features.csv')
            products_df.to_csv('products.csv')
        if kwargs['output'].lower() == 'json':
            features_df.to_json('features.json', orient="index")
            products_df.to_json('products.json', orient="index")
        elif kwargs['output'].lower() == 'db':
            dbf.fill_products_df(products_df)
            dbf.fill_features_df(features_df)
