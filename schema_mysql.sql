-- ShelfSignal MySQL schema reference.
-- The Flask application creates equivalent tables automatically via SQLAlchemy.
-- Create the database first: CREATE DATABASE shelfsignal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS products (
  product_id VARCHAR(32) PRIMARY KEY,
  product_name VARCHAR(120) NOT NULL,
  category VARCHAR(80) NOT NULL DEFAULT 'Uncategorised',
  default_price DOUBLE NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id VARCHAR(32) NOT NULL,
  store_id VARCHAR(32) NOT NULL,
  current_stock INT NOT NULL DEFAULT 0,
  lead_time_days INT NOT NULL DEFAULT 3,
  safety_stock_days INT NOT NULL DEFAULT 3,
  CONSTRAINT uq_inventory_product_store UNIQUE (product_id, store_id),
  CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sales_records (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  sale_date DATE NOT NULL,
  store_id VARCHAR(32) NOT NULL,
  product_id VARCHAR(32) NOT NULL,
  unit_price DOUBLE NOT NULL DEFAULT 0,
  promotion BOOLEAN NOT NULL DEFAULT FALSE,
  holiday BOOLEAN NOT NULL DEFAULT FALSE,
  sales_units INT NOT NULL,
  CONSTRAINT uq_sales_date_store_product UNIQUE (sale_date, store_id, product_id),
  CONSTRAINT fk_sales_product FOREIGN KEY (product_id) REFERENCES products(product_id),
  INDEX ix_sales_product_store_date (product_id, store_id, sale_date),
  INDEX ix_sales_sale_date (sale_date)
) ENGINE=InnoDB;
