from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from io import BytesIO
from flask import Flask, send_file, request
from flask_cors import CORS
import asyncpg
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database connection URL
url = os.getenv("DB_URL")

@app.get("/api/sales/export-sales")
async def export_sales():
    try:
        logging.debug("Establishing database connection...")
        connection = await asyncpg.connect(dsn=url)
        logging.debug("Database connection established.")

        # Get query parameters
        start_date = datetime.strptime(request.args.get("startDate"), "%Y-%m-%d").date()
        end_date = datetime.strptime(request.args.get("endDate"), "%Y-%m-%d").date()
        frequency = request.args.get("frequency")

        logging.debug(f"Received params: startDate={start_date}, endDate={end_date}, frequency={frequency}")

        if not start_date or not end_date:
            return {"error": "startDate and endDate are required."}, 400

        # Query to fetch sales data
        query = ""
        if frequency == "Daily":
            query = """
                SELECT sale_date, SUM(total_price) AS total_sales
                FROM Sales
                WHERE sale_date BETWEEN $1 AND $2
                GROUP BY sale_date
                ORDER BY sale_date;
            """
        elif frequency == "Monthly":
            query = """
                SELECT EXTRACT(YEAR FROM sale_date) AS sale_year,
                       EXTRACT(MONTH FROM sale_date) AS sale_month,
                       SUM(total_price) AS total_sales
                FROM Sales
                WHERE sale_date BETWEEN $1 AND $2
                GROUP BY sale_year, sale_month
                ORDER BY sale_year, sale_month;
            """
        elif frequency == "Yearly":
            query = """
                SELECT EXTRACT(YEAR FROM sale_date) AS sale_year,
                       SUM(total_price) AS total_sales
                FROM Sales
                WHERE sale_date BETWEEN $1 AND $2
                GROUP BY sale_year
                ORDER BY sale_year;
            """
        else:
            logging.error("Invalid frequency provided.")
            return {"error": "Invalid frequency"}, 400

        logging.debug("Executing query...")
        result = await connection.fetch(query, start_date, end_date)
        logging.debug(f"Query executed successfully. Result: {result}")

        if not result:
            logging.warning("No data found for the given parameters.")
            return {"error": "No sales data found for the specified range."}, 404

        # Prepare data for Excel
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sales Data"

        # Add headers
        if frequency == "Daily":
            sheet.append(["Sale Date", "Total Sales"])
        elif frequency == "Monthly":
            sheet.append(["Year-Month", "Total Sales"])
        else:
            sheet.append(["Year", "Total Sales"])

        # Add data rows
        for row in result:
            if frequency == "Daily":
                sheet.append([row["sale_date"], row["total_sales"]])
            elif frequency == "Monthly":
                year_month = f"{int(row['sale_year'])}-{int(row['sale_month']):02d}"
                sheet.append([year_month, row["total_sales"]])
            else:
                sheet.append([int(row["sale_year"]), row["total_sales"]])

        # Create a line chart
        chart = LineChart()
        chart.title = "Sales Trend"
        chart.style = 10
        chart.x_axis.title = "Time"
        chart.y_axis.title = "Total Sales"

        # Define data for the chart
        data = Reference(sheet, min_col=2, min_row=1, max_row=sheet.max_row)
        labels = Reference(sheet, min_col=1, min_row=2, max_row=sheet.max_row)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        # Position the chart on the sheet
        sheet.add_chart(chart, "E5")

        # Save the workbook to a BytesIO stream
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        await connection.close()

        # Return the file
        return send_file(
            output,
            as_attachment=True,
            download_name="sales_trend.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        logging.exception("Error occurred during export-sales:")
        return {"error": f"Internal server error: {str(e)}"}, 500
