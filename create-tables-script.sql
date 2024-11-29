-- Table for Categories
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
);

-- Table for Subcategories
CREATE TABLE subcategories (
    subcategory_id SERIAL PRIMARY KEY,
    subcategory_name VARCHAR(100) NOT NULL,
    category_id INT REFERENCES categories(category_id) ON DELETE CASCADE
);

-- Table for Age Groups
CREATE TABLE age_groups (
    age_group_id SERIAL PRIMARY KEY,
    age_group_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Table for Clients
CREATE TABLE clients (
    client_id SERIAL PRIMARY KEY,
    client_name VARCHAR(100),
    gender VARCHAR(10) CHECK (gender IN ('Male', 'Female', 'Other')),
    age_group_id INT REFERENCES age_groups(age_group_id)
);

-- Table for Books
CREATE TABLE books (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    publication_year INT,
    subcategory_id INT REFERENCES subcategories(subcategory_id) ON DELETE CASCADE
);

-- Table for Discounts
CREATE TABLE discounts (
    discount_id SERIAL PRIMARY KEY,
    discount_name VARCHAR(100) NOT NULL,
    discount_rate NUMERIC(5, 2) NOT NULL CHECK (discount_rate > 0 AND discount_rate <= 100),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

-- Table for Events
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    event_type VARCHAR(100),
    description TEXT,
    CHECK (end_date >= start_date) -- Ensure the end date is not before the start date
);

-- Table for Sales
CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(book_id) ON DELETE CASCADE,
    client_id INT REFERENCES clients(client_id),
    sale_date DATE NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    total_price NUMERIC(10, 2) NOT NULL,
    discount_id INT REFERENCES discounts(discount_id),
    event_id INT REFERENCES events(event_id) -- Allow NULL for event_id, meaning no event
);

-- Table for Stock
CREATE TABLE stock (
    stock_id SERIAL PRIMARY KEY,
    book_id INT UNIQUE REFERENCES books(book_id) ON DELETE CASCADE,
    current_stock INT NOT NULL CHECK (current_stock >= 0)
);

-- Table for Stock History
CREATE TABLE stock_history (
    stockhistory_id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stock(stock_id) ON DELETE CASCADE,
    change_date DATE NOT NULL,
    change_quantity INT NOT NULL,
    reason VARCHAR(255)
);



-- Table for Cities (Romanian Cities)
CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL UNIQUE
);

-- Insert some Romanian cities
INSERT INTO cities (city_name) VALUES 
    ('Bucharest'),
    ('Cluj-Napoca'),
    ('Timișoara'),
    ('Iași'),
    ('Constanța'),
    ('Craiova'),
    ('Galați'),
    ('Ploiești'),
    ('Brașov'),
    ('Oradea'),
	('Suceava'),
	('Baia Mare'),
	('Satu Mare'),
	('Dej'),
	('Vatra Dornei'),
	('Gura Humorului'),
	('Dorohoi')

-- Modify Sales Table to Include city_id
ALTER TABLE sales
ADD COLUMN city_id INT REFERENCES cities(city_id) ON DELETE SET NULL;


