import webapp2
import os
import jinja2
import datetime
import time

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class Post(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)


CACHE = {}
UPDATE = {}

def render_front(self):
	if not CACHE.has_key('posts'):
		CACHE['posts'] = db.GqlQuery('SELECT * FROM Post ORDER BY created DESC')
		UPDATE['posts'] = time.time()

	posts = CACHE['posts']
	self.render("front.html", posts = posts, ndate = datetime.date.today().strftime('%m/%d/%Y'), update = round(time.time() - UPDATE['posts'], 1))

class MainHandler(Handler):
    def get(self):
    	render_front(self)

class PostHandler(Handler):
    def get(self):
        self.render("newpost.html")

    def post(self):
    	gSubject = self.request.get('subject')
    	gContent = self.request.get('content')

    	if gSubject and gContent:
    		p = Post(subject = gSubject, content = gContent)
    		p.put()
    		time.sleep(0.1)
    		CACHE.pop('posts')
    		#CACHE['posts'] = db.GqlQuery('SELECT * FROM Post ORDER BY created DESC')
    		#UPDATE['posts'] = time.time()
    		pid = str(p.key().id())
    		CACHE[pid] = p
    		UPDATE[pid] = time.time()
    		self.redirect('/post/%s' % pid)
    	else:
    		if not gSubject and not gContent:
    			self.render('newpost.html', error = 'Need content and subject', )
    		elif not gSubject:
    			self.render('newpost.html', error = "need subject", content = gContent)
    		else:
    			self.render('newpost.html', error = "need content", subject = gSubject)

class PostPage(Handler):
	def get(self, pid):
		if not CACHE.has_key(pid):
			key = db.Key.from_path('Post', int(pid))
			post = db.get(key)

			if not post:
				self.error(404)
				return
			CACHE[pid] = post
			UPDATE[pid] = time.time()
		self.render('permalink.html', post = CACHE[pid], update = round(time.time() - UPDATE[pid], 1))


class Signup(Handler):
	def get(self):
		self.render('signup.html')
	def post(self):
		username = self.request.get('username')
		email = self.request.get('email')
		password = self.request.get('password')
		verify = self.request.get('verify')

		if not (username and password and verify):
			self.render('signup.html', error = 'Need all fields')
		elif password != verify:
			self.render('signup.html', error = 'Passwords do not match')
		else:
			self.response.headers.add_header('Set-Cookie', str("%s=%s; Path=/" % ('username', username)))
 			self.redirect('/welcome')

class Welcome(Handler):
	def get(self):
		username = self.request.cookies.get('username')
		if username:
			self.write('Welcome, %s' % username)
		else:
			self.redirect('/signup')

class User(db.Model):
	username = db.StringProperty(required = True)

class Login(Handler):
	def get(self):
		self.render('login.html')
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		if username and password:
			self.response.headers.add_header('Set-Cookie', str("%s=%s; Path=/" % ('username', username)))
			self.redirect('/welcome')

class Logout(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie', str("%s=%s; Path=/" % ('username', '')))
		self.redirect('/signup')

class Flush(Handler):
	def get(self):
		CACHE.clear()
		UPDATE.clear()
		self.redirect('/')

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/newpost', PostHandler),
    ('/post/([0-9]+)', PostPage),
    ('/signup', Signup),
    ('/welcome', Welcome),
    ('/login', Login),
    ('/logout', Logout),
    ('/flush', Flush)
], debug=True)

