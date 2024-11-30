from flask import Flask, send_file, request, jsonify
from flask_cors import CORS
import asyncpg
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from io import BytesIO
import numpy as np
from scipy.optimize import curve_fit
from decimal import Decimal

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database connection URL
DB_URL = os.getenv("DB_URL")


def exponential_func(x, a, b, c):
    """Exponential function: a * exp(b * x) + c."""
    return a * np.exp(b * x) + c


def calculate_trend(x_data, y_data, trend_type, prediction_points):
    """Calculate trend line and future predictions based on the trend type."""
    future_x_data = np.arange(len(x_data) + prediction_points)
    if trend_type == "linear":
        coeffs = np.polyfit(x_data, y_data, 1)
        trend_line = np.polyval(coeffs, x_data)
        future_trend = np.polyval(coeffs, future_x_data)
    elif trend_type == "exponential":
        params, _ = curve_fit(exponential_func, x_data, y_data, p0=(1, 0.01, 1))
        trend_line = exponential_func(x_data, *params)
        future_trend = exponential_func(future_x_data, *params)
    elif trend_type == "polynomial":
        coeffs = np.polyfit(x_data, y_data, 2)
        trend_line = np.polyval(coeffs, x_data)
        future_trend = np.polyval(coeffs, future_x_data)
    elif trend_type == "logarithmic":
        coeffs, _ = curve_fit(lambda x, a, b: a * np.log(x + 1) + b, x_data, y_data, p0=(1, 1))
        trend_line = coeffs[0] * np.log(x_data + 1) + coeffs[1]
        future_trend = coeffs[0] * np.log(future_x_data + 1) + coeffs[1]
    elif trend_type == "power-law":
        coeffs, _ = curve_fit(lambda x, a, b: a * x**b, x_data + 1, y_data, p0=(1, 1))
        trend_line = coeffs[0] * (x_data + 1) ** coeffs[1]
        future_trend = coeffs[0] * (future_x_data + 1) ** coeffs[1]
    elif trend_type == "moving_average":
        window_size = 3
        trend_line = np.convolve(y_data, np.ones(window_size) / window_size, mode="same")
        future_trend = np.concatenate([trend_line, np.repeat(trend_line[-1], prediction_points)])
    else:
        raise ValueError(f"Invalid trendType: {trend_type}")
    return trend_line, future_trend


