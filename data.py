import asyncpg
import asyncio
import random
from datetime import date, timedelta
from faker import Faker


def get_age_group(age):
    """Determine the age group based on age."""
    if 13 <= age <= 19:
        return  1
    elif 20 <= age <= 64:
        return  2
    else:  
        return  3


# Initialize Faker
fake = Faker()

# Database connection parameters
DB_CONFIG = {
    "user": "postgres",
    "password": "postgres",
    "database": "BookStore",
    "host": "localhost",
    "port": 5432,
}

# Sample data for categories and subcategories
CATEGORIES = ["Fiction", "Technical", "Medical", "Historical", "Philosophy"]
SUBCATEGORIES = {
    "Fiction": ["Novels", "Short Stories", "Fantasy", "Mystery", "Drama"],
    "Technical": ["Programming", "Engineering", "Mathematics", "Science", "Data Science"],
    "Medical": ["Anatomy", "Pharmacology", "Surgery", "Nursing", "Psychology"],
    "Historical": ["Ancient", "Medieval", "Modern", "World Wars", "Cultural Studies"],
    "Philosophy": ["Ethics", "Logic", "Metaphysics", "Aesthetics", "Epistemology"],
}

AGE_GROUPS = [
    {"name": "Youth", "description": "Ages 13-19"},
    {"name": "Adults", "description": "Ages 20-64"},
    {"name": "Elderly", "description": "Ages 65+"},
]

# Discounts and Events Data
DISCOUNTS = [
    {"name": "Summer Sale", "rate": 15.0, "start_date": "2024-06-01", "end_date": "2024-06-30"},
    {"name": "Black Friday", "rate": 25.0, "start_date": "2024-11-25", "end_date": "2024-11-30"},
    {"name": "New Year Discount", "rate": 10.0, "start_date": "2025-01-01", "end_date": "2025-01-07"},
]

EVENTS = [
    {"name": "Book Fair", "start_date": "2024-03-01", "end_date": "2024-03-05", "event_type": "Exhibition", "description": "Annual book fair with authors and publishers."},
    {"name": "Literature Symposium", "start_date": "2024-08-15", "end_date": "2024-08-17", "event_type": "Conference", "description": "A symposium on modern literature."},
    {"name": "Summer Reading Event", "start_date": "2024-06-15", "end_date": "2024-06-20", "event_type": "Festival", "description": "Celebrate summer with discounts on selected books."},
]

