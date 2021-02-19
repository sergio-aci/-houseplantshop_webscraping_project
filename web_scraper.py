"""
Authors: Isaac Misri, Sergio Drajner

Description: This script scrapes a web site for the data mining project.
"""
import web_scraper_config as CFG
import grequests
import requests
from bs4 import BeautifulSoup
import re
import csv


def process_option(option_info, options_names, options_prices,
                   options_are_sold_out):
    """
    Processes an option of a product in the web site and updates the
    option lists for that product (i.e., option_names, option_prices
    and options_are_sold_out)
    :param option_info: raw information about the option of a product
    :param options_names: names of the options of a product
    :param options_prices: prices of the options of a product (may be 0
    if sold out)
    :param options_are_sold_out: indicate whether the options are sold
    out or not
    :return: updated options_names, options_prices and options_sold_out
    """
    options_names.append(option_info[:option_info.find(CFG.SEPARATOR)])
    if option_info.find('sold_out') == CFG.NOT_FOUND:
        options_prices.append(
            option_info[option_info.find(CFG.SEPARATOR)
                        + len(CFG.SEPARATOR + CFG.CURRENCY_SIGN):])
        options_are_sold_out.append(False)
    else:
        options_prices.append(CFG.NO_PRICE)
        options_are_sold_out.append(True)


def get_options_types(options):
    """
    :param options: raw information about the options of a product
    :return: a list of types of options of a product
    """
    options_types_raw = [option_type_raw.get_text()
                         for option_type_raw in options.select(".option-name")]
    return [option_type_raw[:option_type_raw.find(CFG.COLON)]
    if option_type_raw.find(CFG.COLON) != CFG.NOT_FOUND else option_type_raw
            for option_type_raw in options_types_raw]


def process_options(product, products_names, products_urls, products_prices,
                    products_are_sold_out):
    """
    Updates the product in the position being processed
    :param product: position in the different product lists to be
    updated
    :param products_names: list of names of products to be updated
    :param products_urls: list of names of urls of the products to
    find the options
    :param products_prices: list of prices of products to be updated
    :param products_are_sold_out: lists of flags indicating whether
    the products are sold out
    :return: updated products_names, products_prices and
    products_are_sold_out
    """
    options_names = []
    options_prices = []
    options_are_sold_out = []
    url = CFG.URL_FIRST_PART + products_urls[product]
    print(f'Processing product page {url} (with options)')
    web_page = requests.get(url)
    if web_page.status_code == requests.codes.ok:
        soup = BeautifulSoup(web_page.content, 'html.parser')
        options = soup.find(id="shopify-section-static-product")
        options_info = [option_info.get_text()
                            .strip(CFG.CHARACTERS_TO_STRIP).split(CFG.NEW_LINE)
                        for option_info in options.select("select", name="id")]
        for index in range(CFG.FIRST, len(options_info[CFG.FIRST]), CFG.IGNORE):
            option_info = options_info[CFG.FIRST][index].strip()
            process_option(option_info, options_names, options_prices,
                           options_are_sold_out)

        options_types = get_options_types(options)

        products_names[product] = [products_names[product]] + [options_types] \
                                  + [options_names]
        products_prices[product] = options_prices
        products_are_sold_out[product] = options_are_sold_out
    else:
        print(f'Could not download product page {url}')


def process_products(products, products_names, products_urls, have_options,
                     products_prices, products_are_sold_out):
    """
    Updates all the lists associated with the products of a page
    :param products: raw information of products of a page to be used
    as input
    :param products_names: list of names of products to be updated
    :param products_urls: list of urls of products to be updated
    :param have_options: list of flags indicating whether products have
     options, to be updated
    :param products_prices: list of prices of products to be updated
    :param products_are_sold_out: list of flags indicating whether they
    are sold out, to be updated
    :return: updated lists products_names, products_urls, have_options,
     product_prices, products_are_sold_out
    """
    elements_so_far = len(products_names)
    products_names += [name.get_text().strip(CFG.CHARACTERS_TO_STRIP)
                       for name in products.select(".productitem--title")]
    products_urls += [product_url["href"]
                      for product_url in products.select(".productitem--title a")]
    products_prices_or_options_raw = [price_raw.get_text()
                                          .strip(CFG.CHARACTERS_TO_STRIP)
                                      for position, price_raw in
                                      enumerate(products.select(".price--main"))
                                      if position % 2 == 0]  # remove duplicates
    have_options += [False
                     if price_raw.find(CFG.HAS_OPTIONS) == CFG.NOT_FOUND
                     else True
                     for price_raw in products_prices_or_options_raw]
    products_prices += [price_raw[price_raw.rfind(CFG.CURRENCY_SIGN) + 1::]
                        for price_raw in products_prices_or_options_raw]
    products_items = [product_item.get_text()
                      for product_item in products.select(".productitem")]
    products_are_sold_out += [False
                              if check_if_sold_out.find('Sold out') == CFG.NOT_FOUND
                              else True
                              for check_if_sold_out in products_items]
    for product in range(elements_so_far, len(have_options)):
        if have_options[product]:
            process_options(product, products_names, products_urls, products_prices,
                            products_are_sold_out)


