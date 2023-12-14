## What is Flask?

Flask is a *micro-framework* for writing webapps in Python. It's very easy, very simple, very extensible, and very usable. And it scales pretty well too!  
  
A lot can be learned from the [docs/homepage](https://flask.palletsprojects.com/en/2.3.x/) and a surprising amount from [wikipedia](https://en.wikipedia.org/wiki/Flask_(web_framework)) as well. But I'll give an uber-basic rundown of how flask stuff works here.

## What is Jinja?

Jinja is the [templating language](https://en.wikipedia.org/wiki/Web_template_system) that is used to serve Flask web apps. ([wikipedia](https://en.wikipedia.org/wiki/Jinja_(template_engine))) It is basically a system to dynamically serve HTML based on a number of factors that we have control of: we can change what HTML we serve based on variable values, loop through data structures, etc.

## What is Bootstrap?

Bootstrap is the CSS framework I'd like to work in. [Bootstrap](https://en.wikipedia.org/wiki/Bootstrap_(front-end_framework)) was originally developed by Twitter, but it's a way to make responsive, awesome (\*arguably) webapps with a certain look and feel that work over many sorts of formats from mobile to desktop without having to go completely nuts with vanilla CSS.

### So what would this look like?

I'll provide a few samples here of my webapp [MoodTracky](https://fitzentoaster.github.io/moodtracky.html) to show you how you can leverage your existing HTML/CSS knowledge with a few little quirks to make powerful, dynamic webapps.

![MoodTracky img](https://fitzentoaster.github.io/moodtrackysummaryscreen.png)

This is a rough example of how a hypothetical user's "Summary" site would look on the Mood Tracky app. It pings the database for information the user has logged about their mood symptoms and medication, and shows it in a dynamic pattern. Looks complicated right?  
  
Well first here's all the python required

```python
def summary():
    todays_date = todaysDate(session["timezone_offset"])
    month_ago = todays_date - datetime.timedelta(days = 30)
    
    db = sql.connect(DB)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM entries WHERE datestamp > ? AND user_id = ? ORDER BY datestamp desc", (month_ago.strftime(date_format), session["user_id"]))
    displayable_entries = cursor.fetchall()
    db.close()
    
    if len(displayable_entries) == 0:
        return render_template('noentries.html')
    else:
        return render_template("summary.html", entries = displayable_entries, format = "summary")
```

That's the entirety of the backend of the Summary site. If there's no displayable entries, it displays the "noentries.html" site. If there are entries, it displays "summary.html" and passes two values (props? if you will) to it.

The bulk of it is just pinging the database using [SQL](https://en.wikipedia.org/wiki/SQL).

### Next is the HTML/Jinja/Bootstrap

Next up is the HTML/Stuff we're actually serving to the client. This is pretty simple too. I won't post the entirety of the html/jinja template here but we'll go piece by piece.

```xml
{% extends "layout.html" %}
```

First we include this line, which covers all of the basic interface we need to include in our page. It essentially includes layout.html in the page itself, so we don't have to copy it: nice!

Next up is some stuff, but the bulk of it can be explained away with these few lines:

```xml
{% if entries %}
    {% for row in entries %} 
        <h2>(HTML GOES HERE)</h2>
```

Basically, we're using if/then, and an iterative loop... for html? Neat! Thanks Jinja! So if entries isn't blank, we're iterating through every entry, row by row. Here we can display each row, pick its font, its color, its heading, etc. all by using normal html (and bootstrap shenanigans, of course). This allows us to serve html for a whole mess of rows for a table by just using a few lines of code.

Within this block, we can access ANY of the props we passed into the Jinja template. For instance in this case, {{ row\[4\] }} would be the current row's (or the day we're working with) depressive symptom rating. I didn't bother making this more explicit but we can make this even easier, to the point where something like {{ row.depressive }} would mean we can access the depression symptoms of the current date.

Using this style, we can iterate over an entire month's worth of symptoms and show them in an easy-to-see format. For this project, this is likely how we would show a shopping cart, etc.

## I hope it sorta makes sense!

If you're in my group I'll walk you through setting up the venv and stuff you'll need so you can just program away and test it all locally before sending anything to github, etc. This isn't even a primer, just kinda a way to sell you on the process. This also ignores much of bootstrap, but we'll get to that as well!


