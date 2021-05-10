"""
Authors: Isaac Misri, Sergio Drajner
Description: This script contains all the functions that are used to extract
all product information for each product listed.
"""
import sys
import time
import logging
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pymysql.cursors
import web_scraper_config as CFG


class Products:
    """
    This is the class related to the information of Products.
    """
    def __init__(self, features_and_products_df, **kwargs):
        """
        Constructor for Products.
        Gets the products according to the 'scraping' option: either from the
        web scraping process or from a products.csv file that could have been
        created by this script before.
        Then, filters the products according to the parameters received.
        :param Products instance
        :param features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
        :param kwargs: parameters received from the CLI
        :return: products_df: dataframe
        """
        products_columns = ['Name', 'Type', 'Option', 'Price', 'Is Sold Out']
        self.products_df = pd.DataFrame(columns=products_columns)
        if not kwargs['scrape']:
            self.products_df = self.process_input_file(features_and_products_df, **kwargs)
        else:
            print('Extracting products...')
            self.productsdf = self.process_pages(features_and_products_df, **kwargs)
            print('Products extracted!')
        self.products_df.set_index(['Name', 'Type', 'Option'], inplace=True)

    def process_input_file(self, features_and_products_df, **kwargs):
        """
        Gets the file products.csv that was previously created as an input.
        Therefore, no scraping is performed. Then filters the products
        according to the received parameters.
        :param features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
        :param kwargs: parameters to be used for filtering
        :return: products_df: object dataframe
        """
        try:
            products_to_filter_df = pd.read_csv('products.csv')
        except FileNotFoundError:
            print('Error - Input file products.csv was not found in the current directory')
            sys.exit(4)

        products_to_filter_df.fillna("", inplace=True)
        products_to_filter_df = \
            self.filter_products(products_to_filter_df,
                                 features_and_products_df,
                                 **kwargs)
        self.products_df = self.products_df.append(products_to_filter_df)
        return self.products_df

    def process_pages(self, features_and_products_df, **kwargs):
        """
        Processes the pages of the web site to scrape information, returns
        the updated scraped information.
        :param features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
        :param kwargs: parameters to be used for filtering
        :return: products_df: object dataframe
        """
        url_second_part = CFG.URL_SECOND_PART_FIRST_TIME
        attempts = CFG.ATTEMPTS if kwargs['retries'] is None else kwargs['retries']
        wait_time = CFG.WAIT_TIME if kwargs['sleep'] is None else kwargs['sleep']
        while True and attempts > 0:
            url = CFG.URL_FIRST_PART + url_second_part
            logging.info(f'Processing page {url}')
            web_page = requests.get(url)
            if web_page.status_code == requests.codes.ok:
                soup = BeautifulSoup(web_page.content, 'html.parser')
                page_products = soup.find(id="shopify-section-static-collection")
                self.products_df = \
                    self.process_products(page_products,
                                          features_and_products_df,
                                          **kwargs)
                url_second_part = Products.get_next_url_second_part(page_products)
                if url_second_part is None:
                    break

                else:
                    attempts = CFG.ATTEMPTS if kwargs['retries'] is None else kwargs['retries']
                    wait_time = CFG.WAIT_TIME if kwargs['sleep'] is None else kwargs['sleep']
            else:
                attempts -= 1
                if attempts > 0:
                    logging.info(f"\tAttempting {attempts} more time{'s' if attempts > 1 else ''}"
                                 f" in {wait_time} second"
                                 f"{'s' if wait_time != 1 else ''}")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Could not download page {url}. ")
        return self.products_df

    @staticmethod
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

    @staticmethod
    def filter_products(products_to_filter_df, features_and_products_df, **kwargs):
        """
        Given the dataframe with products to filter, filter them according
        to the filtering parameters passed at kwargs.
        :param products_to_filter_df: dataframe
        :param features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
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
        if not (kwargs['feature'] is None and not kwargs['break_down']):
            products_to_filter_df = \
                features_and_products_df.merge(products_to_filter_df,
                                               how='inner', left_on='Products',
                                               right_on='Name')
            products_to_filter_df.drop(['Feature', 'Products'], axis=1, inplace=True)
            products_to_filter_df.drop_duplicates(inplace=True)
        products_filter = (products_to_filter_df['Name'].str.contains(kwargs['product'],
                                                                      case=False,
                                                                      regex=False,
                                                                      na=False)) \
        & (products_to_filter_df['Price'].between(price_inferior_limit,
                                                  price_superior_limit)) \
        & (products_to_filter_df['Is Sold Out'].between(boolean_to_compare_1,
                                                        boolean_to_compare_2))
        return products_to_filter_df[products_filter]

    def process_products(self, page_products, features_and_products_df, **kwargs):
        """
        Updates the products_df dataframe with all the products of a page
        :param page_products: bs4 object - raw information of products of a page
        to be used as input
        :param features_and_products_df: dataframe with filtered features and
        their partly filtered products (flattened).
        :param kwargs: parameters to be used for filtering
        :return: products_df: object dataframe, updated
        """
        filter_products_names = [name.get_text().strip(CFG.CHARACTERS_TO_STRIP)
                                 for name in page_products.select(".productitem--title")]
        filter_products_names = [filter_products_names[index]
                                 for index in range(CFG.FIRST_VALID,
                                                    len(filter_products_names),
                                                    CFG.SKIP_INVALID)]
        filter_products_urls = [product_url["href"]
                                for product_url in page_products.select(".productitem--title a")]
        filter_products_urls = [filter_products_urls[index]
                                for index in range(CFG.FIRST_VALID,
                                                   len(filter_products_urls),
                                                   CFG.SKIP_INVALID)]

        filter_products_prices_or_options_raw = \
            [price_raw.get_text().strip(CFG.CHARACTERS_TO_STRIP)
             for position, price_raw in enumerate(page_products.select(".price--main"))
             if position % 2 == 0]  # remove duplicates
        filter_have_options = [False
                               if price_raw.find(CFG.HAS_OPTIONS) == CFG.NOT_FOUND
                               else True
                               for price_raw in filter_products_prices_or_options_raw]
        filter_products_prices = [float(price_raw[price_raw.rfind(CFG.CURRENCY_SIGN) + 1::])
                                  for price_raw in filter_products_prices_or_options_raw]
        filter_products_items = [product_item.get_text()
                                 for product_item in page_products.select(".productitem")]
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
                products_to_filter_df = \
                    self.process_options(filter_products_names[product],
                                         filter_products_urls[product],
                                         products_to_filter_df,
                                         **kwargs)
        products_to_filter_df = self.filter_products(products_to_filter_df,
                                                     features_and_products_df,
                                                     **kwargs)
        self.products_df = \
            self.products_df.append(products_to_filter_df, ignore_index=True)
        self.products_df.fillna("", inplace=True)
        return self.products_df

    @staticmethod
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
        attempts = CFG.ATTEMPTS if kwargs['retries'] is None else kwargs['retries']
        wait_time = CFG.WAIT_TIME if kwargs['sleep'] is None else kwargs['sleep']
        page_is_ok = False
        while attempts > 0:
            web_page = requests.get(url)
            if web_page.status_code == requests.codes.ok:
                page_is_ok = True
                soup = BeautifulSoup(web_page.content, 'html.parser')
                options = soup.find(id="shopify-section-static-product")
                options_types = Products.get_options_types(options)
                options_info = \
                    [option_info.get_text().strip(CFG.CHARACTERS_TO_STRIP).split(CFG.NEW_LINE)
                     for option_info in options.select("select", name="id")]
                for index in range(CFG.FIRST, len(options_info[CFG.FIRST]), CFG.IGNORE):
                    option_info = options_info[CFG.FIRST][index].strip()
                    products_to_filter_df = \
                        Products.process_option(option_info, filter_product_name, options_types,
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

    @staticmethod
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
            option_price = \
                float(option_info[option_info.find(CFG.SEPARATOR)
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

    @staticmethod
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

    def get_product_info(self, product):
        """
        Given a product, return its information
        :return: products_df row: object dataframe row
        """
        return self.products_df.loc[product]

    def sort_products(self, how, is_in_ascending_order):
        """
        Sorts the products according to the desired category and order.
        :param how: indicates how products are to be sorted
        :param is_in_ascending_order: order features and products are to be sorted
        :return:
        """
        if how == 'index':
            self.products_df.sort_index(ascending=is_in_ascending_order, inplace=True)
        else:
            self.products_df.sort_values(by='Price', ascending=is_in_ascending_order, inplace=True)

    def display_products(self):
        """
        Displays the products.
        :return:
        """
        print('Product/s:')
        print(self.products_df.to_string())

    def fill_products_df(self):
        """
        This function takes a dataframe of products and inserts all the
        data into the general_product_name and all_products tables in a
        pre-existing plant_db SQL database. The tables are first
        refreshed before values are updated. All user information to
        connect to the database can be modified in the
        web_scraper_config.py file.
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
                sql_command_delete_general = """DELETE FROM general_product_names"""
                cursor.execute(sql_command_delete_general)
            connection.commit()
        except Exception:
            pass

        try:
            with connection.cursor() as cursor:
                sql_command_delete_all = """ DELETE FROM all_products"""
                cursor.execute(sql_command_delete_all)
            connection.commit()
        except Exception:
            pass

        repeated = {}
        type_id = 0
        product_id = 0

        for index, rows in self.products_df.iterrows():
            if index[CFG.NAME_INDEX] not in repeated.keys():
                repeated[index[CFG.NAME_INDEX]] = type_id
                type_id += 1

                if rows['Is Sold Out']:
                    bool_val = 1
                else:
                    bool_val = 0

                try:
                    with connection.cursor() as cursor:
                        sql_command_general = \
                            """ INSERT INTO general_product_names VALUES (%s, %s)"""
                        cursor.execute(sql_command_general,
                                       (repeated.get(index[CFG.NAME_INDEX]),
                                        index[CFG.NAME_INDEX]))
                    connection.commit()
                except Exception:
                    pass

                try:
                    with connection.cursor() as cursor:
                        sql_command_products = \
                         """ INSERT INTO all_products VALUES (%s, %s, %s, %s, %s)"""
                        cursor.execute(sql_command_products,
                                       (product_id,
                                        repeated.get(index[CFG.NAME_INDEX]),
                                        index[CFG.NAME_INDEX] + ' '
                                        + str(index[CFG.TYPE_INDEX]) + ' ' +
                                        str(index[CFG.OPTION_INDEX]),
                                        rows['Price'], bool_val))

                    connection.commit()
                except Exception:
                    pass

            else:

                if rows['Is Sold Out']:
                    bool_val = 1
                else:
                    bool_val = 0

                try:
                    with connection.cursor() as cursor:
                        sql_command_general = \
                            """ INSERT INTO general_product_names VALUES (%s, %s)"""
                        cursor.execute(sql_command_general,
                                       (repeated.get(index[CFG.NAME_INDEX]),
                                        index[CFG.NAME_INDEX]))
                    connection.commit()
                except Exception:
                    pass

                try:
                    with connection.cursor() as cursor:
                        sql_command_products = \
                         """ INSERT INTO all_products VALUES (%s, %s, %s, %s, %s)"""
                        cursor.execute(sql_command_products,
                                       (product_id, repeated.get(index[CFG.NAME_INDEX]),
                                        index[CFG.NAME_INDEX] + ' '
                                        + str(index[CFG.TYPE_INDEX]) + ' ' +
                                        str(index[CFG.OPTION_INDEX]), rows['Price'], bool_val))
                    connection.commit()
                except Exception:
                    pass

            product_id += 1

        connection.close()

    def output_products(self, **kwargs):
        """
        Outputs the products per the attached parameters.
        :param kwargs: parameters to be used for outputting
        :return:
        """
        if kwargs['output'].lower() == 'csv':
            self.products_df.to_csv('products.csv')
        elif kwargs['output'].lower() == 'json':
            self.products_df.to_json('products.json', orient="index")

    @staticmethod
    def api_products_to_sql(api_info):
        """
        This function take a dictionary with crops and their features and inserts the data into the
        tables relevant to products in the SQL database that has already been created.
        """
        logging.info('Updating database with product API info')
        connection = pymysql.connect(host=CFG.SQL_HOST,
                                     user=CFG.SQL_USER,
                                     password=CFG.SQL_PASS,
                                     db=CFG.SQL_DB,
                                     charset=CFG.SQL_CHARSET,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )
        cursor = connection.cursor()
        connection.commit()

        sql_count_general = """ Select count(*) from general_product_names"""
        cursor.execute(sql_count_general)
        gen_prod_counts = cursor.fetchall()[0].get('count(*)') + 1

        sql_count_all = """ Select count(*) from all_products"""
        cursor.execute(sql_count_all)
        all_prod_counts = cursor.fetchall()[0].get('count(*)') + 1

        for product in api_info.keys():
            try:
                with connection.cursor() as cursor:
                    sql_general = """ INSERT INTO general_product_names VALUES (%s, %s)"""
                    cursor.execute(sql_general, (gen_prod_counts, product))
                connection.commit()
            except Exception:
                pass

            try:
                with connection.cursor() as cursor:
                    sql_all = """ INSERT INTO all_products VALUES (%s, %s, %s, %s, %s)"""
                    cursor.execute(sql_all, (all_prod_counts, gen_prod_counts,
                                             product, 0, 1))
                connection.commit()
            except Exception:
                pass

            all_prod_counts += 1
            gen_prod_counts += 1

        logging.info('Product API update completed')
        connection.close()
