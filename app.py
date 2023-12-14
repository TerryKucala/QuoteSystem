###############################################################################
#        CSCI467 Group Project (Group 2b) APP.PY Main Driver Program          #
#                                                                             #
#                                                                             #
#                                                                             #
###############################################################################

###############################################################################
#                             IMPORTS                                         #
###############################################################################
from flask import Flask, flash, redirect, render_template, request, session
from flask_mail import Message, Mail
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector as mysql
import sqlite3 as sqlite
import requests
from datetime import datetime

###############################################################################
#                             CONFIG                                          #
###############################################################################
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = '42'
app.config['SESSION_PERMANENT'] = False
app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = 'b56514a7c4fd1b'
app.config['MAIL_PASSWORD'] = 'ad98ea22d7523f'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

###############################################################################
#                    LOGIN REQUIRED WRAPPER FUNCTIONS                         #
#       USE THESE WITH for example  (@associate_login_required)               #
###############################################################################
def associate_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("associate_id") is None:
            return redirect("/associate/login")
        return f(*args, **kwargs)
    return decorated_function

def convert_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("inhouse_id") is None:
            return redirect("/convert/login")
        return f(*args, **kwargs)
    return decorated_function

def sanction_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("inhouse_id") is None:
            return redirect("/sanction/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("admin_id") is None:
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated_function    

def apology(message, code=400):
    return render_template("error.html", top=code, bottom=message), code

###############################################################################
#                   USEFUL HELPER FUNCTIONS                                   #
###############################################################################
# Returns a database object for the legacy db, use with db = legacy_db()
def legacy_db():
    SQLHOST = "blitz.cs.niu.edu"
    SQLDB = "csci467"
    SQLUSER = "student"
    SQLPW = "student"
    SQLPORT = "3306"
    return mysql.connect(host=SQLHOST, 
                        database=SQLDB, 
                        user=SQLUSER, 
                        password=SQLPW, 
                        port=SQLPORT) 

# Returns a database object for the current db, use with db = current_db()
def current_db():
    return sqlite.connect("./db/csci467.sqlite")

# Sends a quote to the RESTFul API Quote Processing System at NIU
def send_quote_to_api(order, associate, custid, amount):
    APIURL = "http://blitz.cs.niu.edu/PurchaseOrder/"

    purchase_order = {
        "order": order,
        "associate": associate,
        "custid": custid,
        "amount": amount
    }

    response = requests.post(APIURL, json=purchase_order)
    return response.json()

###############################################################################
#                     ASSOCIATES QUOTE ROUTE                                  #
###############################################################################

###############################################################################
#                     USABLE FUNCTIONS                                        #
###############################################################################
# Gets the quotes that a specific associate owns
def get_quotes_by_associate(associate_id):
    db = current_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT *
        FROM Quote
        WHERE Quote.AssociateID = ? AND Quote.Finalized = 0
        GROUP BY Quote.ID, Quote.CustID
    """, (associate_id,))
    quotes = cursor.fetchall()
    db.close()
    return quotes

###############################################################################
#                         HOME ROUTE                                          #
###############################################################################
@app.route('/')
def main_home():
    return render_template("home.html")

@app.route('/about')
def main_about():
    return render_template("about.html")

###############################################################################
#                     ROUTES                                                  #
###############################################################################
# Associate Interface Follows

# Logged in Associate Home Route
@app.route('/associate', methods=["GET", "POST"])
@associate_login_required
def associate_home():
    associate_id = session["associate_id"]
    quotes = get_quotes_by_associate(associate_id)
    return render_template("./associate/home.html", quotes=quotes)

# Associates New Quote Route
@app.route('/associate/newquote', methods=["GET"])
@associate_login_required
def associate_newquote():
    db = legacy_db()
    crsr = db.cursor()
    crsr.execute("SELECT name, id FROM customers")
    rows = crsr.fetchall()
    db.close()
    return render_template("./associate/newquote.html", customers=rows)

# Associates Create Quote Route
@app.route('/associate/createquote', methods=["GET", "POST"])
@associate_login_required
def associate_createquote():
    if request.method == "POST":
        cust_id = request.form.get("customer")
        
        # Get Customer Info from Legacy DB
        db = legacy_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM customers WHERE id = %s", (cust_id,))
        row = crsr.fetchone()
        cust_name = row[1]
        cust_city = row[2]
        cust_addr = row[3]
        cust_contact = row[4]
        date = datetime.now()
        date = date.strftime("%Y/%m/%d")
        db.close()

        cust_email = request.form.get("custEmail")

        # Create Quote
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("""INSERT INTO quote 
                         (AssociateID, CustID, CustName, CustCity, CustAddr, CustContact, Date, CustEmail) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?);""", 
                         (session["associate_id"], cust_id, cust_name, cust_city, 
                          cust_addr, cust_contact, date, cust_email))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE INSERT ERROR", "warning")

        quote_id = crsr.lastrowid
        crsr.execute("SELECT * from quote WHERE ID = ?", (quote_id,))
        quote_data = crsr.fetchone()

        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
        line_item_rows = crsr.fetchall()

        crsr.execute("SELECT * FROM secretnotes WHERE QuoteID = ?", (quote_id,))
        sec_notes_rows = crsr.fetchall()

        db.close()
        return render_template("/associate/editquote.html",
                               quote_id=quote_id,
                               quote=quote_data,
                               lirows=line_item_rows,
                               notesrows=sec_notes_rows)
    else:
        flash("Please select a customer", "info")
        db = legacy_db()
        crsr = db.cursor()
        crsr.execute("SELECT name, id FROM customers")
        rows = crsr.fetchall()
        db.close()
        return render_template("newquote.html", customers=rows)

# Associate Confirm Delete Route
@app.route('/associate/delconfirm', methods=["GET", "POST"])
@associate_login_required
def associate_del_confirm():
    if request.method == "POST":
        del_id  = request.form.get("del_quote_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM quote WHERE id = ?", (del_id,))
        quote = crsr.fetchone()
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (del_id,))
        line_items = crsr.fetchall()
        db.close()
        total_price = 0.0
        for li in line_items:
            total_price += li[2]
        price_string = "{:,.2f}".format(total_price)
        return render_template("/associate/delconfirm.html", 
                               quote=quote, 
                               line_items=line_items, 
                               price=price_string)
    else:
        return redirect('/associate')

# Associate Edit Quote Route
@app.route('/associate/editquote', methods=["GET", "POST"])
@associate_login_required
def associate_edit_quote():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        quote_id = request.form.get("edit_quote_id")
        if request.form.get("lisubmit") == "li":
            try:
                desc = request.form.get("line_item")
                price = request.form.get("price")
                crsr.execute("""INSERT INTO lineitems (Description, Price, QuoteID)
                            VALUES (?, ?, ?)""", (desc, price, quote_id))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE INSERT ERROR", "warning")

        elif request.form.get("nosubmit") == "no":
            try:
                note = request.form.get("notes")
                crsr.execute("""INSERT INTO secretnotes (NoteText, QuoteID)
                            VALUES (?, ?)""", (note, quote_id))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE INSERT ERROR", "warning")

        elif request.form.get("del_line_item"):
            li_to_delete = request.form.get("del_line_item")
            try:
                crsr.execute("DELETE FROM lineitems WHERE id = ?", (li_to_delete,))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE DELETION ERROR", "warning")

        elif request.form.get("del_note"):
            note_to_delete = request.form.get("del_note")
            try:
                crsr.execute("DELETE FROM secretnotes WHERE id = ?", (note_to_delete,))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE DELETION ERROR", "warning")
                        
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
        line_item_rows = crsr.fetchall()
        total_price = sum(row[2] for row in line_item_rows)
        
        try:
            crsr.execute("""UPDATE quote 
                        SET SubTotal = (?)
                        WHERE ID = (?);""", (total_price, quote_id))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE ERROR", "warning")

        crsr.execute("SELECT * FROM secretnotes WHERE QuoteID = ?", (quote_id,))
        sec_notes_rows = crsr.fetchall()
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        quote_data = crsr.fetchone()
        db.close()

        return render_template("/associate/editquote.html",
                               quote_id=quote_id,
                               quote=quote_data,
                               lirows=line_item_rows,
                               notesrows=sec_notes_rows)
    else:
        return redirect("/associate")

# Confirm Edit Quote Route
@app.route('/associate/editconfirm', methods=["GET", "POST"])
@associate_login_required
def associate_confirm_edit():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        quote_id = request.form.get("quote_id")
        crsr.execute("SELECT * FROM quote WHERE id = ?", (quote_id,))
        quote = crsr.fetchone()
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
        line_items = crsr.fetchall()
        total_price = sum(row[2] for row in line_items)
        price_string = "{:,.2f}".format(total_price)

        return render_template("/associate/editconfirm.html",
                               quote=quote,
                               line_items=line_items,
                               total_price=price_string)
    else:
        return redirect("/associate")

# Process Finalize Quote Route
@app.route('/associate/finalizequote', methods=["GET", "POST"])
@associate_login_required
def associate_finalize_quote():
    if request.method == "POST":
        cust_email = request.form.get("email")
        quote_id = request.form.get("quote_id")
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("""UPDATE quote 
                            SET CustEmail = ?, Finalized = 1
                            WHERE id = ?;""", 
                            (cust_email, quote_id))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE ERROR", "warning")
        db.close()
        flash("Quote Finalized", "primary")
        return redirect("/associate")
    else:
        return redirect("/associate")
            
# Associates Delete Quote Route
@app.route('/associate/delquote', methods=["GET", "POST"])
@associate_login_required
def associate_del_quote():
    if request.method == "POST":
        del_id = request.form.get("del_quote_submit")
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("DELETE FROM quote WHERE id = ?", (del_id,))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE DELETION ERROR", "warning")
        return redirect('/associate') 

# Associates Login Route
@app.route('/associate/login', methods=["GET", "POST"])
def associate_login():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        un = request.form.get("username")
        pw = request.form.get("password")
        crsr.execute("SELECT * FROM associate WHERE username = ?;", (un,))
        rows = crsr.fetchall()
        db.close()
        if len(rows) != 1 or not check_password_hash(rows[0][2], pw):
            flash("Invalid Username or Password", "danger")
            return redirect('/associate/login')
        
        session["associate_id"] = rows[0][0]
        session["associate_firstName"] = rows[0][5]
        flash("Login Succesful", "primary")
        return redirect('/associate')
    else:
        return render_template("./associate/login.html")

# Associates Logout Route
@app.route('/associate/logout')
@associate_login_required
def associate_logout():
    session.clear()
    flash("Logged Out Successfully", "primary")
    return redirect("/associate")

###############################################################################
#                      SANCTION QUOTES ROUTE                                  #
###############################################################################
@app.route('/sanction', methods=['GET', 'POST'])
@sanction_login_required
def sanction_home():
    if request.method == 'POST':
        pass
    db = current_db()
    crsr = db.cursor()

    crsr.execute("SELECT * FROM quote WHERE finalized = 1 AND sanctioned = 0")
    finalized_quotes = crsr.fetchall()

    db.close()

    return render_template("./sanction/home.html", finalized_quotes=finalized_quotes)

# Sanction Quote login route
@app.route('/sanction/login', methods=["GET", "POST"])
def sanction_login():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        un = request.form.get("username")
        pw = request.form.get("password")
        crsr.execute("SELECT * FROM inhouseemployee WHERE username = ?;", (un,))
        rows = crsr.fetchall()
        db.close()
        if len(rows) != 1 or not check_password_hash(rows[0][2], pw):
            flash("Invalid Username or Password", "danger")
            return redirect('/sanction/login')
        
        session["inhouse_id"] = rows[0][0]

        flash("Login Succesful", "primary")
        return redirect('/sanction')
    else:
        return render_template("./sanction/login.html")
    
# Sanction Delete Quote Route
@app.route('/sanction/delquote', methods=["GET", "POST"])
@sanction_login_required
def sanction_del_quote():
    if request.method == "POST":
        del_id = request.form.get("del_quote_submit")
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("DELETE FROM quote WHERE id = ?", (del_id,))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE DELETION ERROR", "warning")
        return redirect('/sanction') 
    
# Sanction quote deletion confirmation
@app.route('/sanction/delconfirm', methods=["GET", "POST"])
@sanction_login_required
def sanction_del_confirm():
    if request.method == "POST":
        del_id  = request.form.get("del_quote_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM quote WHERE id = ?", (del_id,))
        quote = crsr.fetchone()
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (del_id,))
        line_items = crsr.fetchall()
        db.close()
        total_price = 0.0
        for li in line_items:
            total_price += li[2]
        price_string = "{:,.2f}".format(total_price)
        return render_template("/sanction/delconfirm.html", 
                                quote=quote, 
                                line_items=line_items, 
                                price=price_string)
    else:
        return redirect("/sanction/home.html")

# Sanction Edit Quote Route
@app.route('/sanction/editquote', methods=["GET", "POST"])
@sanction_login_required
def sanction_edit_quote():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        quote_id = request.form.get("edit_quote_id")
                
        # Line item submit        
        if request.form.get("lisubmit") == "li":
            try:
                desc = request.form.get("line_item")
                price = request.form.get("price")
                crsr.execute("""INSERT INTO lineitems (Description, Price, QuoteID)
                            VALUES (?, ?, ?)""", (desc, price, quote_id))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE INSERT ERROR", "warning")

        # Note submit
        if request.form.get("nosubmit") == "no":
            try:
                note = request.form.get("notes")
                crsr.execute("""INSERT INTO secretnotes (NoteText, QuoteID)
                            VALUES (?, ?)""", (note, quote_id))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE INSERT ERROR", "warning")
        
        # Discount
        if request.form.get("discount_type") and request.form.get("discount_amount"):
            discount_type = request.form.get("discount_type")
            discount_amount = request.form.get("discount_amount")

            try:
                # Convert discount_amount to float
                discount_amount = float(discount_amount)

                if discount_type == "percentage":
                    # Check for valid percentage range
                    if discount_amount < 0 or discount_amount > 100:
                        flash("Invalid percentage value. Must be between 0 and 100.", "warning")
                    else:
                        crsr.execute("""UPDATE quote 
                                        SET InitDiscountPercent = ?, InitDiscountAmt = ?
                                        WHERE ID = (?);""",
                                        (discount_amount, 0, quote_id))
                        db.commit()
                        flash("Discount Applied", "success")

                elif discount_type == "flat":
                    if discount_amount < 0 :
                        flash("Invalid flat amount. Must be greater than 0.", "warning")
                    else:
                        crsr.execute("""UPDATE quote 
                                        SET InitDiscountPercent = ?, InitDiscountAmt = ?
                                        WHERE ID = (?);""",
                                        (0, discount_amount, quote_id))
                        db.commit()
                        flash("Discount Applied", "success")

            except ValueError:
                db.rollback()
                flash("Invalid discount amount. Must be a number.", "warning")
            except:
                db.rollback()
                flash("DATABASE ERROR", "warning") 

        # Handle resetting the discount
        if request.form.get("reset_discount"):
            try:
                # Reset discount values
                crsr.execute("""UPDATE quote 
                                SET InitDiscountPercent = 0, InitDiscountAmt = 0
                                WHERE ID = (?);""", (quote_id,))
                db.commit()

                # Recalculate total price based on line items
                crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
                line_item_rows = crsr.fetchall()
                total_price = sum(row[2] for row in line_item_rows)
                
                # Update the total price in the quote table
                crsr.execute("""UPDATE quote 
                                SET SubTotal = (?)
                                WHERE ID = (?);""", (total_price, quote_id))
                
                db.commit()
                flash("Discount reset to 0. Total price recalculated.", "success")
            except:
                db.rollback()
                flash("DATABASE ERROR", "warning")

        # Delete Line item
        if request.form.get("del_line_item"):
            li_to_delete = request.form.get("del_line_item")
            try:
                crsr.execute("DELETE FROM lineitems WHERE id = ?", (li_to_delete,))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE DELETION ERROR", "warning")

        # Delete note
        if request.form.get("del_note"):
            note_to_delete = request.form.get("del_note")
            try:
                crsr.execute("DELETE FROM secretnotes WHERE id = ?", (note_to_delete,))
                db.commit()
            except:
                db.rollback()
                flash("DATABASE DELETION ERROR", "warning")
                
                
        # Handle editing line items
        if request.form.get("edit_line_item"):
            line_item_id = request.form.get("edit_line_item")
            edit_line_item_desc = request.form.get(f"edit_line_item_desc_{line_item_id}")
            edit_line_item_price = request.form.get(f"edit_line_item_price_{line_item_id}")

            # Ensure edit_line_item_desc is not None or empty before updating
            if edit_line_item_desc is not None:
                crsr.execute("""UPDATE lineitems 
                                SET Description = ?, Price = ?
                                WHERE id = ?;""", (edit_line_item_desc, edit_line_item_price, line_item_id))
                db.commit()
            else:
                flash("Invalid line item description", "warning")
                        
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
        line_item_rows = crsr.fetchall()
        
        # Retrieve discount values
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        discount_values = crsr.fetchone()

        # Calculate the total price after applying the discount
        total_price = sum(row[2] for row in line_item_rows)
        discounted_price = total_price
        # Apply percentage discount
        percent = discount_values[4] / 100
        discounted_price -= discounted_price * percent
        # Subtract flat amount discount
        discounted_price -= discount_values[5]
            
        # Ensure total price is not below 0
        total_price = max(total_price, 0)    

        try:
            crsr.execute("""UPDATE quote 
                            SET SubTotal = (?)
                            WHERE ID = (?);""", (total_price, quote_id))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE ERROR", "warning")

        # Retrieve secret notes and quote data
        crsr.execute("SELECT * FROM secretnotes WHERE QuoteID = ?", (quote_id,))
        sec_notes_rows = crsr.fetchall()
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        quote_data = crsr.fetchone()
        db.close()

        return render_template("/sanction/editquote.html",
                                quote_id=quote_id,
                                quote=quote_data,
                                lirows=line_item_rows,
                                notesrows=sec_notes_rows,
                                discount_values=discount_values,
                                discounted_price=discounted_price)
    else:
        return redirect("/sanction")
    
# Sanction quote confirm view.
@app.route('/sanction/sanctionquote', methods=["GET", "POST"])
@sanction_login_required
def sanction_quote():
    quote_id = request.form.get("quote_id")
    if request.method == "POST":
        # Check if the "save_changes" button was clicked
        if "save_changes" in request.form:
            # Handle saving changes logic here
            flash("Changes saved", "success")
            return redirect(f'/sanction/sanctionquote')
        
    # If the form was not submitted, retrieve the quote, line items, and notes
    db = current_db()
    crsr = db.cursor()
    crsr.execute("SELECT * FROM quote WHERE id = ?", (quote_id,))
    quote = crsr.fetchone()
    crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
    line_item_rows = crsr.fetchall()
    crsr.execute("SELECT * FROM secretnotes WHERE QuoteID = ?", (quote_id,))
    sec_notes_rows = crsr.fetchall()
    total_price = sum(row[2] for row in line_item_rows)
    discounted_price = total_price

    # Apply percentage discount
    percent = quote[4] / 100
    discounted_price -= discounted_price * percent
    # Subtract flat amount discount
    discounted_price -= quote[5]
        
    # Ensure total price is not below 0
    total_price = max(total_price, 0)    

    db.close()

    return render_template("/sanction/sanctionquote.html", 
                           quote=quote, 
                           line_item_rows=line_item_rows, 
                           sec_notes_rows=sec_notes_rows,
                           discounted_price=discounted_price)

# Send Sanctioning Email
@app.route('/sanction/send_email', methods=["GET", "POST"])
@sanction_login_required
def send_email():
    if request.method == "POST":
        quote_id = request.form.get("quote_id")
        print(quote_id)
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("""UPDATE quote SET sanctioned = 1 where ID = ?""", (quote_id,))
            db.commit()
        except:
            db.rollback()
            flash("Database Error", "warning")
        db.close()

        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM quote WHERE id = ?", (quote_id,))
        quote = crsr.fetchone()
        crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
        line_item_rows = crsr.fetchall()
        total_price = sum(row[2] for row in line_item_rows)
        discounted_price = total_price

        # Apply percentage discount
        percent = quote[4] / 100
        discounted_price -= discounted_price * percent
        # Subtract flat amount discount
        discounted_price -= quote[5]
            
        # Ensure total price is not below 0
        total_price = max(total_price, 0) 

        # Compose Email
        body_string = "Thank you for your order from CSCI467 group 2b! The details are as follows:\n"
        body_string += "Date: %s \n" %(quote[11])
        body_string += "Customer: %s \n" %(quote[13])
        
        body_string += "LINE ITEMS:\n"
        for LI in line_item_rows:
            body_string += "%s -- %s \n" %(LI[1], LI[2])
        
        body_string += "--------------------\n"
        body_string += "TOTAL: %s \n" %(total_price)
        msg = Message("Order Sanctioned from CSCI467Mart", 
                      sender="CSCI467@NIU.EDU",
                      recipients=[quote[3]],
                      body=body_string)
        mail.send(msg)
        flash("Email Sent to Customer: Quote Successfully Sanctioned", "success")

        return redirect('/sanction')
    else:
        return redirect('/sanction')

# Sanction Logout Route
@app.route('/sanction/logout')
@sanction_login_required
def sanction_logout():
    session.clear()
    flash("Logged Out Successfully", "primary")
    return redirect("/sanction")

###############################################################################
#                      QUOTE CONVERSION ROUTE                                 #
###############################################################################
# Quote Conversion Interface Follows
@app.route('/convert', methods=['GET', 'POST'])
@convert_login_required
def convert_home():
    if request.method == 'POST':
        pass
    db = current_db()
    crsr = db.cursor()

    crsr.execute("SELECT ID, date, CustName, FirstName, LastName, CustContact, SubTotal FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE finalized = 1 AND sanctioned = 1 AND ordered = 0")
    sanctioned_quotes = crsr.fetchall()

    db.close()

    return render_template("./convert/home.html", sanctioned_quotes=sanctioned_quotes)

# Quote conversion login route
@app.route('/convert/login', methods=["GET", "POST"])
def convert_login():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        un = request.form.get("username")
        pw = request.form.get("password")
        crsr.execute("SELECT * FROM inhouseemployee WHERE username = ?;", (un,))
        rows = crsr.fetchall()
        db.close()
        if len(rows) != 1 or not check_password_hash(rows[0][2], pw):
            flash("Invalid Username or Password", "danger")
            return redirect('/convert/login')
        
        session["inhouse_id"] = rows[0][0]

        flash("Login Succesful", "primary")
        return redirect('/convert')
    else:
        return render_template("./convert/login.html")

# Convert Quote Route
@app.route('/convert/convertquote', methods=["GET", "POST"])
@convert_login_required
def convert_quote():
    if request.method == "POST":
        quote_id = request.form.get("convert_quote_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        quote_data = crsr.fetchone()
        total_price = quote_data[17]
        reset_price = total_price
        
        # Discount
        if request.form.get("discount_type") and request.form.get("discount_amount"):
            discount_type = request.form.get("discount_type")
            discount_amount = request.form.get("discount_amount")

            try:
                # Convert discount_amount to float
                discount_amount = float(discount_amount)

                if discount_type == "percentage":
                    # Check for valid percentage range
                    if discount_amount < 0 or discount_amount > 100:
                        flash("Invalid percentage value. Must be between 0 and 100.", "warning")
                    else:
                        crsr.execute("""UPDATE quote 
                                        SET FinalDiscountPercent = ?, FinalDiscountAmt = ?
                                        WHERE ID = (?);""",
                                        (discount_amount, 0, quote_id))
                        db.commit()
                        flash("Discount Applied", "success")

                elif discount_type == "flat":
                    if discount_amount < 0 :
                        flash("Invalid flat amount. Must be greater than 0.", "warning")
                    else:
                        crsr.execute("""UPDATE quote 
                                        SET FinalDiscountPercent = ?, FinalDiscountAmt = ?
                                        WHERE ID = (?);""",
                                        (0, discount_amount, quote_id))
                        db.commit()
                        flash("Discount Applied", "success")

            except ValueError:
                db.rollback()
                flash("Invalid discount amount. Must be a number.", "warning")
            except:
                db.rollback()
                flash("DATABASE ERROR", "warning") 

        # Handle resetting the discount
        if request.form.get("reset_discount"):
            try:
                # Reset discount values
                crsr.execute("""UPDATE quote 
                                SET FinalDiscountPercent = 0, FinalDiscountAmt = 0
                                WHERE ID = (?);""", (quote_id,))
                db.commit()
                
                # Update the total price in the quote table
                crsr.execute("""UPDATE quote 
                                SET SubTotal = (?)
                                WHERE ID = (?);""", (reset_price, quote_id))

                db.commit()
                flash("Discount reset to 0. Total price recalculated.", "success")
            except:
                db.rollback()
                flash("DATABASE ERROR", "warning")              
        
        # Retrieve discount values
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        discount_values = crsr.fetchone()

        # Calculate the total price after applying the discount
        discounted_price = total_price
        # Apply percentage discount
        percent = discount_values[6] / 100
        discounted_price -= discounted_price * percent
        # Subtract flat amount discount
        discounted_price -= discount_values[7]
        
            
        # Ensure total price is not below 0
        total_price = max(total_price, 0)   

        try:
            crsr.execute("""UPDATE quote 
                            SET SubTotal = (?)
                            WHERE ID = (?);""", (total_price, quote_id))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE ERROR", "warning")

        return render_template("/convert/convertquote.html",
                                quote=quote_data,
                                quote_id=quote_id,
                                discount_values=discount_values,
                                discounted_price=discounted_price)
    else:
        return redirect("/convert")
    
# Convert quote confirm view.
@app.route('/convert/convertconfirm', methods=["GET", "POST"])
@convert_login_required
def convert_quote_confirm():
    quote_id = request.form.get("quote_id")
    if request.method == "POST":
        # Check if the "save_changes" button was clicked
        if "save_changes" in request.form:
            # Handle saving changes logic here
            flash("Changes saved", "success")
            return redirect(f'/convert/convertconfirm')
        
    # If the form was not submitted, retrieve the quote
    db = current_db()
    crsr = db.cursor()
    crsr.execute("SELECT * FROM quote WHERE id = ?", (quote_id,))
    quote = crsr.fetchone()
    crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
    quote_data = crsr.fetchone()
    total_price = quote_data[17]
    discounted_price = total_price

    # Apply percentage discount
    percent = quote[6] / 100
    discounted_price -= discounted_price * percent
    # Subtract flat amount discount
    discounted_price -= quote[7]
    # Save discounted price as total price
    total_price = discounted_price
        
    # Ensure total price is not below 0
    total_price = max(total_price, 0)    

    crsr.execute("""UPDATE quote 
                    SET SubTotal = (?)
                    WHERE ID = (?);""", (total_price, quote_id))
    db.commit()

    crsr.execute("""UPDATE quote
                    SET Ordered = True
                    WHERE ID = (?);""", (quote_id,))
    db.commit()
    
    db.close()

    return render_template("/convert/convertconfirm.html", 
                           quote=quote_data,
                           quote_id=quote_id, 
                           discounted_price=discounted_price)

# Add a new route to get information from EPS
@app.route('/convert/send_eps', methods=["GET", "POST"])
@convert_login_required
def send_eps():
    if request.method == "POST":
        quote_id = request.form.get("quote_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM quote WHERE ID = ?", (quote_id,))
        quote = crsr.fetchone()
        total_price = quote[17]        
        discounted_price = total_price
        # Apply percentage discount
        percent = quote[4] / 100
        discounted_price -= discounted_price * percent
        # Subtract flat amount discount
        discounted_price -= quote[5]

        # Ensure total price is not below 0
        total_price = max(total_price, 0) 


        date_and_commission = send_quote_to_api(quote_id, quote[1], quote[2], total_price)

        commission_rate = date_and_commission["commission"]
        processed_date = date_and_commission["processDay"]
        string_commission = commission_rate[0:len(commission_rate)-1]
        processed_commission = int(string_commission)
        processed_commission = (processed_commission*total_price)/100

        try:
            crsr.execute("""UPDATE quote 
                            SET ProcessDate = (?)
                            WHERE ID = (?);""", (processed_date, quote_id))
            db.commit()

            crsr.execute("""UPDATE quote 
                            SET Commission = (?)
                            WHERE ID = (?);""", (processed_commission, quote_id))
            db.commit()

            crsr.execute("SELECT * FROM associate WHERE EmpID = ?", (quote[1],))
            accumulated_commission = crsr.fetchone()
            processed_commission += accumulated_commission[3]

            crsr.execute("""UPDATE associate 
                            SET AccumCommision = (?)
                            WHERE EmpID = (?);""", (processed_commission, quote[1]))
            db.commit()
            
            crsr.execute("SELECT * FROM lineitems WHERE QuoteID = ?", (quote_id,))
            line_item_rows = crsr.fetchall()

            body_string = "Thank you for your order from CSCI467 group 2b! The details are as follows:\n"
            body_string += "Date Ordered: %s \n" %(quote[11])
            body_string += "Processing Date: %s \n" %(processed_date)
            body_string += "Customer: %s \n" %(quote[13])
            
            body_string += "LINE ITEMS:\n"
            for LI in line_item_rows:
                body_string += "%s -- %s \n" %(LI[1], LI[2])
            
            body_string += "--------------------\n"
            body_string += "TOTAL: %s \n" %(total_price)

            msg = Message("Purchase Order from CSCI467Mart", 
                        sender="CSCI467@NIU.EDU",
                        recipients=[quote[3]],
                        body=body_string)
            mail.send(msg)

            flash("Purchase order sent. Commission and process date saved.", "success")
        except:
            db.rollback()
            flash("DATABASE ERROR", "warning")
        return redirect('/convert')
    else:
        return redirect('/convert')

# Quote conversion logout route
@app.route('/convert/logout')
@convert_login_required
def convert_logout():
    session.clear()
    flash("Logged Out Successfully", "primary")
    return redirect("/convert")
###############################################################################
#                           ADMIN ROUTE                                       #
###############################################################################
# Admin Interface Follows

# Main admin home route
@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin_home():
    if request.method == 'POST':
        pass
    db = current_db()
    crsr = db.cursor()

    crsr.execute("SELECT * FROM Associate")
    associate_data = crsr.fetchall()

    crsr.execute("SELECT ID, date, CustName, FirstName, LastName, CustContact, SubTotal FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID")
    all_quotes = crsr.fetchall()

    db.close()

    return render_template("./admin/home.html", associate_data=associate_data, all_quotes=all_quotes)

# Admin Add Associate route
@app.route('/admin/addassoc', methods=["GET", "POST"])
@admin_login_required
def admin_addassociate():
    return render_template("./admin/addassoc.html")

# Admin Create Associate route
@app.route('/admin/createassoc', methods=["GET", "POST"])
@admin_login_required
def admin_createassociate():
    if request.method == "POST":
        ID = request.form.get("assocID")
        UN = request.form.get("assocUN")
        PS = request.form.get("assocPS")
        AD = request.form.get("assocAD")
        FN = request.form.get("assocFN")
        LN = request.form.get("assocLN")
        PW = generate_password_hash(PS)
    # Create Associate
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("""INSERT INTO Associate 
                         (EmpID, Username, Password, Address, FirstName, LastName) 
                         VALUES (?, ?, ?, ?, ?, ?);""", 
                         (ID, UN, PW, AD, FN, LN))
            db.commit()
        except:
            db.rollback()
            flash("DATABASE INSERT ERROR", "warning")
        
        crsr.execute("SELECT * FROM Associate")
        associate_data = crsr.fetchall()

        crsr.execute("SELECT ID, date, CustName, FirstName, LastName, CustContact, SubTotal FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID")
        all_quotes = crsr.fetchall()

        db.close()

        flash("Associate Added", "primary")
        return render_template("./admin/home.html", associate_data=associate_data, all_quotes=all_quotes)
    else:
        flash("Please insert all new Associate info", "info")
        return render_template("./admin/addassoc.html")

# Admin Confirm Delete Associate Route
@app.route('/admin/delassocconfirm', methods=["GET", "POST"])
@admin_login_required
def admin_del_confirm():
    if request.method == "POST":
        del_id  = request.form.get("del_associate_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM Associate WHERE EmpID = ?", (del_id,))
        associate = crsr.fetchone()
        db.close()
        return render_template("/admin/delassocconfirm.html", 
                               associate=associate)
    else:
        return redirect('/admin')

# Admin Delete Associate Route
@app.route('/admin/delassoc', methods=["GET", "POST"])
@admin_login_required
def admin_del_associate():
    if request.method == "POST":
        del_id = request.form.get("del_assoc_submit")
        db = current_db()
        crsr = db.cursor()
        try:
            crsr.execute("DELETE FROM Associate WHERE EmpID = ?", (del_id,))
            db.commit()
            flash("Deletion Succesful", "primary")
        except:
            db.rollback()
            flash("DATABASE DELETION ERROR", "warning")
        db.close()
        return redirect('/admin')

# Admin Edit Associate Route
@app.route('/admin/editassoc', methods=["GET", "POST"])
@admin_login_required
def admin_edit_associate():
    if request.method == "POST":
        ed_id  = request.form.get("edit_associate_id")
        db = current_db()
        crsr = db.cursor()
        crsr.execute("SELECT * FROM Associate WHERE EmpID = ?", (ed_id,))
        associate = crsr.fetchone()
        db.close()
        return render_template("/admin/editassoc.html", associate=associate)
    else:
        return redirect('/associate')
    
# Admin Edit Associate Entry Route
@app.route('/admin/editassocconfirm', methods=["GET", "POST"])
@admin_login_required
def admin_editing_associate():
    if request.method == "POST":
        assoc_id = request.form.get("edit_assoc_submit")
        db = current_db()
        crsr = db.cursor()
        ID = request.form.get("assocID")
        UN = request.form.get("assocUN")
        PS = request.form.get("assocPS")
        AD = request.form.get("assocAD")
        FN = request.form.get("assocFN")
        LN = request.form.get("assocLN")
        # Edit associate where applicable
        if ID:
            try:
                crsr.execute("""UPDATE Associate SET EmpID = ? WHERE EmpID = ?""", (ID,assoc_id))
                db.commit()
                flash("Updated Associate's ID", "success")
                assoc_id = ID
            except:
                db.rollback()
                flash("Database Error", "warning")
        if UN:
            try:
                crsr.execute("""UPDATE Associate SET Username = ? WHERE EmpID = ?""", (UN,assoc_id))
                db.commit()
                flash("Updated Associate's Username", "success")
            except:
                db.rollback()
                flash("Database Error", "warning")
        if PS:
            try:
                crsr.execute("""UPDATE Associate SET Password = ? WHERE EmpID = ?""", (PS,assoc_id))
                db.commit()
                flash("Updated Associate's Password", "success")
            except:
                db.rollback()
                flash("Database Error", "warning")
        if AD:
            try:
                crsr.execute("""UPDATE Associate SET Address = ? WHERE EmpID = ?""", (AD,assoc_id))
                db.commit()
                flash("Updated Associate's Address", "success")
            except:
                db.rollback()
                flash("Database Error", "warning")
        if FN:
            try:
                crsr.execute("""UPDATE Associate SET FirstName = ? WHERE EmpID = ?""", (FN,assoc_id))
                db.commit()
                flash("Updated Associate's First Name", "success")
            except:
                db.rollback()
                flash("Database Error", "warning")
        if LN:
            try:
                crsr.execute("""UPDATE Associate SET LastName = ? WHERE EmpID = ?""", (LN,assoc_id))
                db.commit()
                flash("Updated Associate's Last Name", "success")
            except:
                db.rollback()
                flash("Database Error", "warning")
        db.close()
        return redirect('/admin')

# Admin Choose Search Filters route
@app.route('/admin/searchquote', methods=["GET", "POST"])
@admin_login_required
def admin_searchquote():
    return render_template("./admin/searchquote.html")

# Admin Search Results route
@app.route('/admin/searchquoteresults', methods=["GET", "POST"])
@admin_login_required
def admin_searchquoteresults():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        afterd = request.form.get("afterdate")
        befored = request.form.get("beforedate")
        search = request.form.get("searchterm")

        aftd = datetime.strptime(afterd, '%Y-%m-%d')
        bfrd = datetime.strptime(befored, '%Y-%m-%d')

        aftd = aftd.strftime("%Y/%m/%d")
        bfrd = bfrd.strftime("%Y/%m/%d")

        search = search + "%"
        
        # Get Search Results
        if request.form.get("status") == "All":
            if request.form.get("person") == "Username":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND Username LIKE ?", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
            elif request.form.get("person") == "CustName":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND CustName LIKE ?", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
        elif request.form.get("status") == "Finalized":
            if request.form.get("person") == "Username":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND Username LIKE ? AND Finalized = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
            elif request.form.get("person") == "CustName":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND CustName LIKE ? AND Finalized = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
        elif request.form.get("status") == "Sanctioned":
            if request.form.get("person") == "Username":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND Username LIKE ? AND Sanctioned = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
            elif request.form.get("person") == "CustName":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND CustName LIKE ? AND Sanctioned = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
        elif request.form.get("status") == "Ordered":
            if request.form.get("person") == "Username":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND Username LIKE ? AND Ordered = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")
            elif request.form.get("person") == "CustName":
                try:
                    crsr.execute("SELECT ID, Date, CustName, FirstName, LastName, CustCity, CustContact, SubTotal, Commission FROM quote INNER JOIN Associate ON quote.AssociateID = Associate.EmpID WHERE Date BETWEEN ? AND ? AND CustName LIKE ? AND Ordered = 1", (aftd,bfrd,search))
                    quotesearch = crsr.fetchall()
                    db.close()
                    return render_template("./admin/searchquoteresults.html", quotesearch=quotesearch)
                except:
                    flash("Search Error", "warning")

    db.close()
    return render_template("./admin/searchquote.html")

# Admin login route
@app.route('/admin/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        db = current_db()
        crsr = db.cursor()
        un = request.form.get("username")
        pw = request.form.get("password")
        crsr.execute("SELECT * FROM adminemployee WHERE username = ?;", (un,))
        rows = crsr.fetchall()
        db.close()
        if len(rows) != 1 or not check_password_hash(rows[0][2], pw):
            flash("Invalid Username or Password", "danger")
            return redirect('/admin/login')
        
        session["admin_id"] = rows[0][0]

        flash("Login Succesful", "primary")
        return redirect('/admin')
    else:
        return render_template("./admin/login.html")

# Admin logout route
@app.route('/admin/logout')
@admin_login_required
def admin_logout():
    session.clear()
    flash("Logged Out Successfully", "primary")
    return redirect("/admin")

###############################################################################
#                            RUN APP                                          #
###############################################################################
# This will have to change when we go live: it works running on localhost  
if __name__ == "__main__":
    app.run()