def random_date_between(start_date, end_date):
    """Generate a random date between start_date and end_date."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

async def create_and_insert_data():
    # Connect to the database
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Insert categories and subcategories
        category_ids = {}
        for category, subcategories in SUBCATEGORIES.items():
            category_id = await conn.fetchval(
                "INSERT INTO categories (category_name) VALUES ($1) RETURNING category_id", category
            )
            category_ids[category] = category_id

            for subcategory in subcategories:
                await conn.execute(
                    "INSERT INTO subcategories (subcategory_name, category_id) VALUES ($1, $2)",
                    subcategory, category_id,
                )

        # Insert age groups
        age_group_ids = {}
        for group in AGE_GROUPS:
            age_group_id = await conn.fetchval(
                "INSERT INTO age_groups (age_group_name, description) VALUES ($1, $2) RETURNING age_group_id",
                group["name"], group["description"]
            )
            age_group_ids[group["name"]] = age_group_id  # Store the numeric ID, not the name

        clients = []
        for _ in range(2000):
            age = random.randint(13, 85)  # Assuming the age range is from 13 to 85
           
            
            # Make sure to use the correct age group ID (numeric) from the dictionary
            age_group_id = get_age_group(age)  # Correct reference

            gender = random.choice(["Male", "Female", "Other"])
            client_name = fake.name()
    
            # Insert client into the database
            client_id = await conn.fetchval(
                "INSERT INTO clients (client_name, gender, age_group_id, age) VALUES ($1, $2, $3, $4) RETURNING client_id",
                client_name, gender, age_group_id, age  # Use numeric age_group_id
            )
            clients.append(client_id)

        # Insert books
        books = []
        for _ in range(500):
            title = fake.sentence(nb_words=3).rstrip(".")
            author = fake.name()
            publication_year = random.randint(1990, 2024)
            subcategory = random.choice(list(SUBCATEGORIES.keys()))
            subcategory_id = await conn.fetchval(
                "SELECT subcategory_id FROM subcategories WHERE subcategory_name = $1 LIMIT 1", 
                random.choice(SUBCATEGORIES[subcategory])
            )
            book_id = await conn.fetchval(
                "INSERT INTO books (title, author, publication_year, subcategory_id) VALUES ($1, $2, $3, $4) RETURNING book_id",
                title, author, publication_year, subcategory_id,
            )
            books.append(book_id)

        # Insert discounts
        discount_ids = {}
        for discount in DISCOUNTS:
            discount_id = await conn.fetchval(
                "INSERT INTO discounts (discount_name, discount_rate, start_date, end_date) VALUES ($1, $2, $3, $4) RETURNING discount_id",
                discount["name"], discount["rate"], date.fromisoformat(discount["start_date"]), date.fromisoformat(discount["end_date"])
            )
            discount_ids[discount["name"]] = discount_id

        # Insert events
        event_ids = {}
        for event in EVENTS:
            event_id = await conn.fetchval(
                "INSERT INTO events (event_name, start_date, end_date, event_type, description) VALUES ($1, $2, $3, $4, $5) RETURNING event_id",
                event["name"], date.fromisoformat(event["start_date"]), date.fromisoformat(event["end_date"]), event["event_type"], event["description"]
            )
            event_ids[event["name"]] = event_id

        # Insert stock
        for book_id in books:
            await conn.execute(
                "INSERT INTO stock (book_id, current_stock) VALUES ($1, $2) ON CONFLICT (book_id) DO NOTHING",
                book_id, random.randint(10, 200)  # Random initial stock
            )

        # Insert sales
        start_date = date(2008, 1, 1)
        end_date = date(2024, 12, 31)
        for _ in range(5000):
            book_id = random.choice(books)
            client_id = random.choice(clients)
            
            # Randomly pick a discount or event to apply
            apply_discount = random.choice([True, False])
            apply_event = random.choice([True, False])

            sale_date = random_date_between(start_date, end_date)  # Sale date between the full range

            # Determine if discount or event is applicable and adjust sale date accordingly
            discount_id = None
            event_id = None

            if apply_discount:
                # Pick a random discount and set sale date between discount start and end date
                discount = random.choice(DISCOUNTS)
                discount_start_date = date.fromisoformat(discount["start_date"])
                discount_end_date = date.fromisoformat(discount["end_date"])
                sale_date = random_date_between(discount_start_date, discount_end_date)  # Set sale_date within discount period
                discount_id = discount_ids[discount["name"]]  # Use the discount ID

            if apply_event:
                # Pick a random event and set sale date between event start and end date
                event = random.choice(EVENTS)
                event_start_date = date.fromisoformat(event["start_date"])
                event_end_date = date.fromisoformat(event["end_date"])
                sale_date = random_date_between(event_start_date, event_end_date)  # Set sale_date within event period
                event_id = event_ids[event["name"]]  # Use the event ID

            quantity = random.randint(1, 5)  # Random quantity sold
            total_price = round(random.uniform(5.0, 100.0) * quantity, 2)  # Random total price

            await conn.execute(
                "INSERT INTO sales (book_id, client_id, sale_date, quantity, total_price, discount_id, event_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                book_id, client_id, sale_date, quantity, total_price, discount_id, event_id
            )

        print("Data insertion complete.")
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        traceback.print_exc()  # This will print the full stack trace
    finally:
        await conn.close()

# Run the script with asyncio.run() for Python 3.10+
if __name__ == "__main__":
    asyncio.run(create_and_insert_data())
