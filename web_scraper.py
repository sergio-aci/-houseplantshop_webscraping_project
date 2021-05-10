"""
Authors: Isaac Misri, Sergio Drajner
Description: This script scrapes a web site for the data mining project.
"""
import gevent.monkey
gevent.monkey.patch_all(thread=False, select=False)

import logging
import click
from product_info_functions import Products
from features_functions import Features
import output_processing as op

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='3.0.0')
@click.option('--feature', help='Type a filter to get specific features (default: All)', type=str)
@click.option('--product', help='Type a filter to get specific products (default: All)', type=str)
@click.option('--price', '-p', help='Price range (default: All)', nargs=2,
              type=float)
@click.option('--output', '-o', help='Where do you want to write the data? (Default: no output '
                                     'unless you want to display on the screen)',
              type=click.Choice(['db', 'csv', 'json'], case_sensitive=False))
@click.option('--sort', '-s', help="Would you like your output sorted? (Default: unsorted). "
                                   "If so, how? By 'n'ame or by 'p'rice? "
                                   "'A'scending or 'd'escending order? (Default: ascending order)",
              type=click.Choice(['n', 'p', 'na', 'nd', 'pa', 'pd'], case_sensitive=False))
@click.option('--retries', '-r', help='How many times do you want to try scraping the data?',
              type=int)
@click.option('--sleep', '-sl', help='How long do you want to wait between attempts to scrape '
                                     'the data (in seconds)?', type=int)
@click.option('--sold-out/--not-sold-out', '-so/-nso',
              help="Items sold out or not (default: All)", default=None)
@click.option('--scrape/--no-scrape', help='Where is the data coming from? Choose --no-scrape'
                                           'if you want to get it from csv files (Default: '
                                           'scrape', default=True)
@click.option('--verbose/--no-verbose', help='Display to screen (Default: yes)?', default=True)
@click.option('--enrich/--not-enrich',
              help='Enrich data base from API (Default: no)?', default=False)
@click.option('--break-down/--no-break-down',
              help='Break down display to screen by feature? '
                   'If not, will only show the products '
                   '(Default: only show products)', default=False)
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
    logging.info("\tStart of script.")
    houseplant_features = Features(**kwargs)
    houseplant_products = Products(houseplant_features.features_and_products_df, **kwargs)
    if kwargs['sort'] is not None:
        op.sort_result(houseplant_features, houseplant_products, **kwargs)
    op.output_result(houseplant_features, houseplant_products, **kwargs)
    if kwargs['enrich'] is None or kwargs['enrich'] :
        api_products_and_features = Features.create_api_dict()
        Features.api_features_to_sql(api_products_and_features)
        Products.api_products_to_sql(api_products_and_features)

if __name__ == '__main__':
    logging.info("\tEnd of script.")


if __name__ == '__main__':
    main()
