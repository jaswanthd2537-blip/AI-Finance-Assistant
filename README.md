# AI Finance Assistant

A working beginner-friendly Flask + SQLite + scikit-learn project based on the supplied SRS.

## Features
- Registration/login with hashed passwords
- Add income and expenses
- Automatic ML expense categorization
- Dashboard with balance and category chart
- Monthly category budgets
- Basic AI-style spending insights
- Transaction deletion
- JSON API for category prediction and insights

## Run on Windows
1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate it:
   `venv\Scripts\activate`
5. Install packages:
   `pip install -r requirements.txt`
6. Start:
   `python app.py`
7. Open `http://127.0.0.1:5000`

The first run creates `finance.db` and trains `expense_model.pkl`.

## Example
Description: `swiggy dinner 450`
Amount: `450`
Type: Expense
Category: Auto

The ML model should classify it as Food.

This is an educational application, not professional financial advice.
