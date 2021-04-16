import os

import crypto
import sqldb
import datetime

from flask import abort, jsonify, request, Flask, session, redirect, url_for
from flask_session import Session
from datetime import datetime
#from flask_cors import CORS, cross_origin


# TODO(mikolaj): remove static_* parameters for production
app = Flask(__name__, static_url_path='', static_folder='../static')

SESSION_COOKIE_NAME = 'unifier-session'
SESSION_COOKIE_PATH = '/'
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = True

SESSION_TYPE = 'filesystem'

SECRET_KEY = b'\x11\xe7\x18\xbd\xf1\xban&a\x9ap\xa5\xdbc\xb2\xfa'

app.config.from_object(__name__)
#app.config['CORS_HEADERS'] = 'Content-Type'
sess = Session()


@app.route('/')
#@cross_origin()
def main():
    return app.send_static_file('index.html')


# TODO(mikolaj): implement csrf protection
# TODO(daim): implement registration REST end point
@app.route('/api/register', methods=['POST'])
def register():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    email = request.values.get('email', None)
    username = request.values.get('username', None)
    password = request.values.get('password', None)

    if email is None or username is None or password is None:
        return app.response_class(status=400)

    query = 'SELECT * FROM UserAuth WHERE username LIKE ? OR email LIKE ?;'
    parameters = (username, email)
    existing_user = sqldb.do_sql(cur, query, parameters)

    if existing_user is not None:
        print(f'Username/email already exists!')
        return app.response_class(status=400)

    print(f'Registering user: {username} ({email}) with password {password}')

    query = 'INSERT INTO UserAuth (username, email, hash, salt) VALUES (?,?,?,?,?);'
    parameters = (username, email, *crypto.hash_secret(password))
    sqldb.do_sql(cur, query, parameters)

    print(f'Succesfuly registered user: {username} ({email})')

    return app.response_class(status=200)


# TODO(mikolaj): implement csrf protection
@app.route('/api/login', methods=['POST'])
def login():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    username = request.values.get('username', None)
    password = request.values.get('password', None)

    if username is None or password is None:
        return app.response_class(status=400)

    query = 'SELECT userId, hash, salt FROM UserAuth WHERE username LIKE ?;'
    parameters = (username,)
    matching_users = sqldb.do_sql(cur, query, parameters)

    for uid, user_hash, user_salt in matching_users:
        if crypto.verify_secret(password, user_hash, user_salt):
            session['uid'] = uid
            return app.response_class(status=200)

    return app.response_class(status=401)


# TODO(mikolaj): implement csrf protection
@app.route('/api/logout', methods=['POST'])
def logout():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid', None)

    if uid is None:
        return app.response_class(status=400)

    session.pop('uid')

    print(f'[user-{uid}] Logged out!')
    redirect('/')

    return app.response_class(status=200)


@app.route('/api/readProfile', methods=['GET'])
def read_profile():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid')

    query = '''SELECT * FROM Users
    WHERE id LIKE ?;'''
    parameters = (uid,)
    user_profile = sqldb.do_sql(cur, query, parameters)[0]
    uid, name, dob, gender, bio, picture_id = user_profile

    query = '''SELECT data FROM UserPictures
    WHERE id LIKE ?;'''
    parameters = (picture_id,)
    picture = sqldb.do_sql(cur, query, parameters)[0][0]

    query = '''SELECT interestId FROM UsersInterestsJoin 
    INNER JOIN Users ON UsersInterestsJoin.userId = Users.id 
    INNER JOIN Interests ON UsersInterestsJoin.interestId = Interests.id 
    WHERE userId LIKE ?;'''
    parameters = (uid,)
    interests = sqldb.do_sql(cur, query, parameters)
    
    query = 'SELECT name FROM Interests WHERE id LIKE ?;'
    interest_names = [None] * len(interests)
    for idx, interest in enumerate(interests):
        interest_names[idx] = sqldb.do_sql(cur, query, interest)

    return jsonify({
        'uid': uid,
        'username': name,
        'dob': dob,
        'gender': gender,
        'biography': bio,
        'picture': 1,
        'interests': interest_names,
    })


#update interests left to do
@app.route('/api/updateProfile', methods=['GET'])
def update_profile():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = request.values.get('uid')
    name = request.values.get('name')
    dob = user.values.get('dob')
    interests = request.values.get('interests')
    biography = request.values.get('biography')
    gender = request.values.get('gender')
    profilePicture = request.values.get('profilePicture')

    interests_list = interests.split(',')

    user_exist = sqldb.do_sql(cur, 'SELECT * FROM Users WHERE id LIKE ?;', uid)

    if user_exist is None:
        query = 'INSERT INTO Users (id, name, dob, gender, bio) VALUES (?,?,?,?,?);'
        parameters = (uid, name, dob, gender, biography)
        cur.execute(query, parameters)

        query = 'INSERT INTO UserPictures(data) VALUES (?);'
        parameters = (profilePicture,)
        cur.execute(query, parameters)

        for interest in interests_list:
            interest_id = sqldb.get_interest_id(interest)
            query_interest = 'INSERT INTO UsersInterestsJoin (userId, interestId) VALUES (?,?);'
            do_sql(cur, query_interest, (uid, interest_id))

    else: 
        query = 'UPDATE Users SET bio = ?, gender = ? WHERE id LIKE ?;'
        parameters = (biography, gender, uid)
        cur.execute(query, parameters)

        query = 'SELECT pictureId FROM Users WHERE id LIKE ?;'
        parameters = (uid,)
        cur.execute(query, parameters)
        picId = cur.fetchone()

        query = '''UPDATE UserPictures SET data = ? 
        INNER JOIN Users ON UserPictures.id = Users.pictureId 
        WHERE id LIKE ?;'''

        parameters = (profilePicture, picId)
        cur.execute(query, parameters)

        for interest in interest_list:
            interest_id = sqldb.get_interest_id(interest)
            existing_interests = do_sql(cur, 'SELECT interestId FROM UsersInterestsJoin WHERE userId LIKE ?;', (uid,))
            if (interest in existing_interests):
                continue;
            else:
                query_interest = 'INSERT INTO UsersInterestsJoin (userId, interestId) VALUES (?,?);'
                do_sql(cur, query_interest, (uid, interest_id))

    return app.response_class(status=200)


