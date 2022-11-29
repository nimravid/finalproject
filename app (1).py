from flask, import Flask, render_template, request

app = Flask (_name_)

@app.route("/")
def index():
    name = request.args.get("name", "filler")
    return render_template("index.html", name=name)
    ## what render_template does: finding file and viewing it (index.html)

## adding a route for friends to
@app.route("/friends")
def friends():
    friends = request.args.get("friend")
    month = request.args.get("month")
    day = request.args.get
    return render_template("friends.html", friends=friends, month=month, day=day)