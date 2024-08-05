from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient
import random

app = Flask(__name__)


# LOAD .env FILE
from dotenv import load_dotenv
load_dotenv()

import os
CLIENT_ID = os.getenv("CLIENT_ID")

client = MongoClient(CLIENT_ID)
db = client.kcj

# MAIN & READ CARD
@app.route('/')
def index():
    cards = list(db.cards.find({}))
    card = random.choice(cards)
    return render_template('index.html', card=card)

# CREATE CARD
# @app.route('/add', methods=['POST'])
# def add():
#     card = request.form['card']
#     return redirect(url_for('index'))



if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)