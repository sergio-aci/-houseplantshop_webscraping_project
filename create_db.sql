CREATE DATABASE plant_db;

CREATE TABLE general_product_names(
    type_id int NOT NULL PRIMARY KEY,
    product_name varchar(100) UNIQUE
);


CREATE TABLE all_products(
    product_id int NOT NULL PRIMARY KEY,
    type_id int,
    full_product_name varchar(100) UNIQUE,
    price float,
    sold_out bool,
    FOREIGN KEY (type_id) REFERENCES general_product_names(type_id)
);

CREATE TABLE features (
    feature_id int NOT NULL PRIMARY KEY,
    feature_name varchar(100) UNIQUE
);


CREATE TABLE features_prod_join(
    feature_id int,
    product_name varchar(100),
    FOREIGN KEY (feature_id) REFERENCES features(feature_id),
    FOREIGN KEY (product_name) REFERENCES general_product_names(product_name)
);

