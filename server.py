#!/usr/bin/env python

"""
Columbia's COMS W4111.003 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@104.196.152.219/proj1part2
#
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.152.219/proj1part2"
#
DATABASEURI = "postgresql://yl4875:5056@35.196.73.133/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/')
def platform():
    platform = g.conn.execute("SELECT * FROM Platforms")
    platform_objs = []
    for result in platform:
        platform_obj = {
        "pid": result['pid'],
        "pname": result['pname'],
        "license": result['license']
        }
        platform_objs.append(platform_obj)  # can also be accessed using result[0]
    platform.close()
    
    context = dict(data = platform_objs)
    return render_template("platform.html", **context)

@app.route('/login/<pid>')
def login_with_platform(pid):
    platform = g.conn.execute(f'SELECT * FROM Platforms WHERE pid={pid}')
    platform_objs = []
    for result in platform:
        platform_obj = {
          "pid": result['pid'],
          "pname": result['pname'],
          "license": result['license']
        }
        platform_objs.append(platform_obj)  # can also be accessed using result[0]
    platform.close()
    return render_template("login.html", platform_objs = platform_objs)

@app.route('/user', methods=['POST'])
def user_page():
    contact = request.form.get('contact')
    user = g.conn.execute(f'SELECT * FROM Users')
    current_user = None
    current_membership = None
    for result in user:
        if(result['ucontact']==contact):
            current_user = {
                "user_id": result['user_id'],
                "name": result['name'],
                "ucontact": result['ucontact'],
                "upay": result['upay']
            }
    membership = g.conn.execute(f'SELECT * FROM Memberships JOIN Has ON Memberships.mid=Has.mid JOIN Monitors ON Monitors.mid=Has.mid JOIN Platforms ON Monitors.pid=Platforms.pid AND Has.user_id={current_user["user_id"]}')

    for result in membership:
        current_membership = {
          "mid": result[0],
          "member_level": result[1],
          "rewards": result[2],
          "upay_amount": result[3],
          "platform_name":result[11]
        }
    #bookings = g.conn.execute(f'SELECT * FROM Events WHERE eid=(SELECT eid FROM Registers WHERE pid=(SELECT pid FROM BooksFor WHERE user_id={current_user["user_id"]}))')
    #bookings = g.conn.execute(f'SELECT * FROM Events JOIN Registers ON Events.eid=Registers.eid JOIN BooksFor ON Registers.pid=BooksFor.pid AND BooksFor.user_id={current_user["user_id"]}')
    bookings = g.conn.execute(f'SELECT * FROM Events JOIN Registers ON Events.eid=Registers.eid JOIN Participants ON Registers.pid=Participants.pid JOIN BooksFor ON Participants.pid=BooksFor.pid AND BooksFor.user_id={current_user["user_id"]}')
    current_registers = []
    for result in bookings:
        register = {
          "ename": result[1],
          "eplace": result[2],
          "etime": result[3],
          "edate": result[4],
          "pid": result[9],
          "seat_zone": result[10],
          "seat_number": result[11],
          "pname": result[12]
        }
        current_registers.append(register)
     
    Events = g.conn.execute("SELECT * FROM Events")
    events = []
    for result in Events:
        event_obj ={
          "eid":result[0],
          "name":result[1],
          "place":result[2],
          "time":result[3],
          "date":result[4],
          "limitted_attendance":result[5]
        }
        events.append(event_obj)
    Events.close()

    return render_template("user.html", current_user=current_user, current_membership=current_membership, current_registers=current_registers, events=events)

@app.route('/signup', methods=['POST', 'GET'])
def signup_page():
  if request.method == 'GET':
      memberships = g.conn.execute("SELECT * FROM Memberships ORDER BY mid")
      memberships_objs = []
      for result in memberships:
          membership_obj = {
            "mid": result["mid"],
            "member_level": result["member_level"],
            "upay_amount": result["upay_amount"],
            "rewards": result["rewards"],
          }
          memberships_objs.append(membership_obj)
      return render_template("signup.html", memberships_objs=memberships_objs)
  if request.method == 'POST':
      name = request.form.get('name')
      ucontact = request.form.get('ucontact')
      upay = request.form.get('upay')
      print('print request')
      print(request.form)
      engine.execute(f"INSERT INTO Users (name, ucontact, upay, coupon) VALUES ('{name}', '{ucontact}', '{upay}', 0);")
      return redirect('/')

@app.route('/update_membership/<user_id>', methods=['POST', 'GET'])
def update_membership(user_id):
    memberships = g.conn.execute("SELECT * FROM Memberships ORDER BY mid")
    memberships_objs = []

    for result in memberships:
        membership_obj = {
            "mid": result["mid"],
            "member_level": result["member_level"],
            "upay_amount": result["upay_amount"],
            "rewards": result["rewards"],
        }
        memberships_objs.append(membership_obj)



    if request.method == 'GET':
        return render_template("update_membership.html", user_id = user_id, memberships_objs = memberships_objs)
    if request.method == 'POST':
        mid = request.form.get('mid')
        membership_exist = g.conn.execute(f'SELECT EXISTS (SELECT * FROM Has WHERE user_id={user_id})')
        has = None
        for result in membership_exist:
            has = result[0]

        # if user has a membership record in Has table, update its Has record   
        if has == True:
            engine.execute(f"UPDATE Has SET mid={mid} WHERE user_id={user_id};")

        # if user doesn't have a membership record in Has table, insert one
        else:
            engine.execute(f"INSERT INTO Has (user_id, mid) VALUES ('{user_id}', '{mid}');")
      
        return redirect('/')

@app.route('/eventinfo/<eid>')
def category(eid):
    Category = g.conn.execute(f'SELECT * FROM Categories WHERE category_id=any(SELECT category_id FROM BelongsTo WHERE eid={eid})')
    category_objs = []
    for result in Category:
        category_obj = {
        "category_name": result[1],
        "price_level": result[2],
        "price_interval": result[3],
        "maximum_price": result[4]
        }
        category_objs.append(category_obj)  # can also be accessed using result[0]
    Category.close()

    Casts = g.conn.execute(f'SELECT * FROM Casts WHERE cid=any(SELECT cid FROM Performs WHERE eid={eid})')
    casts_objs=[]
    for result in Casts:
        result_obj ={
        "cid":result[0],
        "name":result[1],
        "role":result[2],
        "salary":result[3]
        }
        casts_objs.append(result_obj)

    return render_template("eventinfo.html", category_objs=category_objs,casts_objs=casts_objs)

@app.route('/sponsors/<cid>')
def sponsor(cid):
    Sponsor = g.conn.execute(f'SELECT * FROM Sponsors WHERE sid=any(SELECT sid FROM SponsoredBy WHERE cid={cid})')
    sponsor_objs = []
    for result in Sponsor:
        sponsor_obj={
        "name":result[1],
        "since_when":result[2],
        "until_when":result[3]
        }
        sponsor_objs.append(sponsor_obj)
    return render_template("sponsor.html",sponsor_objs=sponsor_objs)

@app.route('/register/<user_id>', methods=['POST', 'GET'])
def register(user_id):
    Events = g.conn.execute("SELECT * FROM Events")
    events = []
    for result in Events:
        event_obj ={
          "eid":result[0],
          "name":result[1],
          "place":result[2],
          "time":result[3],
          "date":result[4],
          "limitted_attendance":result[5]
        }
        events.append(event_obj)
    if request.method == 'GET':
        return render_template("register.html", user_id=user_id, events=events)
    if request.method =='POST':
        eid = request.form.get('eid')
        name = request.form.get('name')
        seat_zone = request.form.get('seat_zone')
        seat_number = int(request.form.get('seat_number'))
        
        # insert a new participant
        engine.execute(f"INSERT INTO Participants (seat_zone, seat_number, name) VALUES ('{seat_zone}', {seat_number}, '{name}');")
        # get the newest participant is in Participant table
        newest_participant = g.conn.execute("SELECT * FROM Participants WHERE pid=(SELECT MAX(pid) FROM Participants)")
        
        for result in newest_participant:
            newest_pid = result[0]
            
            # insert a new BooksFor using the newest using the newest pid
            engine.execute(f"INSERT INTO BooksFor (pid, user_id) VALUES ('{newest_pid}', {user_id});")

            # insert a new Begister using the newest pid
            engine.execute(f"INSERT INTO Registers (pid, eid) VALUES ('{newest_pid}', {eid});")

        return redirect('/')
#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)


  #
  # example of a database query
  #
  cursor = g.conn.execute("SELECT name FROM test")
  names = []
  for result in cursor:
    names.append(result['name'])  # can also be accessed using result[0]
  cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be 
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #     
  #     # creates a <div> tag for each element in data
  #     # will print: 
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  context = dict(data = names)


  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/another')
def another():
  return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  g.conn.execute('INSERT INTO test VALUES (NULL, ?)', name)
  return redirect('/')


@app.route('/login')
def login():
    #abort(401)
    #this_is_never_executed()
    return render_template("login.html")


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
