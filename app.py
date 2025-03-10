from flask import Flask, render_template, request, jsonify
import re
from datetime import datetime
import pymysql as mysql

app = Flask(__name__)

import re
from word2number import w2n

def convert_hindi_words_to_numbers(text):
    """
    Converts Hindi number words (like "chaubees") to digits (like "24").
    Uses `word2number` to intelligently convert numbers written as words.
    """
    try:
        # Split the text into words
        words = text.lower().split()
        converted_text = []
        temp_phrase = []

        for word in words:
            temp_phrase.append(word)
            try:
                # Try converting the phrase to a number
                num = w2n.word_to_num(" ".join(temp_phrase))
                converted_text.append(str(num))  # Replace words with numeric digits
                temp_phrase = []  # Reset after conversion
            except ValueError:
                continue  # Keep adding words until we detect a number

        # Add remaining words that couldn't be converted
        if temp_phrase:
            converted_text.extend(temp_phrase)

        return " ".join(converted_text)

    except Exception as e:
        pass

def extract_data(text):
    """
    Extracts date, shift (morning/evening), and amount from the provided text.
    Expected format:
      - Date: "24 March" -> Converted to "24-03-2025"
      - Shift: "subah" (morning) / "shaam" (evening)
      - Amount: "289.97"
    """
    date = None
    shift = None
    amount = None

    list_of_words = text.split()
    for word in list_of_words:
        digit=convert_hindi_words_to_numbers(word)
        if digit:
            text=text.replace(word,digit)
    text=" ".join(list_of_words)


    # Dictionary to convert Hindi month names to numerical format
    month_map = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    # Extract date pattern (e.g., "24 March" or "24 march")
    date_pattern = re.search(r'(\d{1,2})\s+([A-Za-z]+)', text, re.IGNORECASE)
    if date_pattern:
        day = date_pattern.group(1)
        month_name = date_pattern.group(2).lower()

        if month_name in month_map:
            month = month_map[month_name]
            year = datetime.now().year  # Assume current year
            date = f"{year}-{month}-{day}"  # New format: YYYY-MM-DD

    # Extract shift: "subah" (morning) or "shaam" (evening)
    if "subah" in text.lower():
        shift = "morning"
    elif "shaam" in text.lower() or "sham" in text.lower():
        shift = "evening"

    # Extract amount (supports decimal values)
    amount_pattern = re.search(r'(\d+\.\d+)', text)
    if amount_pattern:
        amount = amount_pattern.group(1)

    if date and shift and amount:
        cn=mysql.connect(host='localhost',user
='root',password="admin",database='hisab2')
        cr=cn.cursor()
        cr.execute("create table if not exists money(date date,shift varchar(10),amount float(5,2));")
        cn.commit()
        cr.execute("insert into money values(%s,%s,%s);",(date,shift,amount))
        cn.commit()
        cn.close()
        

    return date, shift, amount


@app.route('/select_month', methods=['GET', 'POST'])
def select_month():
    total_value = None  # Placeholder for total value
    data_table = []  # Placeholder for nested tuple

    if request.method == 'POST':
        selected_month = request.form['month']
        if len(selected_month) == 1:
            selected_month = "0" + selected_month
        cn=mysql.connect(host='localhost',user
='root',password="admin",database='hisab2')
        cr=cn.cursor()
        cr.execute("select * from money where date like '{}';".format("%"+selected_month+'-__'))
        data_table=list(cr.fetchall())
        cr.execute("select sum(amount) from money where date like '{}';".format("%"+selected_month+'%'))
        total_value=cr.fetchone()[0]
        cr.execute("update money set amount=500 where date like '{}';".format("_____"+selected_month+'%'))
        cn.commit()
        cn.close()

        return render_template('select_month.html', total=total_value, data=data_table, selected_month=selected_month)

    return render_template('select_month.html', total=None, data=None, selected_month=None)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    text = data.get('text', '')
    date, shift, price = extract_data(text)
    return jsonify({
        'date': date,
        'shift': shift,
        'price': price,
        'original_text': text
    })

if __name__ == '__main__':
    app.run(debug=True)
