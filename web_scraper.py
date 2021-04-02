"""
Authors: Isaac Misri, Sergio Drajner
Description: This script scrapes a web site for the data mining project.
"""
import logging
import click
import pandas as pd
import web_scraper_config as CFG
import features_functions as ff
import product_info_functions as pif
import output_processing as op

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='2.0.0')
@click.option('--feature', help='Type a filter to get specific features (default: All)', type=str)
@click.option('--product', help='Type a filter to get specific products (default: All)', type=str)
@click.option('--price', '-p', help='Price range (default: All)', nargs=2,
              type=float)
@click.option('--output', '-o', help='Where do you want to write the data? (Default: no output'
                                     'unless you want to display on the screen)',
              type=click.Choice(['db', 'csv', 'json'], case_sensitive=False))
@click.option('--sort', '-s', help="Would you like your output sorted? (Default: unsorted). "
                                   "If so, how? By 'n'ame or by 'p'rice? "
                                   "'A'scending or 'd'escending order? (Default: ascending order)",
              type=click.Choice(['n', 'p', 'na', 'nd', 'pa', 'pd'], case_sensitive=False))
@click.option('--iterations', '-i', help='How many times do you want to try scraping the data?',
              type=int)
@click.option('--wait-time', '-w', help='How long do you want to wait between attempts to scrape '
                                        'the data (in seconds)?', type=int)
@click.option('--sold-out/--not-sold-out', '-so/-nso', help="Items sold out or not (default: All)", default=None)
@click.option('--scrape/--no-scrape', help='Where is the data coming from? Choose --no-scrape'
                                           'if you want to get it from csv files (Default: '
                                           'scrape', default=True)
@click.option('--screen/--no-screen', help='Display to screen (Default: yes)?', default=True)
@click.option('--break-down/--no-break-down', help='Break down display to screen by feature? '
                                                   'If not, will only show the '
                                                   'products (Default: only show products)', default=False)
def main(**kwargs):
    """
    Welcome to the web scraper by Sergio and Isaac!
    By using this tool, you'll be able to scrape the Houseplants Shop webpage
    and get information about its features and products. You'll also be able
    to create a customized output based on the options you choose. Please see
    below for the current ones. Enjoy!
    """
    logging.basicConfig(filename='web_scraper_log_file.log',
                        format='%(asctime)s-%(levelname)s-FILE:%(filename)s-'
                               'FUNC:%(funcName)s-LINE:%(lineno)d-%(message)s',
                        level=logging.INFO)
    logging.info(f"\tStart of script.")
    features_df, features_and_products_df = process_features(**kwargs)
    products_df = process_products(features_and_products_df, **kwargs)
    if kwargs['sort'] is not None:
        op.sort_result(features_df, products_df, **kwargs)
    op.output_result(features_df, products_df, **kwargs)
    logging.info(f"\tEnd of script.")


def process_features(**kwargs):
    """
    Gets the features from a features.csv created in the features_fiction script.
    Then, filters the features according to the parameters received.
    :param kwargs: parameters received from the CLI
    :return: features_df: dataframe
    """
    if kwargs['scrape']:
        ff.get_additional_information()
    features_to_filter_df = pd.read_csv('features.csv', names=['Feature', 'Products'])
    features_to_filter_df['Products'] = features_to_filter_df['Products']\
        .apply(lambda x: x[CFG.BEGINNING:CFG.END].split(', '))
    features_to_filter_df.fillna("", inplace=True)
    return op.filter_features(features_to_filter_df, **kwargs)


def process_products(features_and_products_df, **kwargs):
    """
    Gets the products according to the 'scraping' option: either from the
    web scraping process or from a products.csv file that could have been
    created by this script before.
    Then, filters the products according to the parameters received.
    :param features_and_products_df: dataframe with filtered features and
    their partly filtered products (flattened).
    :param kwargs: parameters received from the CLI
    :return: products_df: dataframe
    """
    products_columns = ['Name', 'Type', 'Option', 'Price', 'Is Sold Out']
    products_df = pd.DataFrame(columns=products_columns)
    if not kwargs['scrape']:
        products_df = pif.process_input_file(products_df, features_and_products_df, **kwargs)
    else:
        products_df = pif.process_pages(products_df, features_and_products_df, **kwargs)
    products_df.set_index(['Name', 'Type', 'Option'], inplace=True)
    return products_df


if __name__ == '__main__':
    main()
