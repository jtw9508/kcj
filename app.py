from flask import Flask, render_template, request, url_for, redirect, g, jsonify, Response
from pymongo import MongoClient
from bson import ObjectId
import hashlib
import datetime
import jwt
from functools  import wraps
import math
import time

app = Flask(__name__)

# LOAD .env FILE
from dotenv import load_dotenv
load_dotenv()

import os
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

client = MongoClient(CLIENT_ID)
db = client.kcj

##한국 시간 + 초 단위로 시간 측정
def convert_to_korea_time(time_str):    
    # 9시간을 더하여 한국 시간으로 변환
    korea_time_obj = time_str + datetime.timedelta(hours=9)
    
    # 변환된 시간을 문자열로 변환 (원하는 형식으로)
    korea_time_str = korea_time_obj.strftime('%Y-%m-%d %H:%M:%S')

    return korea_time_str

# 게시물, 댓글 시간 변환 함수
def convert_time(time):    
    ##현재 시간 unix시간 초 단위로 변환
    now_time = datetime.datetime.utcnow()    
    time_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
    time_obj = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    millis = int(time_obj.timestamp())    

    ##게시물시간 unix시간 초 단위로 변환
    time_str_post = time.strftime('%Y-%m-%d %H:%M:%S')
    time_obj_post = datetime.datetime.strptime(time_str_post, '%Y-%m-%d %H:%M:%S')
    fd_time = int(time_obj_post.timestamp())

    me_time = math.floor(((millis - fd_time)/60))
    me_timehour = math.floor((me_time/60))
    me_timeday = math.floor((me_timehour/24))
    me_timeyear = math.floor(me_timeday / 365)

    if me_time < 1 :
        a = '방금 전'
        
    elif me_time < 60 :
        a = str(me_time) + '분 전'
        
    elif me_timehour < 24 :
        a = str(me_timehour) + '시간 전'
    
    elif me_timeday < 365 :
        a = str(me_timeday) + '일 전'
    
    elif me_timeyear >= 1 : 
        a = str(me_timeyear) + '년 전'
    return a

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

def is_logined(access_token):
    if access_token:
        is_login = True
        try:
            payload = jwt.decode(access_token, SECRET_KEY, 'HS256')
            print(payload)
            user_name = payload['username']
        except jwt.ExpiredSignatureError: ##기한이 만료된 경우 
            is_login = False
            user_name = '로그인해주세요'
            return is_login, user_name, {'username':''}
        
    else:
        is_login = False
        user_name = '로그인해주세요'
        payload = {'username':''}
    return is_login, user_name, payload

# MAIN & READ CARD
@app.route('/')
def index():
    access_token = request.cookies.get('mytoken')
    print(type(access_token))
    # payload = jwt.decode(access_token, SECRET_KEY, 'HS256')
    
    is_login, user_name, payload = is_logined(access_token)
    print(payload)
    print(user_name, is_login)

    cards = list(db.cards.find({}))
    new_cards = []
    for card in cards:
        try:
            if card['author'] == payload['username']:
                card['canrevise'] = 'ok'
            else:
                card['canrevise'] = 'no'
        except:
            card['canrevise'] = 'no'

        card['time_convert'] = convert_time(card['time'])
        new_cards.append(card)
    cards = sorted(new_cards, key = lambda new_cards: new_cards['time'], reverse=True)
    print(user_name)
    return render_template('index.html', cards = cards, is_login = is_login, user_name = user_name)

@app.route('/loginpage', methods = ['GET'])
def loginpage():
    return render_template('signin.html')

@app.route('/signuppage', methods = ['GET'])
def signuppage():
    return render_template('signup.html')
    return render_template('index.html', cards=cards)

# CREATE CARD
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        context = request.form['card-context']
        token_receive = request.cookies.get('mytoken')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload['username']
        card = {'author': username, 'context': context, 'time': datetime.datetime.utcnow()}
        db.cards.insert_one(card)
        return redirect(url_for('index'))
    return render_template('create-card.html')