def create_excel_report(dates, sales, trend_line, future_trend, frequency, prediction_points, end_date):
    """Create an Excel workbook with sales data and trend chart."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales Data"

    # Add headers
    sheet.append(["Date", "Total Sales", "Trend Line", "Estimated Future Trend"])

    # Add actual data rows
    for i, (date, sale) in enumerate(zip(dates, sales)):
        sheet.append([date, sale, trend_line[i], None])

    # Add future prediction rows
    future_dates = [
        end_date + timedelta(days=i) if frequency == "Daily" else
        end_date + timedelta(days=30 * i) if frequency == "Monthly" else
        end_date + timedelta(days=365 * i)
        for i in range(1, prediction_points + 1)
    ]
    for i, future_date in enumerate(future_dates):
        sheet.append([future_date, None, None, future_trend[len(dates) + i]])

    # Create and add a line chart
    chart = LineChart()
    chart.title = "Sales Trend"
    chart.x_axis.title = "Date"
    chart.y_axis.title = "Total Sales"
    data = Reference(sheet, min_col=2, min_row=1, max_row=sheet.max_row, max_col=4)
    labels = Reference(sheet, min_col=1, min_row=2, max_row=sheet.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    sheet.add_chart(chart, "E5")

    # Save workbook to a BytesIO stream
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


@app.get("/api/sales/fetch-sales")
async def fetch_sales():
    try:
        logging.debug("Establishing database connection...")
        connection = await asyncpg.connect(dsn=DB_URL)

        # Validate and parse query parameters
        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")
        gender = request.args.get("gender", "All")
        min_age = request.args.get("minAge")
        max_age = request.args.get("maxAge")
        city = request.args.get("city", "All")

        # Ensure required parameters are present
        if not start_date or not end_date:
            return {"error": "startDate and endDate are required."}, 400

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            if start_date > end_date:
                return {"error": "startDate must be before endDate."}, 400
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}, 400

        min_age = int(min_age) if min_age else None
        max_age = int(max_age) if max_age else None

        # Build and execute query
        query = """
            SELECT sale_id, title, age_group_name, description, age, gender, sale_date, quantity, total_price AS total_sales, category_name, city_name
            FROM Sales
            LEFT JOIN Clients ON Sales.client_id = Clients.client_id
            LEFT JOIN Age_groups ON Clients.age_group_id = Age_groups.age_group_id
            LEFT JOIN Books ON Sales.book_id = Books.book_id
            LEFT JOIN Subcategories ON Books.subcategory_id = Subcategories.subcategory_id
            LEFT JOIN Categories ON Subcategories.category_id = Categories.category_id
            LEFT JOIN Cities ON Sales.city_id = Cities.city_id
            WHERE sale_date BETWEEN $1 AND $2
        """
        params = [start_date, end_date]

        if gender != "All":
            query += " AND gender = $3"
            params.append(gender)
        if min_age is not None:
            query += f" AND age >= ${len(params) + 1}"
            params.append(min_age)
        if max_age is not None:
            query += f" AND age <= ${len(params) + 1}"
            params.append(max_age)
        if city != "All":
            query += " AND city_name = $3"
            params.append(city)

        query += " ORDER BY sale_date;"
        result = await connection.fetch(query, *params)

        if not result:
            return {"error": "No sales data found for the specified range."}, 404

        # Prepare the response data with additional details
        sales_data = [
            {
                "sale_id": row["sale_id"],
                "book_title": row["title"],
                "age_group": row["age_group_name"],
                "age": row["age"],
                "gender": row["gender"],
                "sale_date": row["sale_date"].strftime("%Y-%m-%d"),
                "quantity": row["quantity"],
                "total_sales": row["total_sales"],
                "category": row["category_name"],
                "city": row["city_name"],
            }
            for row in result
        ]

        # Return sales data (for the fetch-sales endpoint)
        return {"data": sales_data}

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": f"An error occurred while processing the request: {e}"}, 500

    finally:
        await connection.close()


@app.get("/api/sales/export-sales")
async def export_sales():
    try:
        logging.debug("Establishing database connection...")
        connection = await asyncpg.connect(dsn=DB_URL)

        # Validate and parse query parameters
        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")
        gender = request.args.get("gender", "All")
        min_age = request.args.get("minAge")
        max_age = request.args.get("maxAge")
        city = request.args.get("city", "All")
        trend_type = request.args.get("trendType", "linear")
        frequency = request.args.get("frequency", "Daily")
        prediction_years = int(request.args.get("predictionYears", 1))

        # Ensure required parameters are present
        if not start_date or not end_date:
            return {"error": "startDate and endDate are required."}, 400

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            if start_date > end_date:
                return {"error": "startDate must be before endDate."}, 400
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}, 400

        min_age = int(min_age) if min_age else None
        max_age = int(max_age) if max_age else None

        # Build and execute query
        query = """
            SELECT sale_id, title, age_group_name, description, age, gender, sale_date, quantity, total_price AS total_sales, category_name, city_name
            FROM Sales
            LEFT JOIN Clients ON Sales.client_id = Clients.client_id
            LEFT JOIN Age_groups ON Clients.age_group_id = Age_groups.age_group_id
            LEFT JOIN Books ON Sales.book_id = Books.book_id
            LEFT JOIN Subcategories ON Books.subcategory_id = Subcategories.subcategory_id
            LEFT JOIN Categories ON Subcategories.category_id = Categories.category_id
            LEFT JOIN Cities ON Sales.city_id = Cities.city_id
            WHERE sale_date BETWEEN $1 AND $2
        """
        params = [start_date, end_date]

        if gender != "All":
            query += " AND gender = $3"
            params.append(gender)
        if min_age is not None:
            query += f" AND age >= ${len(params) + 1}"
            params.append(min_age)
        if max_age is not None:
            query += f" AND age <= ${len(params) + 1}"
            params.append(max_age)
        if city != "All":
            query += " AND city_name = $3"
            params.append(city)

        query += " ORDER BY sale_date;"
        result = await connection.fetch(query, *params)

        if not result:
            return {"error": "No sales data found for the specified range."}, 404

        # Prepare the sales data
        sales_data = [
            {
                "sale_id": row["sale_id"],
                "book_title": row["title"],
                "age_group": row["age_group_name"],
                "age": row["age"],
                "gender": row["gender"],
                "sale_date": row["sale_date"].strftime("%Y-%m-%d"),
                "quantity": row["quantity"],
                "total_sales": row["total_sales"],
                "category": row["category_name"],
                "city": row["city_name"],
            }
            for row in result
        ]

        # Generate trend line and future predictions
        dates = [datetime.strptime(sale["sale_date"], "%Y-%m-%d") for sale in sales_data]
        sales = [float(sale["total_sales"]) for sale in sales_data]
        float_sales_array = np.array(sales, dtype=np.float64)
        trend_line, future_trend = calculate_trend(np.arange(len(sales)), sales, trend_type, prediction_years * 12)

        # Create Excel file with trend chart
        excel_output = create_excel_report(dates, float_sales_array, trend_line, future_trend, frequency, prediction_years * 12, end_date)

        # Send Excel file as response
        return send_file(excel_output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="sales_trend.xlsx")

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": f"An error occurred while processing the request: {e}"}, 500

    finally:
        await connection.close()


if __name__ == "__main__":
    app.run(debug=True)
