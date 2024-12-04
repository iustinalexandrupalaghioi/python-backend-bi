import asyncpg
import random
import asyncio

async def update_sales_with_random_cities():
    # Connect to your PostgreSQL database
    conn = await asyncpg.connect(
        user='postgres',
        password='postgres',
        database='BookSales',
        host='localhost',  # Or your database host
        port='5432'        # Default PostgreSQL port
    )

    # Step 1: Fetch all city IDs from the cities table
    city_ids = await conn.fetch('SELECT city_id FROM cities;')
    city_ids = [city['city_id'] for city in city_ids]

    # Step 2: Fetch all sale IDs from the sales table
    sales_ids = await conn.fetch('SELECT sale_id FROM sales;')
    sales_ids = [sale['sale_id'] for sale in sales_ids]

    # Step 3: Update sales records with random city_id
    for sale_id in sales_ids:
        random_city_id = random.choice(city_ids)
        await conn.execute(
            'UPDATE sales SET city_id = $1 WHERE sale_id = $2;',
            random_city_id, sale_id
        )

    # Close the connection
    await conn.close()

    print("Sales records updated with random cities successfully.")

# Run the asynchronous function
asyncio.run(update_sales_with_random_cities())
