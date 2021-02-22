import web_scraper_config as CFG
import requests
from bs4 import BeautifulSoup
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