@app.route('/api/startConversation', methods=['POST'])
def start_conversation():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid')
    other_uid = request.values.get('other')

    query = '''SELECT conversationId FROM UsersConversationsJoin
    INNER JOIN Users ON UsersConversationsJoin.userId = Users.id
    WHERE userId LIKE ?;'''
    parameters = (uid,)
    result = sqldb.do_sql(cur, query, parameters)

    if result is None:
        # TODO(mikolaj): fixme - invalid insert with too few values
        query = '''INSERT INTO Conversations VALUES (?);'''
        parameters = ('',)
        new_conversation = sqldb.do_sql(cur, query, parameters)
        print(new_conversation)

        return app.response_class(200)


    print(result)
    session['cid'] = result[0]

    return app.response_class(status=200)


@app.route('/api/stopConversation', methods=['POST'])
def stop_conversation():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid')
    cid = session.get('cid', None)

    if cid is None:
        return app.response_class(status=200)

    session.pop('cid')

    return app.response_class(status=200)


@app.route('/api/sendMessage', methods=['POST'])
def send_message():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid')
    cid = session.get('cid')
    message = request.values.get('message')
    date_time = datetime.utcnow()

    query = '''SELECT conversationId FROM UsersConversationsJoin 
    INNER JOIN Users ON UsersConversationsJoin.userId = Users.id 
    WHERE userId LIKE ? AND converstaionId LIKE ?;'''

    parameters = (uid, cid)
    convoValidation = sqldb.do_sql(cur, query, parameters)

    if convoValidation is None:
        print(f'User does not have access to this conversation!')
        return app.response_class(status=400)

    query = '''SELECT fpath FROM Conversations 
    INNER JOIN UsersConversationsJoin ON UsersConversationsJoin.converstaionId = Conversations.id 
    WHERE id LIKE ?;'''

    parameters = (cid,)
    cur.execute(query, parameters)
    fpath = cur.fetchone()

    conversations.write_message(fpath, date_time, uid, message)
    return app.response_class(status=200)


@app.route('/api/fetchMessages', methods=['GET'])
def fetch_messages():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    uid = session.get('uid')
    cid = session.get('cid')
    from_date = request.values.get('fromDate')

    query = '''SELECT fpath FROM UsersConversationsJoin 
    INNER JOIN Users ON UsersConversationsJoin.userId = Users.id 
    INNER JOIN Conversations ON UsersConversationsJoin.conversationId = Conversations.id
    WHERE userId LIKE ? AND conversationId LIKE ?;'''
    parameters = (uid, cid)
    conversation = sqldb.do_sql(cur, query, parameters)

    if conversation is None:
        return app.response_class(status=400)

    months = {
        'January': 1,
        'February': 2,
        'March': 3,
        'April': 4,
        'May': 5,
        'June': 6,
        'July': 7,
        'August': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12,
    }

    try:
        from_day, from_month, from_year = from_date.split(' ')
        from_date = datetime.date(from_year, months[from_month], from_day)

        msgs_to_read = conversations.read_messages(fpath, from_date)
        print(msgs_to_read)

        return jsonify([{'timestamp': t[0], 'datestamp': t[1], 'content': t[2], 'isLocal': t[3] == uid} for t in msgs_to_read])
    except:
        return app.response_class(status=400)


@app.route('/api/interests', methods = ['GET'])
def fetch_all_interests():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()

    query = '''SELECT name FROM Interests;'''
    all_interests = sqldb.do_sql(cur, query)

    return jsonify([tup[0] for tup in all_interests])


@app.route('/api/friends', methods = ['GET'])
def fetch_all_friends():
    conn = sqldb.try_open_conn()
    assert conn is not None
    cur = conn.cursor()   

    uid = session.get('uid')

    query = '''SELECT conversationId FROM UsersConversationsJoin
    WHERE userId LIKE ?;'''
    parameters = (uid,)
    conversations = sqldb.do_sql(cur, query, parameters)
    print(conversations)

    if conversations is None:
        return []

    friend_ids = []

    query = '''SELECT userId FROM UsesConversationsJoin
    WHERE userId <> ? AND conversationId LIKE ?;'''

    for idx, conversation_id in enumerate(conversations):
        parameters = (uid, conversation_id)
        friend = sqldb.do_sql(cur, query, parameters)
        friend_ids.append(friend)

    print(friend_ids)

    return jsonify(friend_ids)

