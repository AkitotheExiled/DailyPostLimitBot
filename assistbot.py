import praw
import sqlite3
import requests
from datetime import datetime
from datetime import date
from configparser import ConfigParser
import time
class Ab_Bot():

    def __init__(self):
        self.user_agent = "AssistBot V0.1 by ScoopJr"
        print('Starting up...', self.user_agent)
        CONFIG = ConfigParser()
        CONFIG.read('config.ini')
        self.user = CONFIG.get('main', 'USER')
        self.password = CONFIG.get('main', 'PASSWORD')
        self.client = CONFIG.get('main', 'CLIENT_ID')
        self.secret = CONFIG.get('main', 'SECRET')
        self.subreddit = CONFIG.get('main', 'SUBREDDIT')
        self.token_url = "https://www.reddit.com/api/v1/access_token"
        self.token = ""
        self.t_type = ""
        self.reddit = praw.Reddit(client_id=self.client,
                                  client_secret=self.secret,
                                  password=self.password,
                                  user_agent=self.user_agent,
                                  username=self.user)
        self.db = sqlite3.connect('user_database.sqlite')
        self.cursor = self.db.cursor()
        self.need_date = False
        self.read_date = None
        self.daily_limit = int(CONFIG.get('main', 'DAILY_LIMIT'))
        self.create_table_for_users()
        self.create_table_for_postid()
        try:
            with open('date_of_bot_ran.txt', 'r') as f:
                self.read_date = datetime.date(datetime.strptime(f.read(), '%Y-%m-%d'))
            f.close()
        except Exception as e:
            print(e)
            self.need_date = True
        print(self.read_date, self.read_date < date.today())
        if self.need_date or self.read_date < date.today():
            if self.read_date < date.today():
                self.reset_users_post_count()
            try:
                with open('date_of_bot_ran.txt', 'w+') as f:
                    f.write(str(date.today()))
                f.close()
            except Exception as e:
                print(e)

    def get_token(self):
        """ Retrieves token for Reddit API."""
        client_auth = requests.auth.HTTPBasicAuth(self.client, self.secret)
        post_data = {'grant_type': 'password', 'username': self.user, 'password': self.password}
        headers = {'User-Agent': self.user_agent}
        response = requests.Session()
        response2 = response.post(self.token_url, auth=client_auth, data=post_data, headers=headers)
        self.token = response2.json()['access_token']
        self.t_type = response2.json()['token_type']

    def check_if_user_exists(self, name):
        try:
            query = "SELECT username FROM Users WHERE username='{}'".format(name.lower())
            self.cursor.execute(query)
        except sqlite3.OperationalError as e:
            print(e)
            return None
        else:
            return self.cursor.fetchall()

    def create_table_for_users(self):
        query = "CREATE TABLE IF NOT EXISTS Users ( UserID INTEGER PRIMARY KEY, username TEXT UNIQUE, posts INTEGER DEFAULT 0) "
        self.cursor.execute(query)
        return print('User table has been created!')

    def create_table_for_postid(self):
        query = "CREATE TABLE IF NOT EXISTS Posts ( UserID INTEGER NOT NULL, PostID INTEGER PRIMARY KEY, PostTxt TEXT NOT NULL, FOREIGN KEY (UserID) REFERENCES Users(UserID))"
        self.cursor.execute(query)
        self.db.commit()
        return print('PostID Table Created')

    def insert_user_into_db(self, user):
        query = "INSERT INTO Users (username) VALUES ('{}')".format(str(user.lower()))
        self.cursor.execute(query)
        self.db.commit()
        return print(user,'has been inserted into the database.')

    def update_user_data(self, user, count, id):
        query = "UPDATE Users SET posts={} WHERE username='{}'".format(count, user.lower())
        user_id = self.query_userid(user)
        query2 = "INSERT INTO Posts (UserID, PostTxt) Values({},'{}')".format(user_id[0][0], id)
        self.cursor.execute(query)
        self.cursor.execute(query2)
        self.db.commit()
        return print(f'{user} information has been updated.')

    def query_userid(self,user):
        query = "SELECT UserID FROM Users WHERE username='{}'".format(user.lower())
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def query_user_posts(self, user):
        query = "SELECT posts FROM Users WHERE username='{}'".format(user.lower())
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def query_user_postid(self, user):
        user_id = self.query_userid(user)
        query = "SELECT PostTxt FROM Posts WHERE UserID={}".format(user_id[0][0])
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def reset_users_post_count(self):
        query = "UPDATE Users SET posts=0, counted_posts=''"
        query2 = "DELETE FROM Posts;"
        self.cursor.execute(query)
        self.cursor.execute(query2)
        self.db.commit()
        return print('All users have had their posts reset.')

    def close_db(self):
        self.db.close()
        return print('Database has been closed.')

    def bot_norm_op(self):
        for post in self.reddit.subreddit(self.subreddit).stream.submissions():
            post_time = datetime.utcfromtimestamp(int(post.created_utc)).strftime('%Y-%m-%d')
            post_time = date.fromisoformat(post_time)
            if post.archived or post.locked:
                continue
            if post_time < date.today():
                continue
            else:
                exist_check = self.check_if_user_exists(post.author.name)
                if exist_check:
                    og_count = self.query_user_posts(post.author.name)
                    posts_id = self.query_user_postid(post.author.name)
                    to_break = False
                    to_delete = False
                    if posts_id:
                        for post_info in posts_id:
                            if post.id in post_info:
                                to_break = True
                                break
                            if (og_count[0][0] >= self.daily_limit) and (post.id not in post_info):
                                to_delete = True
                                break
                        if to_break:
                            continue
                        if to_delete:
                            print(post.author.name, ', Their post, ' + str(post.id) + ', will not be removed for exceeding the daily limit.')
                            self.reddit.submission(post.id).mod.remove(mod_note="This user has exceeded their daily post limit.")
                        else:
                            new_ct = og_count[0][0]
                            new_ct += 1
                            self.update_user_data(post.author.name, new_ct, post.id)
                    else:
                        new_ct = og_count[0][0]
                        new_ct +=1
                        self.update_user_data(post.author.name,new_ct, post.id)
                        time.sleep(2)
                else:
                    self.insert_user_into_db(post.author.name)



if __name__ == '__main__':
    bot = Ab_Bot()
    bot.bot_norm_op()