# EDIT CARD
@app.route('/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if request.method == 'POST':
        context = request.form['modified-context']
        db.cards.update_one({'_id': ObjectId(id)}, {'$set': {'context': context}})
        return redirect(url_for('index'))
    card = db.cards.find_one({'_id': ObjectId(id)})
    return render_template('edit-card.html', id=id, card=card)

# DELETE CARD WITH COMMENT
@app.route('/delete/<string:id>')
def delete(id):
    db.cards.delete_one({'_id': ObjectId(id)})
    db.comments.delete_many({'card_id': id})
    return redirect(url_for('index'))

# DETAIL & READ COMMENT & CREATE COMMENT
@app.route('/detail/<string:id>', methods=['GET', 'POST'])
@login_required
def detail(id):
    if request.method == 'POST':
        context = request.form['comment-context']
        token_receive = request.cookies.get('mytoken')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload['username']
        comment = {'author': username, 'card_id': id, 'context': context, 'time': datetime.datetime.utcnow()}
        db.comments.insert_one(comment)
        return redirect(url_for('detail', id=id))
    card = db.cards.find_one({'_id': ObjectId(id)})
    comments = list(db.comments.find({'card_id' : id}))
    new_comments = []
    for comment in comments:
        try:
            if comment['author'] == payload['username']:
                comment['canrevise'] = 'ok'
            else:
                comment['canrevise'] = 'no'
        except:
            comment['canrevise'] = 'no'

        comment['time_convert'] = convert_time(comment['time'])
        new_comments.append(card)
    comments = sorted(new_comments, key = lambda new_comments: new_comments['time'], reverse=True)

    return render_template('detail.html', id=id, card=card, comments=comments)

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
    username = payload['username']
    comment = {'author': username, 'card_id': id, 'context': context, 'time': datetime.datetime.utcnow()}
    db.cards.insert_one(comment)
    return jsonify({"status": "success"})

# EDIT COMMENT
@app.route('/comment/edit/<string:card_id>/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_comment(card_id, id):
    if request.method == 'POST':
        context = request.form['modified-comment']
        db.comments.update_one({'_id': ObjectId(id)}, {'$set': {'context': context}})
        return redirect(url_for('detail', id=card_id))
    comment = db.comments.find_one({'_id': ObjectId(id)})
    return render_template('edit-comment.html', card_id=card_id, id=id, comment=comment)

# DELETE COMMENT
@app.route('/comment/delete/<string:card_id>/<string:id>', methods=['GET'])
def delete_comment(card_id ,id):
    db.comments.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('detail', id=card_id))


# SIGNUP API
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
        db.user.insert_one({'ID': id_receive, 'PW': pw_hash, 'username': nickname_receive})
        return jsonify({'result': 'success'})

## LOGIN API
@app.route('/login', methods = ['POST'])
def login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'ID': id_receive, 'PW': pw_hash})
    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰 생성
        payload = {
            'id': id_receive,
            'username': result['username'], #작성자 기록
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=10000)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') #.decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    pass


#logout
@app.route('/logout', methods = ['POST'])
def logout():
    return render_template('index.html')

## MYPAGE API(내 포스트와 댓글들을 가져와서 화면에 보여주기)
@app.route('/mypage/<id>', methods = ['GET'])
@login_required
def get_mypage(id):
    access_token = request.cookies.get('mytoken')
    is_login, user_name, payload = is_logined(access_token)
    user_name = payload['username']
    print(payload)
    print(user_name)
    cards = list(db.cards.find({'author':user_name})) ##user_id(또는 user_name)을 이용해서 user가 남긴 질문을 모두 가져온다.
    print(cards)
    new_cards = []
    for card in cards:
        # try:
        #     if card['author'] == payload['username']:
        #         card['canrevise'] = 'ok'
        #     else:
        #         card['canrevise'] = 'no'
        # except:
        #     card['canrevise'] = 'no'

        card['time_convert'] = convert_time(card['time'])
        new_cards.append(card)
    cards = sorted(new_cards, key = lambda new_cards: new_cards['time'], reverse=True)

    # for card in cards:

    comments = list(db.comments.find({'author':user_name})) ##user_id(또는 user_name)을 이용해서 user가 남긴 댓글을 모두 가져온다.
    return render_template('mypage.html', cards = cards, comments = comments, is_login = is_login, user_name = user_name)


if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)