def get_next_url_second_part(products):
    """
    :param products: raw information to extract the second part of the
     url of the next page
    :return url_second_part: second part of the url of the next page
    """
    url_second_part = None
    next_pages_section = products.select("a.pagination--item")
    pages = [page.get_text() for page in next_pages_section]
    if pages[CFG.LAST].strip() == 'Next':
        url_second_part = [page["href"]
                           for page in next_pages_section][CFG.LAST]
    return url_second_part


def get_feature(feature, additional_features_and_urls):
    """
    Given the html script of a particular feature, this function
    extracts the name and the url from the html script
    of that feature
    """
    try:
        additional_features_and_urls.\
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
        print(f'Now extracting from Page {page_num} of Feature: '
              f'{feature_and_url[CFG.FEATURE_INDEX]} ')
        new_url = feature_and_url[CFG.URL_INDEX]\
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
        print(f'Now extracting from Page 1 of Feature: '
              f'{feature_and_url[CFG.FEATURE_INDEX]}')

        all_product_info = find_all_products(soup)
        process_first_page_product(all_product_info, product_names)

        if num_pages > 1:
            process_additional_page_products(num_pages, feature_and_url,
                                             product_names, current_page)

        feature_and_url.append(product_names)
        feature_dict[feature_and_url[CFG.FEATURE_INDEX]] = product_names
        print(feature_and_url)
        print(f'products in {feature_and_url[CFG.FEATURE_INDEX]} feature: '
              f'{len(feature_and_url[CFG.PRODUCT_INDEX])}')


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
    print(f'scraper encountered {unavailable_pages} unavailable pages')
    print('*******************************************************')

    return feature_dict


def process_pages(products_names, products_urls, have_options,
                  products_prices, products_are_sold_out):
    """
    Processes the pages of the web site to scrape information, returns
    the information scraped
    :param products_names: list of names of products to scrape
    :param products_urls: list of urls of products to scrape
    :param have_options: list of flags indicating whether products
    have options, to scrape
    :param products_prices: list of prices of products to scrape
    :param products_are_sold_out: list of flags indicating whether
    they are sold out, to scrape
    :return: full lists products_names, have_options, product_prices,
    products_are_sold_out
    """
    url_second_part = CFG.URL_SECOND_PART_FIRST_TIME
    attempts = CFG.ATTEMPTS
    while True and attempts > 0:
        url = CFG.URL_FIRST_PART + url_second_part
        print(f'Processing page {url}')
        web_page = requests.get(url)
        if web_page.status_code == requests.codes.ok:

            soup = BeautifulSoup(web_page.content, 'html.parser')
            products = soup.find(id="shopify-section-static-collection")

            process_products(products,
                             products_names,
                             products_urls,
                             have_options,
                             products_prices,
                             products_are_sold_out)

            url_second_part = get_next_url_second_part(products)
            if url_second_part is None:
                break

            else:
                attempts = CFG.ATTEMPTS
        else:
            print(f'Could not download page {url}')
            attempts -= 1


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
        # exporting info to csv file
    dict_file = open('features.csv', 'w')
    writer = csv.writer(dict_file)
    for feature, plants in features_info.items():
        print(feature, plants)
        writer.writerow([feature, plants])
    dict_file.close()


def output_products(products_names, products_prices, products_are_sold_out):
    """
    Writes the results of the products extraction a csv file
    :param products_names: list of names of products to write
    :param products_prices: list of prices of products to write
    :param products_are_sold_out: list of flags indicating whether
    products are sold out, to write
    :return:
    """
    try:
        with open('products.csv', mode='w') as products_file:
            products_data = csv.writer(products_file)
            products_data.writerow(['Name [with Type/s, Option/s]', 'Price', 'Is Sold Out'])
            for name, price, is_sold_out in zip(products_names,
                                                products_prices,
                                                products_are_sold_out):
                products_data.writerow([name, price, is_sold_out])
    except Exception:
        print('There was an error writing to the products file')


def main():
    """
    This is the main function of the script
    :return:
    """
    get_additional_information()
    products_names = []
    products_urls = []
    have_options = []
    products_prices = []
    products_are_sold_out = []
    process_pages(products_names,
                  products_urls,
                  have_options,
                  products_prices,
                  products_are_sold_out)
    output_products(products_names, products_prices, products_are_sold_out)


if __name__ == '__main__':
    main()
