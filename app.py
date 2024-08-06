from flask import Flask, render_template, request, url_for, redirect, jsonify
from pymongo import MongoClient
from bson import ObjectId
import hashlib
import datetime
import jwt

app = Flask(__name__)

# LOAD .env FILE
from dotenv import load_dotenv
load_dotenv()

import os
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

client = MongoClient(CLIENT_ID)
db = client.kcj

# MAIN & READ CARD
@app.route('/')
def index():
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
    cards = [convert_objectid_to_str(card) for card in cards]

    return render_template('index.html', cards=cards)

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
    result = db.user.find_one({'id': id_receive})
    if result is not None:
        return jsonify({'result': 'fail', 'msg': '이미 존재하는 ID입니다!'})
    else:
        db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive})
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
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰 생성
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=100)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') #.decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    pass

@app.route('/isAuth', methods=['GET'])
def api_valid():
    token_receive = request.cookies.get('mytoken')
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'nickname': userinfo['nick']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)