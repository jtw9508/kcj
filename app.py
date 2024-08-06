from flask import Flask, render_template, request, url_for, redirect, g, jsonify,Response
from pymongo import MongoClient
from bson import ObjectId
import hashlib
import datetime
import jwt
from functools  import wraps
import random

app = Flask(__name__)

# LOAD .env FILE
from dotenv import load_dotenv
load_dotenv()

import os
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

client = MongoClient(CLIENT_ID)
db = client.kcj

def login_required(f):      									
    @wraps(f)                   								
    def decorated_function(*args, **kwargs):					
        access_token = request.cookies.get('mytoken') 	
        if access_token is not None:  							
            try:
                payload = jwt.decode(access_token, SECRET_KEY, 'HS256') 				   
            except jwt.InvalidTokenError:
                payload = None     							

            if payload is None: return Response(status=401)  	

            user_id   = payload['id']
            user_name = payload['username']  					
            g.user_id = user_id
            g.user_name = user_name
        else:
            return Response(status = 401)  						

        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
# @is_logined
def index():
    access_token = request.cookies.get('mytoken')

    if access_token:
        is_login = True
        try:
            payload = jwt.decode(access_token, SECRET_KEY, 'HS256')
            user_name = payload['username']
        except jwt.ExpiredSignatureError: ##기한이 만료된 경우 
            is_login = False
            user_name = '로그인해주세요'
            # return render_template('index.html', is_login = is_login, user_name = user_name)
        
    else:
        is_login = False
        user_name = '로그인해주세요'
    # ObjectID string 으로 변환
    def convert_objectid_to_str(doc):
        if isinstance(doc, dict):
            for key, value in doc.items():
                if isinstance(value, ObjectId):
                    doc[key] = str(value)
                elif isinstance(value, (dict, list)):
                    convert_objectid_to_str(value)
        elif isinstance(doc, list):
            for item in doc:
                convert_objectid_to_str(item)
        return doc
    cards = list(db.cards.find({}))

    return render_template('index.html', cards = cards, is_login = is_login, user_name = user_name)

@app.route('/loginpage', methods = ['GET'])
def loginpage():
    return render_template('signin.html')

@app.route('/signuppage', methods = ['GET'])
def signuppage():
    return render_template('signup.html')

# CREATE CARD
@app.route('/add', methods=['POST'])
def add():
    context = request.form['card-context']
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload['username']
    card = {'author': username, 'context': context}
    db.cards.insert_one(card)
    return redirect(url_for('index'))

# EDIT CARD
@app.route('/edit/<string:id>', methods=['GET', 'POST'])
def edit(id):
    if request.method == 'POST':
        context = request.form['modified-context']
        db.cards.update_one({'_id': ObjectId(id)}, {'$set': {'context': context}})
        return redirect(url_for('index'))
    card = db.cards.find_one({'_id': ObjectId(id)})
    return render_template('edit.html', id=id, card=card)

# DELETE CARD
@app.route('/delete/<string:id>')
def delete(id):
    db.cards.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))


@app.route('/signup', methods = ['POST'])
def signup():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    print(pw_receive)
    print(pw_hash)

    # 이미 존재하는 아이디면 패스!
    result = db.user.find_one({'ID': id_receive})
    if result is not None:
        return jsonify({'result': 'fail', 'msg': '이미 존재하는 ID입니다!'})
    else:
        db.user.insert_one({'ID': id_receive, 'PW': pw_hash, 'NICK': nickname_receive})
        return jsonify({'result': 'success'})

@app.route('/login', methods = ['POST'])
def login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    print(pw_receive)
    print()
    print(pw_hash)
    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'ID': id_receive, 'PW': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰 생성
        payload = {
            'id': id_receive,
            'username': result['NICK'], #작성자 기록
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=100)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') #.decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    pass

@app.route('/logout', methods = ['POST'])
def logout():
    return render_template('index.html')

@app.route('/mypage', methods = ['POST'])
@login_required
def get_mypage():
    my_post = db.card.find_all({'author':user_name}) ##user_id(또는 user_name)을 이용해서 user가 남긴 질문을 모두 가져온다.
    my_reply = db.comment.find_all({'author':user_name}) ##user_id(또는 user_name)을 이용해서 user가 남긴 댓글을 모두 가져온다.
    return render_template('my_page.html')


if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)