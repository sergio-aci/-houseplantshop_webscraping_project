"""
Authors: Isaac Misri, Sergio Drajner
Description: This file contains all the functions that are used to extract
the feature options from the url.
"""

import re
import csv
import json
import logging
from bs4 import BeautifulSoup
import requests
import grequests
import pandas as pd
import pymysql.cursors
import web_scraper_config as CFG


class Features:
    """
    This is the class related to the information of Features.
    """
    def __init__(self, **kwargs):
        """
        Contructor for Features.
        :param kwargs:
        """
        self.features_df, self.features_and_products_df = \
            self.process_features_and_products(**kwargs)

    def process_features_and_products(self, **kwargs):
        """
        Gets the features from a features.csv created in the features_fiction script.
        Then, filters the features according to the parameters received.
        :param kwargs: parameters received from the CLI
        :return: features_df: dataframe
        """
        if kwargs['scrape']:
            Features.get_information()
        features_to_filter_df = pd.read_csv('features.csv', names=['Feature', 'Products'])
        features_to_filter_df['Products'] = features_to_filter_df['Products'] \
            .apply(lambda x: x[CFG.BEGINNING:CFG.END].split(', '))
        features_to_filter_df.fillna("", inplace=True)
        return self.filter_features(features_to_filter_df, **kwargs)

    def filter_features(self, features_to_filter_df, **kwargs):
        """
        Given the dataframe with features to filter, filter them according
        to the filtering parameters passed at kwargs. Also returns an
        additional dataframe necessary for filtering.
        :param features_to_filter_df: dataframe
        :param kwargs: filtering parameters
        :return: features_df: filtered dataframe
        :return features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
        """
        if kwargs['feature'] is None:
            kwargs['feature'] = ''
        if kwargs['product'] is None:
            kwargs['product'] = ''
        feature_filter = (features_to_filter_df['Feature'].str.contains(kwargs['feature'],
                                                                        case=False,
                                                                        regex=False))
        features_to_filter_df = features_to_filter_df[feature_filter]
        features_copy_df = features_to_filter_df.copy()
        features_copy_df['Products'] = features_copy_df['Products'].apply(
                lambda product_list: [Features.clean_product(product) for product in product_list
                                      if kwargs['product'].upper() in product.upper()])
        self.features_df = features_copy_df[features_copy_df['Products'].str.len() > 0]
        self.features_and_products_df = \
            pd.DataFrame(self.features_df['Products'].to_list(),
                         index=[self.features_df['Feature']]).stack()
        self.features_and_products_df = self.features_and_products_df.reset_index('Feature')
        self.features_and_products_df.columns = ['Feature', 'Products']
        return self.features_df, self.features_and_products_df

    @staticmethod
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

    def sort_features(self, is_in_ascending_order):
        """
        Sorts the features and its related products according to the desired order.
        :param is_in_ascending_order: order features and products are to be sorted
        :return:
        """
        self.features_df.sort_values(by='Feature', ascending=is_in_ascending_order, inplace=True)
        self.features_df['Products'] = self.features_df['Products'] \
            .sort_values() \
            .apply(lambda product_list: sorted(product_list, reverse=not is_in_ascending_order))

    def display_features(self, products):
        """
        Displays the features and its related products.
        :param products: Products object
        :return:
        """
        for row in self.features_df.itertuples():
            print('Feature:', row[CFG.FEATURE])
            print()
            print('Product/s:')
            for element in row[CFG.PRODUCT]:
                product = Features.clean_product(element)
                try:
                    product_info = products.get_product_info(product)
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

    def fill_features_df(self):
        """
        This function takes a dataframe of features and inserts all the data into the features
        and features_prod_join tables in a pre-existing plant_db SQL database.
        The tables are first refreshed before values are updated. All user information to connect
        to the database can be modified in the web_scraper_config.py file.
        """
        connection = pymysql.connect(host=CFG.SQL_HOST,
                                     user=CFG.SQL_USER,
                                     password=CFG.SQL_PASS,
                                     db=CFG.SQL_DB,
                                     charset=CFG.SQL_CHARSET,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )

        try:
            with connection.cursor() as cursor:
                sql_command_delete_general = """DELETE FROM features"""
                cursor.execute(sql_command_delete_general)
            connection.commit()
        except Exception:
            pass

        try:
            with connection.cursor() as cursor:
                sql_command_delete_all = """ DELETE FROM features_prod_join"""
                cursor.execute(sql_command_delete_all)
            connection.commit()
        except Exception:
            pass

        feature_id = 0

        df = self.features_df.iloc[1:]
        for row in df.itertuples():
            try:
                with connection.cursor() as cursor:
                    sql_command_general = """ INSERT INTO features VALUES (%s, %s)"""
                    cursor.execute(sql_command_general, (feature_id, row[CFG.FEATURE]))
                connection.commit()
            except Exception:
                pass

            for product in row[CFG.PRODUCT]:
                try:
                    with connection.cursor() as cursor:
                        sql_command_general = """ INSERT INTO features_prod_join VALUES (%s, %s)"""
                        cursor.execute(sql_command_general, (feature_id, product))
                    connection.commit()
                except Exception:
                    pass

            feature_id += 1

        connection.close()

    def output_features(self, **kwargs):
        """
        Outputs the features per the attached parameters.
        :param kwargs: parameters to be used for outputting
        :return:
        """
        if kwargs['output'].lower() == 'csv':
            self.features_df.to_csv('features.csv')
        elif kwargs['output'].lower() == 'json':
            self.features_df.to_json('features.json', orient="index")

    @staticmethod
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

    @staticmethod
    def get_features(url):
        """
        Given a url, this function extracts the html script of the features
        by which products can be filtered.
        For each feature's html script, the function then calls
        get_feature() and finally returns a list
        of all available features along with their urls
        """
        additional_features_and_urls = []

        features_soup = Features.make_soup(url)
        features_soup_list = features_soup.find_all('li', class_='filter-item')

        for feature in features_soup_list:
            Features.get_feature(feature, additional_features_and_urls)

        return additional_features_and_urls

    @staticmethod
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
            logging.error('could not retrieve source code from url')

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def process_first_page_product(all_product_info, product_names):
        """
        This function scrapes the first page of a feature and extracts the
        product names. Once the product names
        have been extracted, they are appended to a list corresponding to
        the particular feature
        """
        for product in all_product_info:
            # product_name = product.find('h2', class_='productitem--title')
            product_name = product.find('div', class_='productitem--info')
            # print(product_name.find('h2').a.text.strip())
            # clean_name = product_name.a.text.strip()
            clean_name = product_name.find('h2').a.text.strip()
            product_names.append(clean_name)

    @staticmethod
    def process_product(all_product_info, product_names, feature_and_url):
        """
        This function is called if there is more than 1 page for a feature.
        It performs exactly the same task as
        process_first_page_product() but also extracts the current page
        number and returns it
        """
        for product in all_product_info:
            # product_name = product.find('h2', class_='productitem--title')
            # clean_name = product_name.a.text.strip()
            product_name = product.find('div', class_='productitem--info')
            clean_name = product_name.find('h2').a.text.strip()
            product_names.append(clean_name)
            current_page = int(re.search('page=(\d)',
                                         feature_and_url[CFG.URL_INDEX]).group(1))
        return current_page

    @staticmethod
    def process_additional_page_products(num_pages, feature_and_url, product_names, current_page):
        """
        This function processes all features that have more than 1 page. It iterates
        through all the pages of a feature and appends product names to a list for a given feature
        """
        for page_num in range(2, num_pages + 1):
            # print(f'Now extracting from Page {page_num} of Feature: '
            #       f'{feature_and_url[CFG.FEATURE_INDEX]} ')
            logging.info(f'Now extracting from Page {page_num} of '
                         f'Feature:{feature_and_url[CFG.FEATURE_INDEX]}')
            new_url = feature_and_url[CFG.URL_INDEX] \
                .replace(f'page={current_page}', f'page={page_num}')
            new_page_soup = Features.make_soup(new_url)
            all_product_info = Features.find_all_products(new_page_soup)
            current_page = Features.process_product(all_product_info, product_names,
                                                    feature_and_url)

    @staticmethod
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
            logging.error('webpage unavailable')
            unavailable_pages += 1
        else:
            soup = BeautifulSoup(rs[index].text, 'html.parser')
            num_pages = Features.get_num_pages(soup)
            current_page = int(re.search('page=(\d)',
                                         feature_and_url[CFG.URL_INDEX]).group(1))
            # print(f'Now extracting from Page 1 of Feature: '
            #       f'{feature_and_url[CFG.FEATURE_INDEX]}')
            logging.info(f'Now extracting from Page 1 of Feature: '
                         f'{feature_and_url[CFG.FEATURE_INDEX]}')

            all_product_info = Features.find_all_products(soup)
            Features.process_first_page_product(all_product_info, product_names)

            if num_pages > 1:
                Features.process_additional_page_products(num_pages, feature_and_url,
                                                          product_names, current_page)

            feature_and_url.append(product_names)
            feature_dict[feature_and_url[CFG.FEATURE_INDEX]] = product_names
            # print(feature_and_url)
            # print(f'products in {feature_and_url[CFG.FEATURE_INDEX]} feature: '
            #       f'{len(feature_and_url[CFG.PRODUCT_INDEX])}')

    @staticmethod
    def get_information():
        """
        This function is the top level function for executing all other
        feature functions. It calls get_features() to extract all features
        from the homepage html script. It then calls process_features()
        to extract all products corresponding to every feature. Once
        completed, it will create a csv file with the features and
        corresponding products
        """
        print('Extracting features...')
        logging.info('Extracting features')
        features_and_urls = \
            Features.get_features(CFG.URL_FIRST_PART
            + CFG.URL_SECOND_PART_FIRST_TIME
            + CFG.URL_PAGE_TAG)
        features_info = Features.process_features(features_and_urls)
        dict_file = open('features.csv', 'w')
        writer = csv.writer(dict_file)
        for feature, plants in features_info.items():
            # print(feature, plants)
            writer.writerow([feature, plants])
        dict_file.close()

    @staticmethod
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
            Features.process_feature(rs, index, unavailable_pages, feature_and_url,
                                     feature_dict)
        # print('*******************************************************')
        # print(f'scraper encountered {unavailable_pages} unavailable features pages')
        # print('*******************************************************')
        print('Features extracted!')
        logging.info('Features extracted')

        return feature_dict

    @staticmethod
    def output_json():
        """
        This function creates a json formated file with all the features on
        the webshop and the products that correspond to that feature.
        """
        features_and_urls = \
            Features.get_features(CFG.URL_FIRST_PART
            + CFG.URL_SECOND_PART_FIRST_TIME
            + CFG.URL_PAGE_TAG)
        features_info = Features.process_features(features_and_urls)
        with open('features.txt', 'w') as outfile:
            json.dump(features_info, outfile, indent=4)

    @staticmethod
    def create_api_dict():
        """
        This function sends a request to the growstuff.org api and returns a dictionary of crops and
        their corresponding features.
        """

        logging.info('Retrieving API info')

        api_dict = {}
        api = 'https://www.growstuff.org/api/v1/crops'
        response = requests.get(api)
        for entry in response.json().get('data'):
            if entry.get('attributes').get('perennial') is False:
                feature = 'no feature'
            else:
                feature = 'perennial'

            api_dict[entry.get('attributes').get('name')] = feature

        logging.info('API info retrieved')
        return api_dict

    @staticmethod
    def api_features_to_sql(api_info):
        """
        This function take a dictionary with crops and their features and inserts the data into the
        tables relevant to features in the SQL database that has already been created.
        """

        logging.info('Updating database with features API info')
        connection = pymysql.connect(host=CFG.SQL_HOST,
                                     user=CFG.SQL_USER,
                                     password=CFG.SQL_PASS,
                                     db=CFG.SQL_DB,
                                     charset=CFG.SQL_CHARSET,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )
        cursor = connection.cursor()
        connection.commit()

        sql_count_features = """ Select count(*) from features"""
        cursor.execute(sql_count_features)
        feature_counts = cursor.fetchall()[0].get('count(*)')

        new_features = set([value for value in api_info.values()])
        for feature in new_features:
            try:
                with connection.cursor() as cursor:
                    sql_feature = """ INSERT INTO features VALUES (%s, %s)"""
                    cursor.execute(sql_feature, (feature_counts, feature))
                connection.commit()
            except Exception:
                pass

            for product in api_info.keys():
                if api_info.get(product) == feature:
                    try:
                        with connection.cursor() as cursor:
                            sql_feature_prod_join = \
                                """ INSERT INTO features_prod_join VALUES (%s, %s)"""
                            cursor.execute(sql_feature_prod_join, (feature_counts, product))
                        connection.commit()
                    except Exception:
                        pass
            feature_counts += 1

        logging.info('Feature api update completed')
        connection.close()
