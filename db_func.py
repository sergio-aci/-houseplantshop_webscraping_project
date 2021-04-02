import pymysql.cursors
import web_scraper_config as CFG
import output_processing as op


def fill_products_df(df):
    """
    This function takes a dataframe of products and inserts all the data into the general_product_name
    and all_products tables in a pre-existing plant_db SQL database.
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

    for index, rows in df.iterrows():
        if index[CFG.NAME_INDEX] not in repeated.keys():
            repeated[index[CFG.NAME_INDEX]] = type_id
            type_id += 1

            if rows['Is Sold Out'] == True:
                bool_val = 1
            else:
                bool_val = 0

            try:
                with connection.cursor() as cursor:
                    sql_command_general = """ INSERT INTO general_product_names VALUES (%s, %s)"""
                    cursor.execute(sql_command_general, (repeated.get(index[CFG.NAME_INDEX]),
                                                         index[CFG.NAME_INDEX]))
                connection.commit()
            except Exception:
                pass

            try:
                with connection.cursor() as cursor:
                    sql_command_products = """ INSERT INTO all_products VALUES (%s, %s, %s, %s, %s)"""
                    cursor.execute(sql_command_products,
                                   (product_id, repeated.get(index[CFG.NAME_INDEX]),
                                    index[CFG.NAME_INDEX] + ' ' + str(index[CFG.TYPE_INDEX]) + ' ' +
                                    str(index[CFG.OPTION_INDEX]), rows['Price'], bool_val))

                connection.commit()
            except Exception:
                pass

        else:

            if rows['Is Sold Out'] == True:
                bool_val = 1
            else:
                bool_val = 0

            try:
                with connection.cursor() as cursor:
                    sql_command_general = """ INSERT INTO general_product_names VALUES (%s, %s)"""
                    cursor.execute(sql_command_general, (repeated.get(index[CFG.NAME_INDEX]),
                                                         index[CFG.NAME_INDEX]))
                connection.commit()
            except Exception:
                pass

            try:
                with connection.cursor() as cursor:
                    sql_command_products = """ INSERT INTO all_products VALUES (%s, %s, %s, %s, %s)"""
                    cursor.execute(sql_command_products,
                                   (product_id, repeated.get(index[CFG.NAME_INDEX]),
                                    index[CFG.NAME_INDEX] + ' ' + str(index[CFG.TYPE_INDEX]) + ' ' +
                                    str(index[CFG.OPTION_INDEX]), rows['Price'], bool_val))
                connection.commit()
            except Exception:
                pass

        product_id += 1

    connection.close()


def fill_features_df(df):
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

    for row in df.itertuples():
        try:
            with connection.cursor() as cursor:
                sql_command_general = """ INSERT INTO features VALUES (%s, %s)"""
                cursor.execute(sql_command_general, (feature_id, row[CFG.FEATURE]))
            connection.commit()
        except Exception:
            pass

        for element in row[CFG.PRODUCT]:
            product = op.clean_product(element)
            try:
                with connection.cursor() as cursor:
                    sql_command_general = """ INSERT INTO features_prod_join VALUES (%s, %s)"""
                    cursor.execute(sql_command_general, (feature_id, product))
                connection.commit()
            except Exception:
                pass

        feature_id += 1

    connection.close()
