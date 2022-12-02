import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Access each stock in the transactions database, where the most recent stock bought is at the top
    symbols = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY symbol ASC", session["user_id"])

    # For easy access to users later on when specifying cash
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

    # Grand total
    grand_total = 0.0

    # Loop through each stock and change the rows of the dictionary to be used in the html file
    for i in range(len(symbols)):
        stock = lookup(symbols[i]["symbol"])
        # Specify symbol
        symbols[i]["symbol"] = stock["symbol"]
        # Specify name
        symbols[i]["name"] = stock["name"]
        # Specify price
        symbols[i]["price"] = stock["price"]
        # Specify total using a float value
        symbols[i]["total"] = (float(stock["price"]) * float(symbols[i]["stocks"]))
        # Add to grand total
        grand_total += symbols[i]["total"]

    # Add user's current amount into grand total
    grand_total += float(user[0]["cash"])

    return render_template("index.html", symbols=symbols, cash=usd(user[0]["cash"]), total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Return apology if stock symbol input is blank
        if not request.form.get("symbol"):
            return apology("stock symbol does not exist", 400)

        # Look up the symbol
        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        # Return apology if stock symbol does not exist
        if not quote:
            return apology("stock symbol does not exist", 400)

        # Look up stock's current price
        current_price = quote["price"]

        # Name of stock
        name = quote["name"]

        # Look up number of shares user wants to buy
        try:
            shares = int(request.form.get("shares"))
            if shares < 1:
                return apology("number of shares is invalid", 400)
        except:
            return apology("number of shares is invalid", 400)

        # Calculate cost
        cost = current_price * shares

        # Check how much cash the user has
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

        # Check if user can afford the number of shares at current price
        if cost > cash:
            return apology("cannot afford the number of shares at the current price", 400)

        # Update finance.db (insert into syntax)
        db.execute("INSERT INTO transactions (user_id, symbol, stocks, price, name) VALUES (?, ?, ?, ?, ?)",
                   session["user_id"], quote["symbol"], shares, current_price, name)

        # Update cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - cost, session["user_id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/main")
@login_required
def history():
    """Show history of transactions"""
    # Access each stock in the transactions database, where the most recent stock bought is at the top
    symbols = db.execute("SELECT * FROM history WHERE user_id = ? ORDER BY symbol ASC", session["user_id"])

    # For easy access to users later on when specifying cash
    user = db.execute("SELECT * FROM history WHERE id = ?", session["user_id"])

    # Specify whether an input is purchased or not and change in index depending on whether or not it was sold or bought
    purchase = "PURCHASED"

    # Loop through each stock and change the rows of the dictionary
    for i in range(len(symbols)):
        stock = lookup(symbols[i]["symbol"])
        symbols[i]["symbol"] = stock["symbol"]
        symbols[i]["price"] = stock["price"]
        symbols[i]["stocks"] = stock["stocks"]
        # Change purchase depending on input
        if stock["stocks"] < 0:
            purchase = "SOLD"

    return render_template("history.html", symbols=symbols, purchase=purchase)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        # Return apology if no symbol was received
        if not request.form.get("symbol"):
            return apology("stock symbol does not exist", 400)

        # Look up the symbol
        quote = lookup(request.form.get("symbol"))

        # Return apology if stock symbol does not exist
        if not quote:
            return apology("stock symbol does not exist", 400)

        # Format to usd
        quote["price"] = usd(quote["price"])

        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Check if user's input username is blank
        username = request.form.get("username")
        if not username:
            return apology("must provide username", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username does not already exist
        if (len(rows) != 0):
            return apology("invalid username", 400)

        # Ensure user input a password
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure user input the confirmation
        elif not request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # Check if confirmation password is equal to password
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords do not match", 400)

        # Generate password hash
        hash = generate_password_hash(request.form.get("password"))

        # Store hashed password into users
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), hash)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/main", methods=["GET", "POST"])
@login_required
def main():
    """Sell shares of stock"""
    if request.method == "POST":
        # Return apology if stock symbol input is blank
        if not request.form.get("symbol"):
            return apology("stock symbol does not exist", 400)

        # Look up the symbol
        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        # Check to see if user owns shares of stock and by creating temporary column for total # of stocks
        stocks = db.execute("SELECT SUM(stocks) AS total_shares FROM transactions WHERE user_id = ? AND symbol = ?",
                            session["user_id"], quote["symbol"])
        if stocks[0]["total_shares"] <= 0:
            return apology("you do not own any shares of that stock", 400)

        # Look up number of shares user wants to buy
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("number of shares is invalid", 400)

        # Check if number of shares user wants to sell is greater than total stocks owned
        if shares > stocks[0]["total_shares"]:
            return apology("you do not own that many shares of that stock", 400)

       # Look up stock's current price
        current_price = quote["price"]

        # Name of stock
        name = quote["name"]

        # Calculate cost
        cost = current_price * shares

        # Check how much cash the user has
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

        # Update finance.db (insert into syntax)
        db.execute("INSERT INTO transactions (user_id, symbol, stocks, price, name) VALUES (?, ?, ?, ?, ?)",
                   session["user_id"], quote["symbol"], -(shares), current_price, name)

        # Update cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + cost, session["user_id"])

        return redirect("/")

    else:
        # Specify what the options for stocks are
        stocks = db.execute("SELECT symbol FROM transactions WHERE user_id = ?", session["user_id"])

        return render_template("main.html", stocks=stocks)

