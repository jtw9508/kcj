from flask import Flask, render_template, request, url_for, redirect, g, jsonify, Response
from pymongo import MongoClient
from bson import ObjectId
import hashlib
import datetime
import jwt
from functools  import wraps

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
        access_token = request.headers.get('Authorization') 	
        if access_token is not None:  							
            try:
                payload = jwt.decode(access_token, SECRET_KEY, 'HS256') 				   
            except jwt.InvalidTokenError:
                payload = None     							

            if payload is None: return Response(status=401)  	

            user_id   = payload['id']
            user_nick = payload['NICK']  					
            g.user_id = user_id
            g.user_nick = user_nick
        else:
            return Response(status = 401)  						

        return f(*args, **kwargs)
    return decorated_function

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
    return render_template('index.html', cards=cards)

# CREATE CARD
@app.route('/add', methods=['POST'])
@login_required
def add():
    context = request.form['card-context']
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload['nickname']
    card = {'author': username, 'context': context}
    db.cards.insert_one(card)
    return redirect(url_for('index'))

# EDIT CARD
@app.route('/edit/<string:id>', methods=['GET', 'POST'])
@login_required
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

# READ COMMENT
@app.route('/comment/<string:id>', methods=['GET'])
def get_comment(id):
    comments = list(db.comments.find({'card_id' : id}))
    return jsonify(comments)

# CREATE COMMENT
@app.route('/comment/<string:id>', methods=['POST'])
def add_comment(id):
    context = request.form['comment-context']
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload['nickname']
    comment = {'author': username, 'card_id': id, 'context': context}
    db.cards.insert_one(comment)
    return jsonify({"status": "success"})

# EDIT COMMENT
@app.route('/memos/<int:id>', methods=['PUT'])
def edit_comment(id):
    memos[id] = request.json['memo']
    return jsonify({"status": "success"})

# DELETE COMMENT
@app.route('/comment/<int:id>', methods=['DELETE'])
def delete_comment(id):
    memos.pop(id)
    return jsonify({"status": "success"})



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
            'nickname': result['NICK'], #작성자 기록
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=100)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') #.decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    pass

@app.route('/mypage', methods = ['POST'])
@login_required
def get_mypage():
    pass  


if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)