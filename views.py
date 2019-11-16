import datetime, re, math, random, os, copy, bcrypt, functools, operator, uuid
import urllib.request, json
from collections import Counter
from itertools import chain
from PIL import Image
from operator import attrgetter, itemgetter
from nexus.models import Tag, Meta_Tag, Venue, Event, Account, Contributor
from nexus.models import Pix, Pix_Set, Pix_Stamp, Journal, People, Video
from nexus.models import News_Tag, Promotion, Subscriber, Essay
from nexus.models import Feedback, Deleted_Account, Posted, Query
from nexus.models import Click, Click_Page
from nexus.models import Click_Review, Click_Essay, Click_People
from nexus.models import Recommend, Event_Comment
from nexus.models import Logged_In, Logins, Locked, Lockouts, Verboten, Cloak
from nexus.models import date_span, earliest_date, furthest_date
from nexus.models import valid_url, valid_length, validate
from nexus.models import helptext, title_text
from nexus.templatetags.nexus_filters import next_ven_open_date
from nexus.templatetags.nexus_filters import next_evt_open_date
from nexus.countries import countries
from nexus.alphabase import alphabase, base_set, reverse_alphabase
from nexus.generator import passwords
from nexus.urlspace import urls_loc
from nexus.forms import MetaTagForm, TagForm,VenueForm,EventForm,AccountForm
from nexus.forms import PromotionForm, SubscriberForm,FeedbackForm
from nexus.words import adjectives
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django import forms, http
from django.http import HttpResponse
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F, Sum
from django.db import transaction
from django.core import mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
logger = logging.getLogger(__name__)

###### SETS IF LOCAL NETWORK OR ON REMOTE SERVER #############
local_network = True
img_prefix = "http://127.0.0.1:5433/static/nexus/images/"
site_prefix = "http://127.0.0.1:5433/"
media_url = "http://127.0.0.1:5433/media/"
##############################################################

strftime = '%a,%d-%b-%y %H:%M' #for most .strftime functions
ministrf = '%a,%d-%b-%y' #for most .strftime functions
longdaystrft = '%A, %d %B %Y' #not used here but in templatetags
superuser_account = 'xxxx@sqwzl.com' #non-public superuser account
no_account = 'xxxx@sqwzl.com' #non-public account for non-registered users
super0 = 'xxxx@sqwzl.com' #public superuser; use real email in case pw reset
superinputters = [super0]
image_file_limit = 1.0 * 1024 * 1000

noaccount_refid = '24-1'  #account refid for no_account users
today = timezone.now()
tomorrow = today + datetime.timedelta(days=1)
today_plus7 = today + datetime.timedelta(days=7)
today_plus30 = today + datetime.timedelta(days=30)
furth_date = furthest_date.strftime('%A, %d %B %Y')
saved_before = False  #track if field already saved to avoid double saves
login_max = 4
attempts = 0
max_banner_pix = 9 #max pix for banner
end_soon_days = 7
start_soon_days = 7
meta_tags = Meta_Tag.objects.all()
ctr_dict = dict((k, v) for k, v in countries)
ctr_reverse = dict((v, k) for k, v in countries)

#set urls space
urls = urls_loc

#Google static map details
'''
http://maps.google.com/maps/api/staticmap?center={{r.venue.ven_zip}}&zoom=15&size=400x300&maptype=roadmap&markers=color:ORANGE|label:A|{{r.venue.ven_zip}}&sensor=true&key=AIzaSyBXQqLpKYzzNoTOoanEJKVUsL7dbuGhv5Q
'''
goog_staticmap_base = 'http://maps.google.com/maps/api/staticmap?center='
goog_staticmap_zoom = '15'
goog_staticmap_size = '400x300'
goog_staticmap_maptype = 'roadmap'
goog_staticmap_markers = 'color:ORANGE|label:A|'
goog_sensor = 'true'
goog_staticmap_key = 'AIzaSyBXQqLpKYzzNoTOoanEJKVUsL7dbuGhv5Q'
goog_staticmap_1 = goog_staticmap_base
goog_staticmap_2 = '&zoom=' + goog_staticmap_zoom + \
					'&size=' + goog_staticmap_size + \
					'&maptype=' + goog_staticmap_maptype + \
					'&markers=' + goog_staticmap_markers
goog_staticmap_3 = '&sensor=' + goog_sensor + '&key=' + goog_staticmap_key

messages = {#error messages; !!not all as some still within defs

	'active_account': 'True',

	'logged_in_msg' :'You are logged in. Add events below.',

	'inactive_account': 'Events for inactive accounts will not be public.',

	'incorrect_login': 'Please correct your login details.',

	'no_password': 'Please enter a password',

	'password_mismatch': 'Please ensure your password entries match.',

	'email_taken': 'The email has been taken. Please try another or login above.',

	'pw_length': 'Password length: ' + \
			str(valid_length('password')[0][0]) + ' to ' + \
			str(valid_length('password')[0][1]) + ' characters',

	'terms_not_ticked': 'Accept Terms & Conditions to continue',

	'login_error': 'We could not log you in. Please contact our help desk.',

	'add_event_fail': 'We are sorry we could not add your event. Please try again. If you still experience problems then please contact our help desk.',

	'event_success':'Thanks! Add more events below.',

	'url_error': 'Please enter a valid url '+helptext('website'),

	'feedback':('Enter comments and feedback below', 'Thank you for your comments. We appreciate your time.'),

	'signup': 'Sign up to add multiple events in one submission, edit events after submission, save and reuse venues and for analytics.',

	'no_description': 'There is no description for this event',

	'forbidden': 'You do not have permission for that page. If you believe this is in error please contact our help desk',

	'new_pw': 'Your new password has been sent to your email address',

	'new_pw_confirm':'You requested a password reset. Please find your new password below. You can now log in with this password and can then change your password if you wish to do so.\n\n Your temporary new password is ',

	'account_del': 'We are sorry to see you leave.',

	'page_error': 'Please correct the errors below',

	'case_sensitive': 'Email and password entries are case sensitive',

	'image_copyright':'All rights reserved.',

	'cookies':'Sqwzl uses cookies for analytics. Continued use of the website means you agree to this. TERMS: Information provided on the website is on a best efforts basis. If travelling to an event, please confirm details before travel.',

	'hashtag': 'Tip: you can click #tags to filter',

	'tagline': 'Events search for the boldly inquisitive',

	'byline':"What's On. Anywhere Everywhere.",

	'meta_title': "The events search platform for the boldly inquisitive",

	'meta_description': "Discover events and what's on from theatre to art exhibitions, gigs and live music, classes, indie cinema, spoken events, nightclubs and more.", #limit to 150 chars incl spaces

	'photoclick_tag': "Discover events and what's on, anywhere and everywhere.", #for social media

	} #messages end here - leave line as flag for defs_msg

gen_preambles = [
	'Life is awesome doing what you love.',
	'20,000 awesome ways to enjoy life more fully.',
	'20,000 awesome ways to see something daring.',
	'20,000 awesome ways to go beyond your boundaries.',
	"Find something extraordinary just for you.",
	'See where remarkable your passions may lead you.',
	'Life is short and precious. Live it.',
	'Be happy off the beaten track.',
	"The easy way to find awesome events when you're tremendously busy.",
	'Promote your unique event to the audience looking for you.',
	'You really should check our guide to killing boredom.',
	'You really should check our guide to destroying apathy.',
	"You can't miss out on these 20,000 enthralling events.",
	"Embrace joy. Find 20,000 easy ways to go crazy with inspiration.",
	'20,000 inspiring events to make you feel even more awesome.',
	'See 20,000 ways to experience something different.',
	"You don't need to go crazy to find out what's going on. Click here.",

]

old_p = [	
	"Find your perfect event",
	'Chase your passion.',
	"Don’t get stuck doing the same things over and over. Find something new.",
	"The path to fulfilment is the one that's best for you. Find your passion",
	"Find an event and moon over something incredible.",
	"Somewhere near where you are someone's doing something incredible you should see.",
	"The things that make you happy are closer than you think.",
	'Tomorrow may never come but what you do today is totally in your hands.',
	"Don't put off until next week what you can do this week",
	'Love thyself. Love art. Find music. Embrace poetry. Dig theatre. Heal with comedy.',
	'Find music - from jazz to pop, rock to soul, folk to electro',
	]

verboten_fields = {'new_account': ['name','email','website'],}

home_blurbs = { #text below home page photos	
	'listing': 'Check event listings',
	'videos': 'See what we are watching'
	}

html_buttons = { #values of various buttons
	'ven_btn_text':('Open', 'Close'),
	'tkt_btn_text':('Add new ticket link',''),
	'inf_btn_text':('Add website link',''),
	'mylinks':'Tickets',
	'myvenues':("nothing","My saved venues"),
	'sign_up':"Add events. It's free!",
	'login':("Log in","LOGIN"),
	}

tooltips = {
	'evt_nam':helptext('name'),
	'account_name':helptext('name'),
	'account_email':helptext('email'),
	'password':helptext('password'),
	'password2':'Please re-enter your new password to match the one above',
	'phone':helptext('phone'),
	'website':'Please enter a valid web address',
	'tags':'Separate multiple tags with a semi-colon and enclose phrases in quotes; ' + helptext('tag'),
	'dropdown':'Select from your previously saved places',
	'add_event_no_account':'Click to add an event without setting up an account. Without an account you will not be able to amend your event details after submission.',
	'add_event':'With an account you can add multiple events in one submission, edit events after submission, set both From & To dates, reuse venues and more.',
	'evt_dte':'You can add events up '+str(date_span)+' days from today to '+furth_date,
	'new_venue':'Add the venue for your event in the form that opens at the bottom of the page. If you have an account this will be saved so you have access to it next time.',
	'pw_reset':'If you have forgotten your password we will send you another. Please enter your email and then click this button',	
	'sweets': 'Website will open in a new window.',
	'icon_click':'Click to view full calendar of events and activities',
	'tag_click': 'Find other events ',
	'free': 'Click to find other free events.',
	'filter_tip': 'Refine search and click Fetch to see the results',
	'contact_me':'For people to contact you via your saved details',
	'fave_tags':'Click to add to the text box',
	}

placeholders = { #for html elements not defined in forms.py
	'new_account_name':'Optional: account name',
	'new_account_email':'Required: login email',
	'new_account_password':'Required: login password',
	'login_email':'Your login email',
	'login_email_reset':'New login email',
	'login_password':'Your login password',
	'reset_name':'New account name',
	'new_login_password':'New login password',
	'password2':'Re-enter new password',
	'reset_confirm_password':'Confirm current password',
	#'search_box':'   Welcome!  Search ...', #unused as cant make colour white
	'link_box':'Descriptive name',
	'url_box':'Full website link',
}

filter_event_actions = [ #my_events drop-down actions: listed in order
	"Select events to show",
	'Show all live events',
	'Show all past events',
	'Show all events',
	#'Most clicked events - can also show numbs bubble on my_eve page',
	#'Most recommended - can also show numbs bubble on my_eve page',
	]

update_venue_actions = [ #my_venues drop-down actions: listed in order
	'Select update action below',
	'Edit venue',
	'Delete venues',
	'Events at this venue',
	'Add a new venue',
	]

filter_keys = ('evt','cty','ven','ctr','met','tag','dte','tim')

query_filters = ('dte=','tme=','eve=','ven=','cty=','ctr=','zip=',
				'tag=','met=','pay=','win=','qry=','ref=','pop=')

date_filters = {
		'tod':today.weekday(),
		'today':today.weekday(),
		'tom':
			(today+datetime.timedelta(days=1)).weekday(),
		'tomorrow':
			(today+datetime.timedelta(days=1)).weekday(),

		'wee':'weekend',
		'n7d':'n7d', 'n30d':'n30d',

		'jan':1,'feb':2,'mar':3,'apr':4,
		'may':5,'jun':6,'jul':7,'aug':8,'sep':9,
		'oct':10,'nov':11,'dec':12,

		'january':1,'february':2,'march':3,'april':4,
		'may':5,'june':6,'july':7,'august':8,'september':9,
		'october':10,'november':11,'december':12,

		'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3,
		'friday':4, 'saturday':5, 'sunday':6,
		'mondays':0, 'tuesdays':1, 'wednesdays':2, 'thursdays':3,
		'fridays':4, 'saturdays':5, 'sundays':6,

		'week':None,'month':None, 'year':None, 'weekend':None,

		'morning':None, 'afternoon':None, 'evening':None,
		'night':None, 'nite':None, 'tonight':None, 'tonite':None,

}

days_filters = {'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3,
		'friday':4, 'saturday':5, 'sunday':6,
		'today':timezone.now().date().weekday(),
		'tomorrow': None,
}

months = ('january', 'february', 'march', 'april', 'may', 'june', 'july',
			'august', 'september', 'october', 'november', 'december')

late = ['night','tonight','nite','tonite',' eve ','evening','pm','late']

day = ['afternoon', 'morning']

home_ips = ['46.101.83.121','81.187.219.187','89.197.81.109','46.102.196.205',]

bot_identifier = ['bot','slurp','spider','crawler','flash_event',
	'qwant','dataprovider','facebookexternalhit','googleusercontent',
	'bing','tweetedtimes']

bot_ips = ['35.197','35.199','35.2','167.100','23.94','158.69','192.99',
			'38.102.129','54.198.55','203.133.168','206.144.68',
			'54.39','23.239.219','34.235.48.77','198.23.168',
			'142.44.215','217.182.132','51.255.83','151.80.23']
	
meta_synonyms = {
	'music':('gigs','live music','live bands','concerts'),
	'theatre':('plays',),
	'cinema':('films','movies'),
	'art':('exhibitions',),
	'clubs':('nightclubs','night clubs',),
}

seo_headers = { #65 chars
	'listings/dte=today':('Today',"Discover events and what's on today"),
	'listings/dte=tomorrow':('Tomorrow',"Discover events and what's on tomorrow"),
	'listings/dte=weekend':('Weekend',"Discover events and what's on this weekend"),

	'listings/met=art':('Art','Discover art events from exhibitions to workshops, tours'),
	'listings/met=music':('Music','Gigs, concerts, live music, open mics'),
	'listings/met=theatre':('Theatre','Discover great drama, opera, musicals, performances'),
	'listings/met=dance':('Dance','From ballet to contemporary dance to street dance'),
	'listings/met=comedy':('Comedy','Indulge your funny bone and find comedy and stand-up nights'),
	'listings/met=kids':('Kids','Fun events for the little ones'),
	'listings/met=families':('Families','Events and activities for all the family'),
	'listings/met=clubs':('Clubs',"Clubnights any time of the week and party like it's 2099"),
	'listings/met=spoken':('Spoken',"Spoken events from poetry to open mics, discussions, q&a"),

	'listings/':("What's On",'The full listings with tens of thousands of events'),
	'curated/':('Curators','Wild and wonderful recommendations from our curators'),
	'essay/':('Write-Ups','Read interesting articles on a variety of topics'),
	'review/':('Reviews','Event reviews on art, theatre, live music and more'),
	'people/':('People','Interviews and conversations with creatives'),
	'video/':('Videos','From music videos to documentaries and web series'),
	'no_account/':('Add An Event','Add and share your own event. Its easy and free.'),
	'loginpage/':('Login','Login or create an account to add and track your events')
}

def is_verboten(check):
	''' check email/user/text in disallowed list '''

	verboten = False
	verbotens = Verboten.objects.all()
	for v in verbotens:
		if v.verboten in check:
			verboten = True
			v.count = v.count + 1
			v.save()
			return verboten
	return verboten

def check_referer(request):
	''' authenticate referer header in approved list '''

	in_referer = False
	refs = [
	'loginpage/','login/existing/','login/new/','logout/',
	'add_event/','my_events/','my_venues/',
	'my_account/','my_account/reset/','my_account/save_changes/',
	'feedback/','account/delete/','refresh/',
	'people/','essay/','video/','review/',
	'listings/','home/','no_account'
	]

	#check referer header is in approved list
	if 'HTTP_REFERER' in request.META.keys():
		if any(site_prefix+r in request.META['HTTP_REFERER'] for r in refs):
			in_referer = True
	return in_referer

def is_logged_in(email,logging_in=False):
	''' check if user is logged on '''

	logged_in = False
	
	#if logging in then possibly not alreally logged in so set = True
	if logging_in: 
		return True
	else:
		try:
			Logged_In.objects.get(user__email=email)
			logged_in = True
		except:
			pass
	return logged_in

def is_superinputter(request):
	''' check if superinputter '''

	superinput = False
	if request.method == 'GET':
		if 'email' in request.GET.keys():
			if request.GET['email'] in superinputters: superinput = True
		if 'name' in request.GET.keys():
			if request.GET['name'] in superinputters: superinput = True
	if request.method == 'POST':
		if 'email' in request.POST.keys():
			if request.POST['email'] in superinputters: superinput = True
		if 'name' in request.POST.keys():
			if request.POST['name'] in superinputters: superinput = True

	return superinput

def authenticate_poster(request,**kwargs):
	''' authenticates poster is a valid account '''
	
	email, token, post_error, authenticated = '', '', '', False
	invalid = [superuser_account, no_account]
	
	#list of security tokens to search in order of preference
	cook, post = request.COOKIES, request.POST
	tokens, logins  = ['sessionid', 'csrftoken'], ['email_', 'new_email']
	
	#for brand new logins
	for l in logins:
		if l in post.keys():
			if post[l] != '': email = post[l]

	#for already logged in
	if email == '':
		for t in tokens:
			if t in cook.keys():
				token = cook[t]
				if t == "sessionid":
					if Logged_In.objects.filter(session=token).exists():
						
						email = Logged_In.objects \
									.filter(session=token)[0].user.email
						#break if email found
						if email != '': break

				elif t == "csrftoken":
					if Logged_In.objects.filter(cookie=token).exists():
						email = Logged_In.objects \
									.filter(cookie=token)[0].user.email
						#break if email found
						if email != '': break

	#assign no_account if not a registered account
	if email == '' and any(t in cook.keys() for t in tokens):
		email = no_account

	#now run validation checks					
	if email != '':
		if email in invalid: return authenticated, email

		if Account.objects.filter(email=email).exists(): 
			
			in_referer = check_referer(request)
			logged_in = is_logged_in(email=email,logging_in=True)
			locked_out = is_locked(request,email=email)
			valid_status = [in_referer, logged_in, not locked_out]

			if all(valid_status): authenticated = True

	return authenticated, email

def is_locked(request,**kwargs):
	''' check if user is locked out '''

	locked_out = False
	if 'email' not in kwargs.keys():
		authenticated, email = authenticate_poster(request)
	else:
		email = kwargs['email']

	try:
		user = Locked.objects.get(user=email)
		locked_out = True
		return locked_out
	except:
		return locked_out

def is_reset(request):
	''' checks if user has asked for page to be reset '''
	reset = False
	if request.POST.get('reset') or request.POST.get('reset2'):
		reset = True
	return reset

def time_convert_to_minutes(time):
	''' convert hour:min to total minutes in day '''
	time = time.split(':')
	hour = int(time[0])
	minute = int(time[1])
	converted = hour * 60 + minute
	return converted

def reformat_date(request, which):
	''' convert date format from jquery choice to database '''

	date, months = '', date_filters

	if request.method == 'POST':
		if which == "first": date = request.POST["evt_dte"]
		if which == "end": date = request.POST["evt_end"]

	else:
		if which == "first": date = request.GET.get("evt_dte")
		if which == "end": date = request.GET.get("evt_end")

	def datetime_format(date):
		''' convert from string YYYY-MM-DD to datetime format '''
		d = None
		if '/' in date: d = date.split('/')
		if '-' in date: d = date.split('-')
		if d:
			if len(d[0]) == 4: #YYYY-MM-DD
				date = datetime.date(int(d[0]), int(d[1]), int(d[2]))
			elif len(d[2]) == 4: #DD-MM-YYYY
				date = datetime.date(int(d[2]), int(d[1]), int(d[0]))
		return date

	#if already in date format e.g. '2014-11-30' then 
	#convert to datetime format
	date = datetime_format(date)

	#do nothing here if submitted without dates
	if isinstance(date, datetime.date): 
		return date

	else:
		#else just continue with main function
		#jquery format e.g.: Thursday, 20 February
		regex = re.compile(r'(.+,\s)(\d+)(.+?)(\d+)$')
		matched = regex.findall(date)

		if matched:
			#findall returns a tuple inside a list!!
			date_number = int(matched[0][1].strip())
			month = matched[0][2].strip()
			year = int(matched[0][3].strip())
			
			#convert month to number format and turn to python object
			month = months[month.lower()]
			date = datetime.date(year, month, date_number)
		else:
			date = None

	return date

def date_range(case,qualifier):
	''' get date range for case month '''

	start, end, pick = '', '', ''
	today = timezone.now().date()
	tomorrow = today + datetime.timedelta(days=1)
	year = today.year 
	mth_today = today.month
	days_to_go = 0
	date_pick = False

	try:
		#date picked from calendar
		pick = datetime.datetime.strptime(case, '%a, %d %B %Y')
		date_pick = True
	except:
		pass

	if case == 'today': 
		start, end = today, today

	elif case == 'tomorrow': 
		start, end = tomorrow, tomorrow

	elif date_pick:
		start, end = pick, pick

	elif case in days_filters:
		#cases like Tuesday, Sunday

		day_index = days_filters[case] #eg Tue = 1
		today_index = today.weekday()
		
		#today=Thur=4 and day_index=Tue=2
		#then we want the following Tue
		#which is 7 - today + day_index = 5 days away
		if today_index > day_index:
			days_to_go = 7 - today_index + day_index
		else:
			#it's day_index - today days away
			days_to_go = day_index - today_index

		start = today + datetime.timedelta(days=days_to_go)
		end = start

		if qualifier == 's':
			end = furthest_date

	elif case == 'week':
		if qualifier == 'this':
			wk_day = today.weekday()
			days_to_go = 6 - wk_day
			start = today
			end = today + datetime.timedelta(days=days_to_go)

		elif qualifier == 'next':
			wk_day = today.weekday()
			days_to_go = 6 - wk_day + 7
			end = today + datetime.timedelta(days=days_to_go)
			start = end - datetime.timedelta(days=6)

	elif case == 'weekend':
		if qualifier == '' or qualifier == 'this':
			wk_day = today.weekday()
			days_to_go = max(0,4 - wk_day)
			days_to_end = max(0,6 - wk_day)
			start = today + datetime.timedelta(days=days_to_go)
			end = today + datetime.timedelta(days=days_to_end)

		elif qualifier == 'next':
			wk_day = today.weekday()
			days_to_go = max(0,4 - wk_day) + 7
			days_to_end = max(0,6 - wk_day) + 7
			start = today + datetime.timedelta(days=days_to_go)
			end = today + datetime.timedelta(days=days_to_end)

	elif case == 'month':
		
		mth_index = today.month
		start_year, end_year = today.year, today.year
				
		if qualifier == 'this':
			next_mth_index = mth_index + 1
			if next_mth_index == 13:
				next_mth_index = 1  #set to january
				end_year = start_year + 1 #of the following year

			start = today
			end = datetime.date(end_year,next_mth_index,1) - \
					datetime.timedelta(days=1)

		elif qualifier == 'next':
			mth_index = today.month + 1
			if mth_index == 13: #so cur_mth=Dec
				mth_index = 1 #set next_mth=Jan
				start_year = start_year + 1	#of following year
				end_year = start_year

			next_mth_index = mth_index + 1
			if next_mth_index == 13: #if cur_mth=Nov,next=Dec,after=Jan
				next_mth_index = 1 #set after=Jan
				end_year = end_year + 1	#of follwing year

			start = datetime.date(start_year,mth_index,1) 
			end = datetime.date(end_year,next_mth_index,1) - \
					datetime.timedelta(days=1)

	elif case in months:
		mth_index = date_filters[case]
		start_year, end_year = today.year, today.year
		next_mth_index = mth_index + 1

		#if month has passed, assume next year
		if mth_index < today.month:
			start_year = start_year + 1
			end_year = start_year

		#if current month = Dec, then next month into next year
		if next_mth_index == 13:
			next_mth_index = 1
			end_year = start_year + 1
		
		start = datetime.date(start_year,mth_index,1)
		end = datetime.date(end_year,next_mth_index,1) - \
					datetime.timedelta(days=1)

	elif case == 'year':

		year = today.year
		
		if qualifier == 'this':
			start = today
			end = datetime.date(year,12,31)

		elif qualifier == 'next':
			start = datetime.date(year+1,1,1)
			end = datetime.date(year+1,12,31)


	return start, end, date_pick

def retrieve_live_events():
	''' all live events '''
	today = timezone.now().date()
	shebang = Event.objects.filter(
					Q(account__active=True) |
					Q(account=None)) \
				.filter(evt_end__gte=today) \
				.order_by('dtg_num','-created') \
				.prefetch_related('venue','meta_tag','evt_tag')
	return shebang

def get_cities(**kwargs):
	''' compile cities list '''

	cities, temp = [], []
	temp = Venue.objects.filter(event__evt_dte__gte=today)
	temp = temp.filter().values_list('ven_cty',flat=True) \
						.order_by('ven_cty').distinct('ven_cty')

	cities = list(temp)
	return cities

def remove_non_term(terms):
	''' remove words phrases that are not really search items '''
	
	#common search terms eg 'what can i do in leicester'
	#eg "what's going on in kent"
	#what's important here is leicester, kent etc
	common = ['what','where','thing','things','place','places',
				'see','can','for','the','events','in','of','at','to',
				'do','on','and','i','you','we','me',
				'happening','going',"what's",'whats','find','get','search',
				'show','any','all','anything','everything','every',
				'you','near','around','stuff','kind','kinds','sort','sorts'
				'interesting','fun','nice']

	apostrophe = ["'",'i','s'] #also ignore double ss as in boss, chess

	#remove duplicates
	if isinstance(terms,list):
		terms = list(set(terms))
		
		#remove short words unlikely to search term eg i, we, is, to, do
		terms = [t for t in terms if len(t) > 2 or t in country_code(t)]

		#remove words common in search phrases
		terms = [t for t in terms if t not in common]
	
	#replace simple plurals with singular
	try:
		for t in terms:
			if t not in common and t[-1] == 's' and t[-2] not in apostrophe:
				if t[-3] != 'i' and t[-2] != 'e': #ignore 'y'$ plural 'ies'
					terms.append(t[:-1])
					terms.remove(t)
	except:
		pass

	return terms

def create_message(count=0, **kwargs):
	''' message to show on returning listings results '''

	count_msg, msg, detail, q = '', '', '', ''
	dict_ = {}
	nxd, free = False, False


	if kwargs['filters']: dict_ = kwargs['filters']
	if kwargs['qualifier']: q = kwargs['qualifier'] + ' '

	if 'pay=' in dict_.keys():
		if dict_['pay='] == 'false': free = True

	if count == 0: 
		if 'orig_' in dict_.keys():
			msg = 'No events for your query: ' + dict_['orig=']
		else:
			msg = 'No events for your query'
	else:
		count_msg = '{:,d}'.format(count) + ' event'

	if count > 1: 
		count_msg += 's'

	#return the original query if there is one
	if count > 0:
		if 'orig=' in dict_.keys():
			orig_qry = dict_['orig=']
			if orig_qry != '':
				return count_msg, orig_qry.title()


	def replace_digit(dte):
		''' replace e.g. n3d with next 3 days '''
		try: 
			num = re.search(r'\d+', dte).group(0)
			if num == '1': dte = 'next ' + str(num) + ' day'
			else: dte = 'next ' + str(num) + ' days'
		except: 
			pass

		return dte


	if count > 0:
		if kwargs['filters']: 

			if 'pop=' in dict_.keys():
				msg += 'Popular'

			if 'eve=' in dict_.keys():
				msg += dict_['eve='].title()

			if 'win=' in dict_.keys():
				msg += dict_['win='].title() + ' soon |'

			if 'terms=' in dict_.keys():
				msg += dict_['terms='].title()

			if 'met=' in dict_.keys(): 
				if dict_['met='].title() not in detail and \
					dict_['met='].title() not in msg:
					detail += dict_['met='].title()+' events'

			if 'tag=' in dict_.keys(): 
				if dict_['tag='].title() not in detail and \
					dict_['tag='].title() not in msg:
					if ' events' in detail: 
						detail = detail.replace(' events','')
					else:
						detail += ' & ' + dict_['tag='].title() + ' events'
				if detail[:3] == ' & ': detail = detail[3:]
				detail = detail.replace('||',' & ')
				detail = detail.replace('|',' , ')
				
			if 'ven=' in dict_.keys(): 
				if dict_['ven='].title() not in detail and \
					dict_['ven='].title() not in msg:
					if detail == '':
						detail = 'Events at ' + dict_['ven='].title()
					else:
						detail += ' at ' + dict_['ven='].title()

			if 'cty=' in dict_.keys(): 
				if dict_['cty='].title() not in detail and \
					dict_['cty='].title() not in msg:
					if detail == '':
						detail = "Events in " + dict_['cty='].title()
					else:
						detail += ' in ' + dict_['cty='].title()

			if 'zip=' in dict_.keys(): 
				if dict_['zip='].title() not in detail and \
					dict_['zip='].title() not in msg:
					if detail == '':
						detail = "Events in " + dict_['zip='].title()
					else:
						detail += ' in ' + dict_['zip='].title()

			if 'ctr=' in dict_.keys(): 
				if dict_['ctr='].title() not in detail and \
					dict_['ctr='].title() not in msg:
					if detail == '':
						detail = "Events in " + dict_['ctr='].title()
					else:
						if 'cty=' in dict_.keys():
							detail = detail.replace(dict_['cty='].title(),'')
							detail += dict_['cty='].title() + ', ' + \
										dict_['ctr='].title()
						else:
							detail += ' in ' + dict_['ctr='].title() 

			if 'dte=' in dict_.keys(): 
				dte = dict_['dte=']
				calendar_date = False

				if re.search(r'.*n\d+d.*',dte):
					dte = replace_digit(dte).title()
					nxd = True

				if detail == '':
					detail = 'Events on ' + dte.title()
				else:
					if re.search(r'\d+',detail):
						#for specific dates only eg Events on 12 Sep
						detail += ' on ' + dte.title()
					else:
						detail += ' ' + dte.title()

				if nxd: detail = detail.replace(' on ',' in ')
				
				detail = detail.replace('Weekend','This Weekend')		

			if 'tme=' in dict_.keys(): 
				if dict_['tme='].lower() in late:
					detail += ' (Late)'
				else:
					detail += ' (Day)'

	
	if len(detail) > 0 and 'events' not in detail.lower():
		if 'eve=' not in dict_.keys():
			detail = 'Events in ' + detail
		else:
			detail = 'events ' + detail

	msg = msg + ' ' + detail
	msg = msg.strip()

	if msg == '':
		if free: 
			msg = 'All Free Events'
		else: 
			msg = "Scroll events below and use any #tag to filter"
	else:
		if msg == 'Popular': msg = 'Popular Events'
		if free: msg = 'Free ' + msg

	return count_msg, msg

def query_date(shebang,filt,qualifier):
	''' retrieve events for the dates filtered on '''

	today = timezone.now().date()
	tomorrow = today + datetime.timedelta(days=1)
	time_filtered = False
	multiple_days = False
	days_to_go = 999

	q_filters = ['weekend','night','evening',]

	filt = filt.lower()

	#capture if Tuesdays
	if len(filt) > 0:
		if filt[-1] == 's' and filt[:-1] in days_filters:
			filt = filt[:-1]
			qualifier = 's'

	start, end, pick = date_range(filt,qualifier)
	if start == '' or end == '':
		start, end = today, today
	the_date = start
	
	#dictionary of Q filters to match query to event days
	Q_dict = {
		0:Q(mon=True), 1:Q(tue=True), 2:Q(wed=True), 3:Q(thu=True),
		4:Q(fri=True), 5:Q(sat=True), 6:Q(sun=True),
		
		'weekend':
		(Q(fri=True,tme_beg__gte="17:00") | Q(sat=True) | Q(sun=True)),
		
	}	

	#execute filters
	filt_several = False

	if re.match(r'n\d+d',filt): #e.g. next 7|14|30|90 days etc
		num = int(re.search(r'(\d+)',filt).group(0))
		num_plus = 0
		if timezone.now().hour > 16: #if run late evening, start count tom
			num_plus = 1
		start = today + datetime.timedelta(days=num_plus)
		end = today + datetime.timedelta(days=num+num_plus)
		shebang = shebang.filter(evt_dte__lte=end) \
							.filter(evt_end__gte=start)

	elif pick:
		#need to ensure day of week is valid
		dow = start.weekday()
		shebang = shebang.filter(Q(Q_dict[dow]) &
					Q(evt_dte__lte=start) & Q(evt_end__gte=end))

	else:
		#for today, tomorrow and specific days
		if '|' in filt: 
			filt_several = True
			shebang_ = shebang.none() #empty queryset

		if filt_several:

			filt_ = filt.split('|')

			#get days from today for each day
			#we use this to set query start and end days
			d_filters = [days_filters[f] for f in filt_]
			max_d, min_d = max(d_filters), min(d_filters)

			#get the number of days to start/end of request
			max_interval = max_d - today.weekday()
			if max_interval < 0:
				max_interval = max_interval + 7
			
			min_interval = min_d - today.weekday()
			if min_interval < 0:
				min_interval = min_interval + 7

			end = today + datetime.timedelta(days=max_interval)
			start = today + datetime.timedelta(days=min_interval)

			for f in filt_:
				day_filt = days_filters[f]
				shebang_ = shebang_ | shebang.filter(Q(Q_dict[day_filt]) &
					Q(evt_dte__lte=end) & Q(evt_end__gte=start))

			shebang = shebang_

		elif filt in days_filters: 
			if filt != 'tomorrow':
				day_filt = days_filters[filt]
			else:
				day_filt = days_filters['today'] + 1
				if day_filt == 7: day_filt = 0

			shebang = shebang.filter(Q(Q_dict[day_filt]) &
					Q(evt_dte__lte=end) & Q(evt_end__gte=start))

		elif filt in Q_dict.keys():
			shebang = shebang.filter(Q(Q_dict[filt]) &
					Q(evt_dte__lte=end) & Q(evt_end__gte=start))

		else:
			shebang = shebang.filter(
					Q(evt_dte__lte=end) & Q(evt_end__gte=start))

	#numb of days before start of query
	#used to figure out if to display 'also today' etc in listings
	#start = datetime.datetime but today is datetime.date
	#convert to same format
	try:
		start = start.date()
	except:
		pass

	try:
		days_to_go = (start - today).days
	except:
		pass
	
	return shebang, days_to_go

def query_meta(shebang,filt):
	''' retrieve events based on meta tags '''
	filt = ['\y'+filt+'\y']
	shebang = shebang.filter(functools.reduce(operator.or_,(
		Q(evt_tag__tag__iregex=f) |
		Q(meta_tag__meta_tag__iregex=f)
			for f in filt))).distinct()
	return shebang

def query_tag(shebang,filt):
	''' retrieve events based on tags '''

	#note using iregex instead of icontains as latter ...
	#will match tag=art in 'artefacts' or 'fart'
	#iregex=underlying db regex; in postgresql \y = word boundaries

	filt = filt.replace('_',' ')
	
	non = ['live'] #tags we want to exclude perhaps from Google cache
	if any(n in filt for n in non):
		for n in non:
			filt = re.sub(r'\b'+n+r'\b','',filt,flags=re.I)

	if '||' in filt: 
		#all call tags apply: 'and'
		tag_done = []
		tags = ['\y'+tag+'\y' for tag in filt.split('||')]
		for tag in tags:
			tag = [tag]
			shebang = shebang.filter(functools.reduce(operator.or_,(
			Q(evt_tag__tag__iregex=t) |
			Q(meta_tag__meta_tag__iregex=t)
				for t in tag))).distinct()

	elif '|' in filt: 
		#any tags in call: 'or' 
		tags = ['\y'+tag+'\y' for tag in filt.split('|')]
		shebang = shebang.filter(functools.reduce(operator.or_,(
			Q(evt_tag__tag__iregex=tag) |
			Q(meta_tag__meta_tag__iregex=tag) \
				for tag in tags))).distinct()

	else:
		filt = ['\y'+filt+'\y']
		shebang = shebang.filter(functools.reduce(operator.or_,(
			Q(evt_tag__tag__iregex=f) |
			Q(meta_tag__meta_tag__iregex=f)
				for f in filt))).distinct()

	return shebang

def query_venue(shebang,filt):
	''' retrieve events based on venue tags '''
	shebang = shebang.filter(venue__ven_nam__icontains=filt).distinct()
	return shebang

def query_city(shebang,filt):
	''' retrieve events based on city tags '''
	shebang = shebang.filter(venue__ven_cty__icontains=filt).distinct()
	return shebang

def query_postcode(shebang,filt):
	''' retrieve events based on postcode tags '''	
	shebang = shebang.filter(venue__ven_zip__iregex='^\y'+filt+'\y') \
					.distinct()
	return shebang

def country_abbreviation(ctr):
	''' return common country abbreviations '''
	abbrv = {'uk':'united kingdom','us': 'united states',}
	us_abbrv = ['us', 'usa', 'america']
	uk_abbrv = ['uk', 'england', 'wales','scotland','northern ireland',
				'britain','gb','great britain']
	for s in us_abbrv:
		if re.search(r'\b'+s+'\\b',ctr): 
			ctr = abbrv['us']
			break

	for s in uk_abbrv:
		if re.search(r'\b'+s+'\\b',ctr): 
			ctr = abbrv['uk']
			break

	return ctr

def country_code(ctr):
	''' returns country code for country '''
	code = ''
	try: code = ctr_reverse[ctr.title()]
	except: code = ctr
	return code

def query_country(shebang,filt):
	''' retrieve events based on country tags '''

	ctr, filt = [], filt.lower()

	#get full names for common country abbreviations
	filt = country_abbreviation(filt)
		
	#compile countries containing filter
	comp = re.compile(r'(.*' + filt + '.*)')
	for k in ctr_reverse.keys():
		ctr.extend(re.findall(comp, k.lower()))	
	ctr = [ctr_reverse[c.title()] for c in ctr]

	#filter events if there's at least one country found
	if ctr:
		shebang = shebang.filter(functools.reduce(operator.or_,(
							Q(venue__ven_ctr__iregex=c) \
							for c in ctr))).distinct()

	return shebang

def user_terms(request):
	''' show terms and conditions '''
	context = constants(request)
	return render(request,"nexus/terms_base.html",context)


def full_shebang(shebang,terms):
	''' run full filter query '''
	if not isinstance(terms,list): terms = [terms]
	shebang = shebang.filter(functools.reduce(operator.or_,(
							Q(evt_tag__tag__iregex='\y'+qry+'\y') |
							Q(evt_nam__iregex='\y'+qry+'.*\y') | 
							Q(descr__icontains='\y'+qry+'.*\y') | 
							Q(evt_tag__tag__iregex='\y'+qry+'\y') |
							Q(venue__ven_nam__iregex='\y'+qry+'\y') |
							Q(meta_tag__meta_tag__iregex='\y'+qry+'\y') \
							for qry in terms))).distinct()
	return shebang

def query_events(shebang, evt):
	''' retrieve evenst based on direct event search '''
	evt_, sheb_ = [], Event.objects.none()

	#event with full title given
	sheb = shebang.filter(evt_nam__iregex='\y'+evt+'\y')

	if evt.isnumeric(): # eg event feature using ref=evt.id
		sheb_ = shebang.filter(id=evt)
		
	elif ' ' in evt: # eg event feature using evt=evt_nam
		evt_.extend(evt.split())

		if evt_: #event with title fragments
			sheb_ = shebang.filter(functools.reduce(operator.and_,(
									Q(evt_nam__iregex='\y'+qry+'\y') \
									for qry in evt_)))

	shebang = sheb | sheb_

	return shebang


def query_terms(shebang, *args):
	''' retrieve events based on names and words '''

	msg_filters = {}
	orig_qry, qualifier = '', ''
	metas = Meta_Tag.objects.all().values_list('meta_tag',flat=True) 
	tags = Tag.objects.all().values_list('tag',flat=True)
	orig_qry_shebang = None
	dtg = 0

	#get list of postcodes in case this in query
	zip_terms, postcode_rip = [], []
	postcode_full = Venue.objects.all().distinct().values_list(
												'ven_zip',flat=True)
	postcode_full = [p.lower() for p in postcode_full]
	for p in postcode_full:
		try:
			postcode_rip.append(re.search(r'([a-zA-Z]+\d{1,2})',p).group(0))
		except:
			continue

	#store for later at >>> if ven_terms:
	orig_shebang = shebang

	if 'search' in args[0].keys():

		terms = args[0]['search']
		try:orig_qry = args[1]['orig=']
		except: pass
		cities = get_cities() #only cities with live events in database
		loc_terms, ctr_terms, cty_terms, ven_terms = [], [], [], []

		if not isinstance(terms,list): terms = [terms.strip()]

		#now search orig_qry for synonyms	
		for k,vals in meta_synonyms.items():
			for v in vals:
				if v in orig_qry or (v[-1]=='s' and v[:-1] in orig_qry):
					terms.append(k)

		#remove orig_qry from terms IF it's a phrase
		#so not part of terms_shebang filter below
		try:
			if ' ' in orig_qry.strip(): 
				terms.remove(orig_qry)
		except: pass

		#search for phrases('_'), or('|') & and '||'
		#for now cannot deal with '||'
		#first we deal with '|', '||' treating latter as 'or'
		t_, t__, to_del = [], [], []
		for t in terms:
			if '|' in t or '||' in t:
				to_del.append(t)
				t = t.replace('|',' ')
				t_.extend(t.split())
				t_ = list(set(t_))
		if to_del:
			for t in to_del: terms.remove(t)

		terms.extend(t_)

		#replace oddities
		terms = [t.replace('_',' ') for t in terms]

		#remove common subjunctions, prepositions, lookup phrases etc
		terms = remove_non_term(terms)

		#set to lower case
		terms = [t.lower() for t in terms]

		if terms == ['']: terms = []

		#get filter terms in search query: start with date
		dte_terms = [t.strip() for t in terms if 
							t.lower() in date_filters.keys() ]

		#if dates, filter for this first 
		if dte_terms:
			for dte in dte_terms:
				
				#if 'next' or this in query;
				#add to the date and remove + dte from terms
				if 'this' in terms: 
					terms.remove('this') 
					qualifier = 'this'
				elif 'next' in terms: 
					terms.remove('next') 
					qualifier = 'next'
				
				#remove single items in terms
				terms.remove(dte)

				msg_filters['dte='] = dte
				shebang, dtg = query_date(shebang,dte,qualifier)
				
			#add to dte_terms so part of message
			dte_terms = [qualifier + ' ' + d for d in dte_terms]

		#next we do venues, cities and locations
		ctr_terms = [country_abbreviation(t) for t in terms]
		if ctr_terms and ctr_terms != ['']:
			ctr_names = [t for t in ctr_terms 
							if t.title() in ctr_reverse.keys()]
			ctr_terms = [country_code(t) for t in ctr_terms 
											if t.title() in ctr_reverse.keys()]

			#add country names to terms so can pick up if in title|descr
			if ctr_names: terms.extend(ctr_names)
			#remove ctr code from terms
			#b/c if in terms: e.g. IN for India or US for United States
			# __descr__ queries will pick up the words 'in'|'us'
			for c in ctr_terms:
				c = c.lower()
				if c in terms: terms.remove(c)

		#for cty we need to look at two-word cities eg new york that 
		#might be split in terms ['new','york'] and cty_terms = ['york']
		#first check orig term:
		cty_orig = [t.strip() for t in orig_qry if t.title() in cities]

		cty_terms, to_del = [], []
		cty_orig = [re.findall(t,orig_qry,flags=re.I) for t in cities]
		for cty in cty_orig:
			if isinstance(cty,str):
				cty_terms.append(cty)
			elif isinstance(cty,list):
				for c in cty:
					cty_terms.append(c)
		cty_terms = list(set(cty_terms))

		cty_orig = cty_terms
		for t in cty_orig:
			for c in cty_orig:
				t_, c_ = t.strip(), c.strip()
				if t_ in c_ and len(t_) < len(c_):
					to_del.append(t)

		for t in to_del:
			cty_terms.remove(t)

		if cty_terms:
			for c in cty_terms:
				if ' ' not in c:
					#remove single items in terms
					if c in terms:
						terms.remove(c)
				else:
					c_str = c.split()
					for c_ in c_str:
						if c_ in terms:
							terms.remove(c_) 

		#do postcodes
		postcodes = [postcode_full, postcode_rip]
		for post in postcodes:
			if any(p in terms for p in post):
				for p in post:
					if p in terms and p not in zip_terms:
						zip_terms.append(p)
					
		#add to zips if it looks like a post/zipcode
		#reason is assuming no 'sw99' then
		#query 'sw99' brings back nothing: good
		#but 'art sw99' will bring back 'art' for all posts/zips: not good
		#so adding 'sw99' means filter on ven_zip brings back nothing: good
		for t in terms:
			if t not in zip_terms:
				if re.search(r'^[a-zA-Z]{1,2}\s{0,1}\d+',t,flags=re.I):
					zip_terms.append(t)

		#remove zips from terms
		if zip_terms:
			for z in zip_terms:
				terms.remove(z)
		
		#remove t where t == ' '
		terms = [t for t in terms if len(t.strip()) > 1]

		#for venue names check for whole term
		#if there: stop eg qry was ABC Arts Theatre
		#and terms = ['ABC Arts Theatre', 'ABC', 'Arts', 'Theatre']
		#if find 'ABC Arts Theatre' then stop but if not
		#carry on with other terms
		pos_ven, vens, ven_terms = [], [], []
		vens = Venue.objects.none()
		for t in terms:
			if ' ' in t: #b/c venue names usually long with spaces
				pos_ven.append(t)
			if pos_ven:
				for p in pos_ven:
					vens = vens | Venue.objects.filter(ven_nam__icontains=p)
			
			#now scrub from terms any term in ven name
			if vens:
				pos_vens = []
				for v in vens:
					v_lo = v.ven_nam.lower()
					pos_vens = v_lo.split()
					for p in pos_vens:
						if p in terms:
							terms.remove(p)
					if v_lo in terms: terms.remove(v_lo) 

		#no vens but a single term might be in a venue name
		#eg 'george' in 'The George And Dragon'
		if not vens:
			ven_terms = [t for t in terms if 
						Venue.objects.filter(ven_nam__iregex='\y'+t+'\y') and
						t.title() not in cities and 
						t.title() not in metas]

		terms = list(set(terms))
		terms = [t for t in terms if t.title() not in cities and 
									t.title() not in ven_terms]

		#more common that if venue in query then this is a constraint
		if vens:
			shebang = shebang.filter(functools.reduce(operator.or_,(
					Q(venue=qry)
					for qry in vens)))

			#list of venues with actual events
			shebang_vens = shebang.values_list('venue__ven_nam',flat=True)
			shebang_vens = list(set(shebang_vens))

			for s in shebang_vens:
				if s.lower() in terms: terms.remove(s.lower())


		#note: distinct() b/c evt_tag returns multiple instances
		if terms:
			#first serach if orig qry exists in name/description
			#eg user types full name of an event
			#if match then likely what we want and ignore any other terms
			#to resolve: 2 venue searches?
			if orig_qry != '' and ' ' in orig_qry:
				orig_qry_shebang = full_shebang(shebang,orig_qry)

			if not orig_qry_shebang:
				#if no orig_qry then search each t in terms
				shebang = full_shebang(shebang,terms)

		#more common that if country in query then this is a constraint
		if ctr_terms:
			shebang = shebang.filter(functools.reduce(operator.or_,(
					Q(venue__ven_ctr__iregex='\y'+qry+'\y')
					for qry in ctr_terms))).distinct()

		#b/c ven_shebang is distinct and you can't merge unique/non-unique
		shebang = shebang.distinct()

		#more common that if venue in query then this is a constraint
		#but it is possible here to have words that are in venue names
		#that's why this is at end of shebangs and not paired with 'if vens:''
		if ven_terms: #only applies if no vens ie no full venue name
			ven_shebang = orig_shebang.filter(functools.reduce(operator.or_,(
					Q(venue__ven_nam__iregex='\y'+qry+'\y')
					for qry in ven_terms))).distinct()

			#merge: note we preserve any previous shebangs b/c e.g
			#'term'='dragon' which is in George & Dragon Pub
			#we don't want to limit to only venues with Dragon
			#as we may be after event names or tags with Dragon
			shebang = shebang | ven_shebang

		#more common that if city in query then this is a constraint
		if cty_terms:
			shebang = shebang.filter(functools.reduce(operator.or_,(
					Q(venue__ven_cty__iregex='\y'+qry+'\y')
					for qry in cty_terms)))

		#more common that if postcode in query then this is a constraint
		if zip_terms:
			#nb regex to get for 'N1': N1 and not N15
			shebang = shebang.filter(functools.reduce(operator.or_,(
					Q(venue__ven_zip__iregex='^\y'+qry+'\y')
					for qry in zip_terms)))			

		#but if orig_qry found then we override and use this
		if orig_qry_shebang: shebang = orig_qry_shebang

		#create feedback message dictionary
		def create_terms(msg_terms):
			term_qry = ''
			for t in msg_terms:
				term_qry += t + ' '
			return term_qry.strip()

		#create an 'orig=' key as msg_filters
		#gets passed back to callback fxn as dict_filters
		msg_filters['orig='] = orig_qry

		if terms:
			msg_filters['terms='] = ' '.join(terms)
			
		if 'pay=' in args[1].keys():
			msg_filters['pay='] = args[1]['pay=']

		if 'met=' in args[1].keys():
			msg_filters['met='] = args[1]['met=']

		if 'dte=' in args[1].keys():
			msg_filters['dte='] = args[1]['dte=']
		elif dte_terms: 
			msg_filters['dte='] = create_terms(dte_terms)

		if 'ven=' in args[1].keys():
			msg_filters['ven='] = args[1]['ven=']
		elif vens:
			msg_filters['ven='] = create_terms(shebang_vens)
		elif ven_terms: 
			msg_filters['ven='] = create_terms(ven_terms)

		if 'cty=' in args[1].keys():
			msg_filters['cty='] = args[1]['cty=']
		elif cty_terms: msg_filters['cty='] = create_terms(cty_terms)

		if 'zip=' in args[1].keys():
			msg_filters['zip='] = args[1]['zip=']
		elif zip_terms: msg_filters['zip='] = create_terms(zip_terms)
		
		#remove venue if duplicated as city
		if 'ven=' in msg_filters.keys() and 'cty=' in msg_filters.keys():
			if msg_filters['ven='] == msg_filters['cty=']:
				del msg_filters['ven=']

		if 'ctr=' in args[1].keys():
			msg_filters['ctr='] = args[1]['ctr=']
		elif ctr_terms: 
			for t in ctr_terms:
				if t in ctr_dict.keys():
					ctr_terms.remove(t) #remove code
					ctr_terms.append(ctr_dict[t]) #add full country name
			msg_filters['ctr='] = create_terms(ctr_terms)

		if 'tag=' in args[1].keys():
			msg_filters['tag='] = args[1]['tag=']

		if 'tme=' in args[1].keys():
			msg_filters['tme='] = args[1]['tme=']

	else: pass

	return shebang, msg_filters, qualifier, dtg

def query_time(shebang,filt):
	''' retrieve events based on time tags '''

	#dictionary of Q filters to match query to event days
	Q_dict = {

		'day':
		Q(tme_beg__lt="17:00"),

		'morning':
		Q(tme_beg__lte="12:00"),

		'afternoon':
		Q(tme_beg__lt="18:00"),

		'late':
		Q(tme_beg__gte="17:00"),
		
	}

	if filt in late:
		shebang = shebang.exclude(tme_beg='00:00')
		filt = 'late'

	if filt in Q_dict.keys():
		shebang = shebang.filter(Q(Q_dict[filt]))
	
	return shebang

def query_free(shebang, filt):
	''' retrieve events based on if free ie pay=filt=yes event '''
	pay, notpay = ['y','yes','true'], ['n','no','false']

	if filt in notpay: shebang = shebang.filter(free=True)
	elif filt in pay: shebang = shebang.filter(free=False)
	else: pass
	return shebang

def query_window(shebang, filt):
	''' retrieve events starting or ending soon '''
	window = today + datetime.timedelta(days=7)
	if filt == 'starting':
		shebang = shebang.filter(evt_end__gt=F('evt_dte'))
		shebang = shebang.filter(evt_dte__gte=today,evt_dte__lte=window)
	elif filt == 'ending': 
		shebang = shebang.filter(evt_dte__lt=F('evt_end'))
		shebang = shebang.filter(evt_end__lte=window)
	else: pass
	return shebang

def get_stuff(request,dict_filters,pop_request=False):
	''' fetch query results '''

	filtered = False
	qualifier = ''
	dtg = 0 #days to go until date queried, used for 'also' in listings

	#all events ignoring date options
	shebang = retrieve_live_events()

	if pop_request:
		shebang_com = shebang.filter(com_cnt__gt=0) 
		shebang_rec = shebang.filter(rec_cnt__gt=0)
		shebang = shebang_rec | shebang_com 

	if dict_filters: filtered = True 

	#if reset or no specific query: return everything but today only
	reset = is_reset(request)
	if reset or not filtered: pass
		
	elif dict_filters:

		# short-circuit if evt_ref query eg event feature promotion
		if 'ref=' in dict_filters:
			filt = dict_filters['ref=']
			shebang = query_events(shebang, filt)

		else:

			for f in dict_filters.keys():
				filt = ''
				if f == 'qry=':
					filt = dict_filters[f]
				else:
					filt = dict_filters[f].lower()
					filt = re.sub('\+',' ',filt) #replace + with spaces

				if f == 'eve=' and dict_filters[f] != '':
					shebang = query_events(shebang, filt)
				if f == 'dte=' and dict_filters[f] != '':
					shebang, dtg = query_date(shebang,filt,qualifier)
				if f == 'met=' and dict_filters[f] != '':
					shebang = query_meta(shebang, filt)
				if f == 'tag=' and dict_filters[f] != '':
					shebang = query_tag(shebang, filt)
				if f == 'ven=' and dict_filters[f] != '':
					shebang = query_venue(shebang, filt)
				if f == 'cty=' and dict_filters[f] != '':
					shebang = query_city(shebang, filt)	
				if f == 'ctr=' and dict_filters[f] != '':
					shebang = query_country(shebang, filt)
				if f == 'zip=' and dict_filters[f] != '':
					shebang = query_postcode(shebang, filt)
				if f == 'tme=' and dict_filters[f] != '':
					shebang = query_time(shebang, filt)
				if f == 'pay=' and dict_filters[f] != '':
					shebang = query_free(shebang, filt)
				if f == 'win=' and dict_filters[f] != '':
					shebang = query_window(shebang, filt)
				if f == 'qry=' and dict_filters[f] not in ['', ['']]:
					shebang, dict_filters, qualifier, dtg = \
						query_terms(shebang,{'search':filt,},dict_filters)	
	else: pass

	count = shebang.count()
	
	count_msg, message = create_message(count,filters=dict_filters,
							qualifier=qualifier)

	return shebang, count, count_msg, message, dtg

def record_query(request, query, filters, terms, results, message):
	''' record query clicks '''
	instance = Query.objects.create()
	instance.query = query
	instance.filters = filters
	instance.terms = terms	
	instance.results = results	
	instance.message = message
	instance.meta = request.META
	instance.save()
	return 0

def journal_clicks(request, page, Model, ref):
	''' record journal clicks '''

	click_dict = {'Review':Click_Review,
					'People':Click_People, 'Essay':Click_Essay}

	title = ''
	
	try: journal = Model.objects.get(id=ref)
	except: journal = Model.objects.all().order_by('-date','-id').first()

	if page == "Essay": title = journal.title+': '+journal.sub_title
	else: title = journal.title

	instance = click_dict[page].objects.create(
		ind=journal.id, title=title, meta=request.META)

	return 0

def scrub_http_path(http_path):
	''' remove extraneous stuff from http_path 
		avoids it becoming too long to store and parse
	'''

	#remove repeated dates - we only need the last one
	finds = re.findall(r'dte=.*?\d{4}',http_path,flags=re.I)
	if len(finds) > 1:
		http_path = http_path.replace(finds[0],'',len(finds)-1)

	#remove repeated inputs - we only need the last one
	finds = re.findall(r'(cal=\w+)',http_path,flags=re.I)
	if len(finds) > 1:
		http_path = http_path.replace(finds[0],'',len(finds)-1)

	#catch any repated amp;amp;amp; etc in request
	while '&&' in http_path:
		http_path = http_path.replace('&&','&')
	while 'amp;' in http_path:
		http_path = http_path.replace('amp','&')

	return http_path


def page_clicks(request, search_qry):
	''' record page clicks '''

	http_path = request.META['PATH_INFO']
	http_path = scrub_http_path(http_path)
	string_meta = str(request.META)
	
	ip = None
	try:
		ip = request.META['HTTP_X_REAL_IP']
	except:
		pass

	click_dict = {
	'Review': (Journal, re.findall(r'/review/ind=(\d.*)$', http_path)),
	'People': (People, re.findall(r'/people/ind=(\d.*)$', http_path)),
	'Essay': (Essay, re.findall(r'/essay/ind=(\d.*)$', http_path)),
	}

	click_pages = ['Review','People','Essay']

	if any(i in string_meta for i in bot_identifier): page = 'Bot'
	elif any(i in string_meta for i in home_ips): page = 'Bot'
	elif ip is not None and any(ip.startswith(b) for b in bot_ips):page = 'Bot'
	elif http_path == '/nexus/': page = 'Home'
	elif http_path == '/': page = 'Home'
	elif '/review' in http_path: page = 'Review'
	elif '/people' in http_path: page = 'People'
	elif '/video/met=topical' in http_path: page = 'Video Topical'
	elif '/video/met=music' in http_path: page = 'Video Music'
	elif '/video/met=cine' in http_path: page = 'Video Cinema'
	elif '/video' in http_path: page = 'Video'
	elif '/essay' in http_path: page = 'Essay'
	elif '/curated' in http_path: page = 'Curators'
	elif '/add_event' in http_path: page = 'Add_Event'
	elif search_qry or '?qry=' in http_path: page = 'Search'
	elif 'pop=true' in http_path: page = 'Popular'
	elif any(re.search(r''+f+r'\w',http_path,flags=re.I) 
			for f in query_filters): page = 'Tagged'
	elif '/&sta' in http_path: page = 'Gen Prom'
	elif '&ref_' in http_path: page = 'Tagged_Prom'
	elif '/listings' in http_path: page = 'Home'
	elif '/home' in http_path: page = 'Home'
	elif '/events' in http_path: page = 'Home'
	elif '/clicks' in http_path: page = 'More'
	elif '/no_account' in http_path: page = 'NoAccount'
	elif '/loginpage' in http_path: page = 'LOGIN'
	elif '/feedback' in http_path: page = 'Feedback'
	elif '/submit_photo' in http_path: page = 'Submit'
	else: page = 'Other'

	instance = Click_Page.objects.create(page=page)
	instance.meta = request.META
	instance.path = http_path

	if 'HTTP_X_REAL_IP' in request.META.keys():
		instance.ip = request.META['HTTP_X_REAL_IP']
	elif 'HTTP_X_FORWARDED_FOR' in request.META.keys():
		instance.ip = request.META['HTTP_X_FORWARDED_FOR']
	elif 'HTTP_HOST' in request.META.keys():
		instance.ip = request.META['HTTP_HOST']

	# record any site general promotion
	if page == 'Gen Prom':
		prom_msg = re.search(r'gen_(\d+)$', http_path)
		if prom_msg:
			try:
				prom_msg = int(prom_msg.group(1))
				prom_msg = gen_preambles[prom_msg]
				instance.prom_msg = prom_msg
			except:
				pass

	#save
	instance.save()

	#record clicks
	ref = 0
	if page in click_pages:
		tmp = click_dict[page][1]
		if len(tmp) == 1: #i.e not empty and a single number
			try: ref = int(tmp[0])
			except: pass
			journal_clicks(request,page,click_dict[page][0],ref=ref,)

	return 0

def global_context(request,**kwargs):
	''' context using global variables '''

	top_pix_title, top_pix_place = '', '' 
	today = timezone.now().date()
	tomorrow = today + datetime.timedelta(days=1)
	authenticated, email = authenticate_poster(request)
	cities = []

	#with xml request: can only make www url request from www.sqwzl
	#we'll change urlspace to exclude www if on plain sqwzl.com
	www_recommend = True
	if 'HTTP_HOST' in request.META.keys():
		if 'www' not in request.META['HTTP_HOST']:
			www_recommend = False

	#get top of page photos
	bann_pix = Pix.objects.filter(banner=True)
	b = random.sample(list(bann_pix),1)[0]

	top_pix = b.title
	try:
		top_pix_set = Pix_Set.objects.filter(pix=b)
		top_pix_evt = Journal.objects.filter(pix_set=top_pix_set)[0]
		top_pix_title = top_pix_evt.title
		top_pix_place = top_pix_evt.place
	except:
		pass

	#record page click
	search_qry = False
	if 'qry' in kwargs.keys():
		search_ = kwargs['qry']
		if search_:
			if search_ != '' and search_ != ['']:
				search_qry = True

	page_clicks(request,search_qry)

	tod_name = today.strftime('%a').lower()
	tom_name = tomorrow.strftime('%a').lower()

	#collate cities
	if 'go_get_cities' in kwargs.keys():
		#specific to listings page which has its own get cities
		if not kwargs['go_get_cities']:
			pass
		else:
			cities = get_cities()
	else:
		cities = get_cities()

	#collate metas
	metas = [m.meta_tag for m in Meta_Tag.objects.filter(use_meta=True)]
	metas = sorted(metas)

	#primarily for Google
	seo_header = messages['meta_title']
	seo_descr = messages['meta_description']
	try: #in case other pages not home page
		seo_header = 'Sqwzl | ' + seo_headers[request_path][0]
		seo_descr = seo_headers[request_path][1]
	except:
		pass
		
	context = dict({
				'authenticated':authenticated,
				'tagline':messages['tagline'], 
				'byline':messages['byline'],
				'seo_header':seo_header, 'seo_descr':seo_descr,
				'request':request,'cities':cities,
				'metas':metas,
				'post':request.POST, #needed to add new venue button
				'urls':urls, #links for buttons to urlconfig
				'earliest':0, 'furthest':date_span,
				'furthest_date':furth_date,
				'tooltips':tooltips, 'page_error':messages['page_error'],
				'placeholders':placeholders,
				'signup_msg': messages['signup'],
				'today':today,'daytoday':today.weekday(),
				'tomorrow':tomorrow,
				'cookies':messages['cookies'],
				'copyright':messages['image_copyright'],
				'top_pix':top_pix,
				'img_prefix':img_prefix,
				'site_prefix':site_prefix,
				'media_url':media_url,
				'www_recommend':www_recommend,
				'top_pix_title':'The upcoming exhibition at the Espacio Gallery is called “Jabberwocky and other nonsense in the here and now”. I was thinking of Lewis Carroll',
				'top_pix_place':top_pix_place,
				'tod_name':tod_name,'tom_name':tom_name,
				'upd_time':timezone.now().isoformat(),
				},)		
	return context

def my_events_list(events,typeset,**kwargs):
	''' generate list of account holder;s events and other stats '''
	
	coming_up = {}

	if 'my_account' in kwargs.keys():
		ev_list = events.order_by('evt_nam',)	
		ev_live = ev_list.filter(evt_end__gte=today)
	else:
		ev_list = events.order_by('evt_dte')
		ev_live = ev_list.filter(evt_end__gte=today)
		
	ev_count = events.values_list().count()
	live_count = ev_live.values_list().count()

	if typeset == "overview":

		#count how many live coming up: for show_account
		live_future = [7,30] #next x days starting tomorrow
		
		#coming up today, in 7 and 30 days
		coming_up[0] = ev_live.filter(evt_dte__lte=today).count()
		coming_up["0_end"] = \
				ev_live.filter(evt_end=today).count()
		
		for f in live_future:
			f_dte = today + datetime.timedelta(days=f)
			coming_up[f] = \
				ev_live.filter(evt_dte__lte=f_dte).count()
			coming_up[str(f)+'_end'] = \
					ev_live.filter(evt_end__lte=f_dte).count()

		return ev_list, ev_count, ev_live, live_count, coming_up
		
	else:	
		return ev_list, ev_count

def my_events_contexts(request,me,**kwargs):
	''' returns contexts for my_events: allows diff functions to use '''

	msg, pre_filt, the_venue = '', '', ''
	click_dict = {}
	ev, live_done = [], []
	e_count, fetch_count, my_count = 0, 0, ''
	fetch_set = False
	good = False
	venue_search, event_search = False, False

	my_events = Event.objects.filter(account__email=me.email) \
								.prefetch_related('venue',)

	if 'good' in kwargs.keys(): good = kwargs['good']

	#filter for specified venue
	if 'ven' in kwargs.keys(): 
		my_events = my_events.filter(venue=kwargs['ven'])

	if 'msg' in kwargs.keys(): msg = kwargs['msg']

	#where my_events previously filtered
	if 'my_eve_search' in request.GET.keys():
		if request.GET['my_eve_search'] != '':

			if Venue.objects.filter(ven_nam = \
						request.GET['my_eve_search']).exists():
				venue_search = True

			if my_events.filter(evt_nam = \
						request.GET['my_eve_search']).exists():
				event_search = True

	#days for a particular event
	if 'evt_filt' in kwargs.keys() or event_search:
		if event_search:
			this_event = \
				my_events.filter(evt_nam=request.GET['my_eve_search'])[0]
		else:
			this_event = my_events.get(evt_ref=kwargs['evt_filt'])

		my_events = my_events.filter(freq_set=this_event.freq_set) \
							.order_by('evt_nam','freq_set','evt_dte')
		my_count = my_events.count()
		pre_filt = this_event.evt_nam
	
	if 'ven_filt' in kwargs.keys() or venue_search:
		#filter results by a venue
		#more likely here event names are unique
		if venue_search:
			v_name = request.GET['my_eve_search']
			the_venue = Venue.objects.get(ven_nam=v_name)
			my_events = my_events.filter(venue=the_venue)
			pre_filt = the_venue
		else:
			venue_search = True
			the_venue = Venue.objects.get(ven_ref=kwargs['ven_filt'])
			my_events = my_events.filter(venue=the_venue)
			pre_filt = the_venue

	if 'reset' in kwargs.keys():
		my_events = my_events.order_by('evt_dte','tme_beg','evt_nam')
		my_events,my_count = my_events_list(my_events,
											"all",my_account=True)

	if 'fetch_set' in kwargs.keys():
		if kwargs['fetch_set'] == True:
			#get an event or if part of a set, get the set
			ev.append(my_events.get(evt_ref=kwargs['ref']))
			if ev[0].freq_set:
					e = ev[0]
					ev = my_events.filter(freq_set=e.freq_set) \
										.filter(evt_dte__gte=today)
			my_events, fetch_set = ev, True

	if 'filter_action' in request.GET.keys():
		
		if request.GET['filter_action'] == 'Show all past events':
			my_events = my_events.filter(evt_end__lt=today)
			my_count = my_events.count()

			
		elif request.GET['filter_action'] == 'Show all live events':
			my_events = my_events.filter(evt_end__gte=today)
			my_count = my_events.count()

		else: #today filter and also fall_back position		
			my_events = my_events.filter()
			my_count = my_events.count()

	else:
		my_events,my_count = my_events_list(my_events,"today",my_account=True)

	#get clicks
	click = Click.objects.filter(acc_ref=me.acc_ref).filter(clicked__gt=0)
	for c in click: click_dict[c.evt_ref] = c.clicked
		
	context = dict({'my_events':my_events,'e_count':my_count,
					'pre_filt':pre_filt,'name':me.name,
					'filter_act':filter_event_actions,
					'fetch_set':fetch_set,
					'msg':msg,'can_edit':True,
					'good':good,
					'email':me.email},
				**global_context(request))
	
	return context

def my_venues_contexts(request,me,**kwargs):
	''' returns contexts for my_venues: allows diff functions to use '''

	msg = ''
	trace = "my_venues"

	if 'msg' in kwargs.keys():
		msg = kwargs['msg']
	if 'trace' in kwargs.keys():
		trace = kwargs['trace']

	my_venues = Venue.objects.filter(ven_ref__startswith=me.acc_ref) \
							.order_by('ven_nam')

	#only want venue objects
	if 'get_raw' in kwargs.keys(): return my_venues
	
	context = dict({'my_venues':my_venues,'msg':msg,'name':me.name,
				'trace':trace, 'updven_act':update_venue_actions,
				'email':me.email, 'can_edit':True},
				**global_context(request))

	return context

def list_my_venues(request,me):
	''' retrieve venues registered by account '''

	vid, to_append = '', ''
	
	#get venues
	venues = my_venues_contexts(request,me,get_raw=True)

	list_venues = [("nothing","My saved venues"),] #hint to click on select box
	for v in venues:
		vid = v.id
		if len(v.ven_zip) > 0:
			zipcode = " (" + v.ven_zip + ")"
		else:
			zipcode = ""
		to_append = v.ven_nam + ' ::: ' + v.ven_loc + zipcode
		
		if (vid, to_append) != ('', ''):
			if (vid, to_append) not in list_venues: #avoids multiple entries
				list_venues.append((vid,to_append))
	return list_venues

def grab_me(request,**kwargs):
	''' get account stuff once '''

	meme = {}
	authenticated, email = authenticate_poster(request)
	me = Account.objects.get(email=email)
	my_events = Event.objects.filter(account__email=me.email)

	if 'get_events' in kwargs.keys():
		get_events = kwargs['get_events']

	meme['email'] = email
	meme['authenticated'] = authenticated
	meme['is_superinputter'] = is_superinputter(request)
	meme['venues_list'] = []

	if email != '':
	
		meme['me'] = me
		meme['id'] = me.id
		meme['acc_ref'] = me.acc_ref
		meme['name'] = me.name

		ev_list, meme['my_evt_count'], meme['live'], \
		meme['live_count'], meme['coming_up'] = \
			my_events_list(my_events,"overview")

		meme['venues_list'] = list_my_venues(request,me)
		meme['venues_raw'] = my_venues_contexts(request,me,get_raw=True)

		if authenticated:
			meme['logged_in'] = True
			meme['is_locked'] = False

	else:
		meme['me'] = Account.objects.get(email=no_account)
		meme['logged_in'] = False

	return meme

def page_feature(request,objects,id_set,page,roll_show):
	''' return page details '''

	navigate, roll_page = '', 1

	#show next/prior/more requested
	if request.POST.get('page'):
		
		#get current prime id which serves as a page marker
		page = int(request.POST.get('page'))
		index = id_set.index(page)
		
		if request.POST.get('next'):
			#if current prime feat is not last in set, try getting next one
			#else keep the last one; remember 0-base indexing!
			if index < len(id_set)-1: page = id_set[index+1] 

		elif request.POST.get('prior'):
			#if current prime feat is not first in set, get previous one
			if index != 0: page = id_set[index-1]

	elif request.POST.get('load'):
		roll_page = int(request.POST.get('load')) + 1
		set_objects = objects[(roll_page-1)*roll_show:roll_page*roll_show]
		page = set_objects[0].id

	#navigation buttons
	if id_set.index(page) == 0: navigate = 'only_more'
	elif id_set[-1] == page: navigate = 'only_back'
	else: navigate = 'more_and_back'

	return page, navigate

def is_photoclick(request):
	''' checks if photoclick link '''
	is_ = False
	http_path = request.META['PATH_INFO'].lower()
	if re.search(r'&sta\d+_\d+&mp',http_path,flags=re.I):
		is_ = True
	return is_

def sections(request, Model, feature, feat_url, **kwargs):
	''' feature page '''

	context, f_set = {}, {}
	cur_pg, roll_show = 0, 20
	contrib = None
	contrib_name, e_field, e_reg, prime_pix = '', '', '', ''
	curated, numb_list = False, False
	other_essay_para = 9 #same as num of photo/links in model less 1 i.e prime
	essay_tag = None
	blogs = {}
	today = timezone.now().date()
	f_objects, r_objects = None, None
	prime_pix_all = None
	article_types = ['essay','write-up','curated']

	if feature == 'essay': feature = 'write-up'

	#gather all the objects and #truncate list to all that will be shown
	if 'contrib' in kwargs.keys():
		contrib = kwargs['contrib']
		if contrib:
			contrib = kwargs['contrib'][8:].strip('/')

			if Contributor.objects \
					.filter(pen_name__icontains=contrib).exists():
				objects = Essay.objects \
					.filter(contrib__pen_name__icontains=contrib,publish=True)

				#filter on field but only set as objects
				#if filtered queryset is not empty
				if 'field' in kwargs.keys():
					e_field = kwargs['field'][6:].strip('/')
					if e_field == 'None': e_field = ''
					f_objects = objects.filter(essay_field__icontains=e_field)
					if f_objects: objects = f_objects

				if 'region' in kwargs.keys():
					e_reg = kwargs['region'][7:].strip('/')
					if e_reg == 'None': e_reg = ''
					if e_reg != '':
						r_objects = \
							objects.filter(essay_field_reg__icontains=e_reg)
					if r_objects: objects = r_objects

				#if nothing then return all 
				#eg new curator but nothing submitted yet
				if not objects: objects = Essay.objects.all()

			else:
				objects = Essay.objects.all()
		else:
			objects = Essay.objects.all()

	else:
		objects = Model.objects.all()

	if Model == Essay: 
		objects = objects.filter(publish=True,status='APP')
		#remove if no contrib set; also avoids get_contrib error later on below
		objects = objects.filter(~Q(contrib=None))

	if Model == Essay and 'tag_' in kwargs.keys():
		if kwargs['tag_']: #i.e. not None
			tag = kwargs['tag_'][4:].strip()
			if tag != 'None':
				objects = objects.filter(essay_tag__tag__icontains=tag) \
								.distinct()
				essay_tag = tag

	#exclude future essays and order
	objects = objects.exclude(date__gt=today).order_by('-date','-id')

	set_objects = objects[:roll_show]
	max_pg = objects.count() // roll_show + 1

	#get list of all ids and set page to latest one
	id_set = list(objects.values_list('id',flat=True))
	page = id_set[0]

	#get details of what page/index to load
	if 'load_roll' in request.GET.keys():
		cur_pg = int(request.GET.get('cur_page'))
		if request.GET.get('load_roll').lower() == 'more':
			if cur_pg == 0: cur_pg = 1 #it's zero on initial load
			roll_page = cur_pg + 1
			set_objects = \
				objects[(roll_page-1)*roll_show:roll_page*roll_show]
			cur_pg = cur_pg + 1
		elif request.GET.get('load_roll').lower() == 'prior':
			roll_page = cur_pg - 1
			set_objects = \
				objects[(roll_page-1)*roll_show:roll_page*roll_show]
			cur_pg = cur_pg - 1
		else: pass
	
	elif 'index' in kwargs.keys():
		#for specific journal id requests
		if kwargs['index'] != None:
			try:
				page = kwargs['index'][4:]
				
				#chop off any stamp in path_info
				if is_photoclick(request):
					page = re.sub(r'&sta\d+_\d+&mp','',page,flags=re.I)
				
				page = int(page)
				id_set.index(page) #if error then doesn't exist
			except:
				page = id_set[0]

	#for next/prior
	page, navigate = page_feature(request,objects,id_set,page,roll_show)

	#compile primary feature either latest or requested
	prime = Model.objects.get(id=page)

	#collect other sections of essay/write-up 
	if Model == Essay:
		titles = [prime.blog2_title,prime.blog3_title,prime.blog4_title,
					prime.blog5_title,prime.blog6_title,prime.blog7_title,
					prime.blog8_title,prime.blog9_title,prime.blog10_title]
		blurbs = [prime.blog_2,prime.blog_3,prime.blog_4,prime.blog_5,
					prime.blog_6,prime.blog_7,prime.blog_8,prime.blog_9,
					prime.blog_10]
		urls = [prime.url_2,prime.url_3,prime.url_4,prime.url_5,prime.url_6,
					prime.url_7,prime.url_8,prime.url_9,prime.url_10]
		photos = [prime.photo_2,prime.photo_3,prime.photo_4,prime.photo_5,
					prime.photo_6,prime.photo_7,prime.photo_8,prime.photo_9,
					prime.photo_10]
		videos = [prime.video_2,prime.video_3,prime.video_4,prime.video_5,
					prime.video_6,prime.video_7,prime.video_8,prime.video_9,
					prime.video_10]

		#check if numbered list option selected
		j = 2
		if prime.numb_list: numb_list = True

		for i in range(other_essay_para):
			p, v, t, b, u = photos[i], videos[i], titles[i], blurbs[i], urls[i]
			if not p and not v and not t and not b: continue

			blogs[i] = {}
			if numb_list and t:
				blogs[i]['title'] = str(j)+'. '+t
				j = j + 1
			else:
				blogs[i]['title'] = t
				numb_list = False
			blogs[i]['photo'] = p
			blogs[i]['video'] = v
			blogs[i]['blurb'] = b
			blogs[i]['url'] = u

		#get contrib
		contrib = Contributor.objects.filter(essay__title=prime.title)
		contrib = contrib[0] #in case 2 were assigned

		if 'curated' in request.META['PATH_INFO'] and contrib.freq == 'REG':
			curated = True
			feature = 'curators'
			if Model == Essay: feature = 'curated'

	#let's get all the details for features to list
	for o in set_objects: f_set[o] = o
		
	#get lead picture
	if Model == Journal:
		prime_pix = prime.pix_set.prime_pix #returns a string	
		if len(prime_pix) > 0:
			prime_pix = str(Pix.objects.get(title=prime_pix))
		else:
			prime_pix = str(pix_[0])

		#get other photos in set
		pp = prime.pix_set.pix.all()
		prime_pix_all = []
		for p in pp:
			prime_pix_all.insert(0,p.title)

	else:
		try:
			prime_pix = str(prime.pix)
		except:
			pass

	#plurals
	plurals = {'people':'people',
				'review':'reviews',
				'write-up':'write-ups',
				'curators':'curators',
				'curated':'curated',
				}

	context = {'feature':feature,'f_set':f_set,'feat_url':feat_url,
				'curated':curated,'contrib':contrib,
				'feat_plural':plurals[feature],
				'e_field':e_field,'e_reg':e_reg,
				'prime':prime,'prime_pix':prime_pix,
				'prime_pix_all':prime_pix_all,
				'blogs':blogs,'essay_tag':essay_tag,
				'article_types':article_types,
				'numb_list':numb_list,
				'cur_pg':cur_pg,'max_pg':max_pg,'roll_show':roll_show,
				'page':page,'navigate':navigate} 

	return context

@require_http_methods(["GET","POST"])
def features(request,**kwargs):
	''' handles section features, gets context and returns to http '''

	#set up dictionary for Models
	feat_url, feature = 'review', None
	f_dict = {'review': Journal,'people':People,'essay':Essay,
				'curated':Essay}
	f_url = {'review':urls['review'],'people':urls['people'],
			'essay':urls['essay'],'curated':urls['curated']}

	#find which feature has been called
	for k in f_dict.keys():
		try: 
			feature = re.search(k,request.META['PATH_INFO']).group(0)
			feat_url = f_url[feature] 
		except: continue

	context = dict(
				sections(request,f_dict[feature],feature,feat_url,**kwargs),
				**global_context(request))

	#replace seo_header with article title if article by curator 
	if 'curated/contrib=' in request.META['PATH_INFO']:
		try:
			context['seo_header'] = context['prime'].title
		except:
			pass
	
	return render(request,"nexus/feature.html",context)

@require_http_methods(["GET","POST"])
def contributors(request,**kwargs):
	''' handles contributing curators '''

	contribs = []
	reg_contribs = Contributor.objects.filter(freq='REG')

	#curators may have more than one field
	#to simplify html template we create each curator+field as a class obj 
	class curator():
		def __init__(self, contrib, field, field_reg):
			self.photo = contrib.photo
			self.pen_name = contrib.pen_name
			self.field = field
			self.field_reg = field_reg
			self.blurb = contrib.blurb
			self.email = contrib.email
			self.social_url = contrib.social_url
			self.social_name = contrib.social_name
			
	#all the different fields 
	fields = (
				('field','field_reg'),
				('field_2','field_2_reg'),
				('field_3','field_3_reg')
			)
	
	#for each regular curator, create a unique self+field combination
	for r in reg_contribs:
		for f in fields:
			field, field_reg = None, None
			field = getattr(r, f[0])
			if not field or field.strip() == '':
				continue #nothing here
			field_reg = getattr(r, f[1])
			c = curator(r,field,field_reg)
			contribs.append(c)

	context = dict({'contribs':contribs},
				**global_context(request))
	return render(request,"nexus/contributors.html",context)

@require_http_methods(["GET","POST"])
def video(request,**kwargs):
	''' videos page '''

	vid_tag, vid_nam, vid_met, vid_ref = '', '', '', ''
	called, called_tag, called_name, _tag, memo, descr = '', '', '', '', '', ''
	cur_pg, max_pg, roll_show, vid_num = 1, 1, 12, 0
	call_vid = False
	vid_attr = ['name_', 'meta_', 'tag_', 'ref_', 'number_']

	def call_vids_by_tag(tag):
		return Video.objects.filter(
				vid_tag__tag__icontains=tag).distinct().order_by('-created')
	def call_vids_by_name(name):
		return Video.objects.filter(name__icontains=name).order_by('-created')
	
	#extract direct call filter for video to show
	for a in vid_attr:
		if a in kwargs.keys() and kwargs[a] != None and kwargs[a] != '':
			if a == 'number_': called = int(kwargs['number_'][4:].strip())
			else: called = kwargs[a][4:].strip() #remove leading colon
			call_vid = True
			break

	#get video(s) if filter exists
	if call_vid == True:
		if a == 'name_': 
			vids = call_vids_by_name(called)
			called_name = called

		elif a == 'meta_': vids = Video.objects.filter(
					vid_meta__meta_tag__icontains=called).order_by('-created')

		elif a == 'tag_': 
			vids = call_vids_by_tag(called)
			called_tag = called

		elif a == 'ref_':
			vids = Video.objects.filter(id=vid_ref).order_by('-created')
			called = journals[0].name + "|" + journals[0].title

	else:
		vids = Video.objects.all().order_by('-created')
		#set max page
		max_pg = vids.count() // roll_show + 1
	
	memo = called.title()

	if 'load_roll' in request.GET.keys():
		cur_pg = int(request.GET.get('cur_page'))
		invalid = ['','/']
		if request.GET.get('called_tag') not in invalid:
			called_tag = request.GET.get('called_tag').lower()
			vids = call_vids_by_tag(called_tag)
		elif request.GET.get('called_name') not in invalid:
			called_name = request.GET.get('called_name').lower()
			vids = call_vids_by_name(called_name)
		else: pass

		#set max page
		max_pg = vids.count() // roll_show + 1

		if request.GET.get('load_roll').lower() == 'more':
			if cur_pg == 0: cur_pg = 1 #it's zero on initial load
			roll_page = cur_pg + 1
			vids = \
				vids[(roll_page-1)*roll_show:roll_page*roll_show]
			cur_pg = cur_pg + 1
		elif request.GET.get('load_roll').lower() == 'prior':
			roll_page = cur_pg - 1
			vids = \
				vids[(roll_page-1)*roll_show:roll_page*roll_show]
			cur_pg = cur_pg - 1
		else: pass
	else:
		vids = vids[:roll_show]

	context = dict({'videos':vids,'video_page':True,
					'cur_pg':cur_pg,'max_pg':max_pg,'roll_show':roll_show,
					'called_name':called_name,'called_tag':called_tag,
					'memo':memo,'descr': descr,
					'path':site_prefix+request.META['PATH_INFO']
					},
				**global_context(request))
	
	return render(request,"nexus/video.html",context)

def get_form_errors(error_forms,other_nots):
	''' retrieve fields with errors '''

	good = False

	#create list with error fields to list
	err = [key for f in error_forms for key in f.errors.keys()]

	#add fields not in field validation
	for o in other_nots:
		if o not in err: 
			err.append(o)

	#remove foreign key fields not relevant
	try:
		err.remove('venue') 
	except:
		pass

	if len(err) == 0: good = True

	return err, good

def get_listings_qry(qry_path):
	''' get all the tagged filters and split out '''
	qry = ''
	try:
		qry = re.findall(r'.*events/(.*)', qry_path)[0]
	except:
		qry = re.findall(r'.*listings/(.*)', qry_path)[0]
	return qry 

def get_query_filters(qry_path):
	''' return dictionary of query calls of type: event/<filter>='' '''

	filter_dict = {}
	dte_long = {
		'tod':'today',
		'tom':'tomorrow'
	}

	#return filters in query path
	filtered = [f for f in query_filters if f in qry_path]

	#store all query path filters in dict 
	if any(filtered):

		hashtags = get_listings_qry(qry_path)
		hashtags = re.sub('&amp;','&',hashtags)
		hashtags = hashtags.strip('&')
		hashtags = hashtags.strip('/')
		filter_dict['prior'] = hashtags
		hashtags = hashtags.split('&')

		#track where we don't want multi-tags eg dates, times
		no_dbl, done = ['dte=','tme=','met=','zip='], []

		for f in filtered:
			fil = ''
			for h in hashtags:
				#if fil in fil=hashtag
				if f in h:
					to_add = h[4:].strip()
					if fil == '' or (f in no_dbl and f in done): 
						fil = to_add
					else: 
						if to_add not in fil:
							fil = fil + '||' + h[4:].strip()
						else:
							pass
				done.append(f)
			filter_dict[f] = fil

		#replace tod/tom with long versions
		if 'dte=' in filter_dict.keys():
			dte_ = filter_dict['dte='].lower()
			if dte_ in dte_long.keys():
				filter_dict['dte='] = dte_long[dte_]

		if 'qry=' in filter_dict.keys():
			#if any spaces then replace with '|'
			#catches cases e.g. initially 'families Kids' query
			#correctly returned as two terms but user then adds
			#Time eg Weekend; in this case there's no POST
			#and 'families kids' being treated as single term
			#instead of split into two terms
			filter_dict['orig='] = filter_dict['qry=']
			filter_dict['qry='] = filter_dict['qry='].replace(' ','|')
			qry_ = 'qry='+filter_dict['qry=']
			prior_ = filter_dict['prior']
			filter_dict['prior'] = prior_.replace(qry_,'')

	elif '/listings/' in qry_path or '/events/' in qry_path:
		filter_dict['qry='] = get_listings_qry(qry_path)

	return filter_dict

def get_pg(pg,max_pg):
	''' get page numbers to show '''
	if pg < 4:
		return 1, 2, 3, 4, 5
	elif pg > max_pg - 2:
		return max_pg-4, max_pg-3, max_pg-2, max_pg-1, max_pg
	else:
		return pg-2, pg-1, pg, pg+1, pg+2

@require_http_methods(["GET","POST"])
def venuemap(request, **kwargs):
	''' prepares url for google static map for venues in listings '''

	req_zip = request.META['PATH_INFO']
	req_zip = req_zip[req_zip.find('map')+4:]
	mapurl = goog_staticmap_1 + req_zip + \
				goog_staticmap_2 + req_zip + \
				goog_staticmap_3
	content = "<img class='ven_map' src='" + mapurl + "'>"
	data = {'staticmap': content,}
	return JsonResponse(data)

def get_photoclick(request_path,orig_path,results,message,dict_filters,social):
	''' populate photoclick data - social media '''

	photo_, photoclick, gen_prom, set_stamp = None, {}, False, False
	feat_types = ['people','review']
	safe_types = ['kids','family']

	#set conditions for choosing a sqwzl branded photo
	#gen promotion for link to home page or fb scrapes
	sqwzl_ph = random.choice((False,False))
	safe_ph = False

	if re.match(r'/&sta\d',orig_path): gen_prom = True
	if gen_prom: sqwzl_ph = True
	if re.search(r'ref=\d',orig_path): sqwzl_ph = False
	if any(r in request_path for r in feat_types): sqwzl_ph = True
	if any(r in request_path for r in safe_types): safe_ph = True

	#collate metas
	M = Meta_Tag.objects.filter(use_meta=True)
	P = Pix.objects.all()
	S = Pix_Stamp.objects.all()

	request_path = request_path[1:] #remove leading forward slash
	click_title = "What's On"

	#seach for any banner pix with one tag that matches tag request
	#we'll use for photoclick only; not pixtop
	#for future dev: to extend functionality to '&cty=' request
	t_pix, photo_done = None, False
	req_tags = ['met=', 'tag=', 'cty='] #nb. pix sought in this order

	orig_path = orig_path[1:] #strip leading slash
	pS = S.filter(stamp=orig_path)


	if sqwzl_ph or safe_ph: #gen_promotion, fb, tw:sqwzl_ph=True
		#sample from last x items to introduce variety
		#but based on latest photos added

		if safe_ph:
			photo_ = Pix.objects.filter(
						title__icontains='social_media_safe')
		else:	
			photo_ = Pix_Set.objects.get(title__istartswith='SocialMediaPix')
			photo_ = photo_.pix.all()
		photo_ = random.sample(list(photo_),1)[0]
		photo_ = img_prefix + photo_.title
		photo_done = True
		
		#save stamp
		Ps = Pix_Stamp(stamp=orig_path,photo=photo_)
		try: Ps.save()
		except: pass #already exists and throws duplicate key error

	elif pS: #tw:sqwzl_ph=False
		#if a photo for stamp exists then use that
		#stamp is set before social_media post so
		#this should already exist when platforms check meta_tags
		photo_ = pS[0].photo
		photo_done = True
		dada = 1

	else:
		set_stamp = True
	

	if set_stamp:

		R = results.exclude(Q(photo='') & Q(venue__photo='') & \
						Q(photo_url=None) & Q(venue__photo_url=None))

		if R:

			typ = ''

			r = random.sample(list(R),1)[0]
			
			if r.photo: 
				photo_ = media_url + r.photo.name
				typ = 'photo'
				photo_done = True

			elif r.photo_url:
				photo_ = r.photo_url
				typ = 'photo_url'

			elif r.venue.photo:
				photo_ = media_url + r.venue.photo.name
				typ = 'photo_venue'
				photo_done = True

			elif r.venue.photo_url:
				photo_ = r.venue.photo_url
				typ = 'venue_photo_url'

			if 'url' in typ: #test if external photo exists
				#resize as social media require min size
				ph_name = photo_.split('/')[-1] #get raw file name
				#timestamp to make unique so social media refreshes on request
				stamp = datetime.datetime.now().strftime('%d%m%y_%H%M%S')
				f_stamp = 'e_stamp/' + stamp + '_' + ph_name
				f_path = os.path.join(os.getcwd() + '/media/' + f_stamp)

				#retrieve and save
				with urllib.request.urlopen(photo_) as f:
					
					if f.status == 200:

						photo_ = media_url + f_stamp

						pho = f.read()
						with open(f_path, mode='w+b') as k:
							k.write(pho)

						photo_done = True

					else:
						photo_ = None
						#	pass #eg 404, Forbidden etc error


		if not photo_done:
			
			if any(tag_ in request_path.lower() for tag_ in req_tags):
				for _tag in req_tags:
					if not photo_done:
						tag_ = re.findall(r'.*'+_tag+r'(.*)$',
										request_path,flags=re.I)
						if tag_:
							tag_ = tag_[0]
							pos = tag_.find('&')
							if pos != -1:
								#remove any succeeding tags
								tag_ = tag_[:pos] 
							tag_ = tag_.replace('|',' ')
							tag_ = tag_.split()
							
							for t in tag_:
								
								if _tag == 'met=':
									
									#pix from class Meta_Tag photo attribute 
									t_ = M.filter(meta_tag__iexact=t)

									if t_:
										photo_ = media_url + t_[0].photo.name
										photo_done = True
										break
								
								elif _tag == 'tag=':
									
									#pix from class Meta_Tag photo attribute
									t_ = M.filter(tag__tag__iexact=t)
									if t_:
										photo_ = media_url + t_[0].photo.name
										photo_done = True
										break

								elif _tag == 'cty=':

									specials = ['|','&']

									_tag_cty = \
									re.findall(r'cty=(.*)',
												request_path,flags=re.I)[0]

									for s in specials:
										pos = _tag_cty.find(s)
										if pos != -1:
											_tag_cty = _tag_cty[:pos]

									#pix from class Pix - pixcity name
									t_ = P.filter(title__istartswith='pixcity',
													location__iexact=_tag_cty)

									if not t_:
										#try country
										_tag_e = \
										Event.objects.filter(
											venue__ven_cty__iexact=_tag_cty) \
																	.first()
										_tag_ctr = _tag_e.venue.ven_ctr

										t_ = P.filter(
											title__istartswith='pixcity',
											location__iexact=_tag_ctr)

									if t_:
										photo_ = img_prefix + t_[0].title 
										photo_done = True
										break


		if not photo_done:
			photo_ = img_prefix + 'sqwzl_logo.png'

		#save stamp
		Ps = Pix_Stamp(stamp=orig_path,photo=photo_)
		Ps.save()

	#replace spaces in request_path, create title
	request_path = request_path.replace(' ','%20')

	# count
	count = results.count()
	if count > 1000:
		count = int(count/1000)*1000
	elif count > 100:
		count = int(count/10)*10
	count = str(format(count,','))

	if 'eve=' in dict_filters.keys() and 'dte=' in dict_filters.keys():
		message = re.sub(dict_filters['dte='],'',message,flags=re.I)

	message = message.replace('  ',' ')
	message = message.replace('Next 90 Days','')
	message = message.replace('(Late)','')
	message = message.strip()


	# prepare filter
	fil = None
	if 'cty=' in dict_filters.keys():	fil = 'cty'
	elif 'met=' in dict_filters.keys(): fil = 'met'
	elif 'tag=' in dict_filters.keys(): fil = 'tag'

	
	# get adjective
	rnd_adj = ''

	if fil is not None:

		if fil == 'cty':
			rnd_adj = ' ' + random.choice(adjectives['positive'])

		elif fil in ['met','tag']:
			# relies on message starting with tag/met
			subj = message.split()[0].strip()
			subj = subj.lower()

			if subj in adjectives['tags'].keys():
				
				# somtimes replace music with gigs
				if subj == 'music':
					subj = random.choice(['music','gigs'])
				
				rnd_adj = ' ' + random.choice(adjectives['tags'][subj])	
	
	else:
		message = re.sub(r' events in','',message,flags=re.I )
		message = re.sub(r' events','',message,flags=re.I )

	# compose message
	if 'eve=' not in dict_filters.keys():
		message = count + rnd_adj.title() + ' ' + message
	elif 'eve=' in dict_filters.keys():
		message = 'Upcoming | ' + message
	elif 'tag=' in dict_filters.keys():
		message = "What's On | " + message
	
	if 'ref=' in dict_filters.keys():
		message = results[0].evt_nam.title()

	message = message.title()

	# general promotion
	if gen_prom:
		i = re.findall(r'&gen_(\d+)',request_path,flags=re.I)

		try: #in case gen_ is malformed for some reason
			if i:
				i = int(i[0])
				click_title = gen_preambles[i]
				i_ph = Pix.objects.filter(text__iexact=click_title)
				if i_ph:
					photo_ = i_ph[0].title
			else:
				click_title = random.sample(gen_preambles,1)[0]
		except:
			click_title = random.sample(gen_preambles,1)[0]
	else:
		click_title = message.strip()

	#submit_photos
	if 'submit_photo' in request_path:
		t_ = M.filter(meta_tag__iexact='Submissions')
		if t_:
			photo_ = media_url + t_[0].photo.name
			click_title = 'Calling all visual storytellers, photograhers and artists - show off your work in our new online gallery'

	#primarily for Social Media post links
	photo_ = photo_.replace('%20','%2520') #double encoding issues with '%20'
	#https://stackoverflow.com/questions/16084935/a-html-space-is-showing-as-2520-instead-of-20

	blurb = messages['photoclick_tag']
	if re.search(r'ref=\d',orig_path):
		blurb = results[0].descr

	photoclick = {'path':site_prefix+orig_path,
				'title':click_title,
				'photo':photo_,
				'blurb':blurb,
				'sqwzl_ph':sqwzl_ph,
				}

	return photoclick

def next_ven_open_date(event):
    ''' find first open day for venues '''

    found = False
    today = datetime.date.today()

    #real ref_date will be latter of today and evt_dte in arg
    ref_date = max(today, event.evt_dte)
    ref_day = ref_date.weekday()

    v = event.venue
    open_dict = {0:v.mon_op,1:v.tue_op,2:v.wed_op,3:v.thu_op,
                    4:v.fri_op,5:v.sat_op,6:v.sun_op}

    #loop through weekdays to see where opening times exist
    #starting with reference date given
    for day in range(ref_day,ref_day+7): 
        if day > 6: #if into following week
            d = day - 7 #shift back to Mon,Tue etc
        else: 
            d = day
        if open_dict[d] != '00:00':
            #days to first open day; could be zero
            d = day - ref_day 

            #get date, weekday and construct text to show
            ven_open = ref_date + datetime.timedelta(days=d)
            #but cannot be later than end fate
            ven_open = min(ven_open,event.evt_end)
            ven_open_day = ven_open.weekday()
            ven_open = ven_open.strftime(' %a, %d %b')
            found = True
            break

    #save_event should not allow events to be created with venue default
    #but with no venue default times. Just in case: use today as date
    if not found: ven_open = today.strftime(' %a, %d %b')

    return ven_open


def next_evt_open_date(event):
    ''' find first open time for event '''
    
    found = False
    today = datetime.date.today()

    #real ref_date will be later of today and evt_dte in arg
    ref_date = max(today, event.evt_dte)
    ref_day = ref_date.weekday()

    if event.ven_tme:
        evt_open = next_ven_open_date(event)

    else:
    	e = event
    	open_dict = {0:e.mon,1:e.tue,2:e.wed,3:e.thu,4:e.fri,5:e.sat,6:e.sun}

    	#loop through weekdays to see where open days (checked) exist
    	#starting with reference date given
    	for day in range(ref_day,ref_day+7):
    		if day > 6: #if into following week
    			d = day - 7 #shift back to Mon,Tue etc
    		else: 
    			d = day
    		if open_dict[d]:
    			#days to first open day; could be zero
    			d = day - ref_day 

    			#get date, weekday and construct text to show
    			evt_open = ref_date + datetime.timedelta(days=d)
    			#but cannot be later than end fate
    			evt_open = min(evt_open,event.evt_end)
    			evt_open = evt_open.strftime(' %a, %d %b')
    			found = True
    			break

    	#save_event should not allow events to be created with venue default
    	#but with no venue default times. Just in case: use today as date
    	if not found: evt_open = today.strftime(' %a, %d %b')

    return evt_open


def convert_text_date(text):
    ''' convert text date to python '''
    
    date = timezone.now().date()
    year = date.year

    if re.search(r'\d{4}',text):
        pass #year exists
    else:
        text += ' ' + str(year)
   
    if datetime.datetime.strptime(text,' %a, %d %b %Y'):
        date = datetime.datetime.strptime(text,' %a, %d %b %Y')
        date = date.date()

    return date


def listing_img(r):
	''' event image for listings page '''
	img = img_prefix+'/sqwzl_logo.png' # default
	if r.photo: 			img = media_url + r.photo
	elif r.photo_url: 		img = r.photo_url
	elif r.venue.photo:		img = media_url+r.venue.photo
	elif r.venue.photo_url:	img = r.venue.photo_url
	return img


def next_date_hint(r, dtg):
	''' text to hint next date for event 
		dtg (days-to-go) comes from first running def event
		r.dtg are run by cron job (at least in production) 
		around 1am every night
	'''

	hint = ''
	today = datetime.date.today()
	tomorrow = today + datetime.timedelta(days=1)
	
	if r.dtg_int == 0:
		if r.evt_dte == today and r.evt_dte < r.evt_end:
			hint = 'starts today'
		elif r.evt_end == today and r.evt_dte < r.evt_end:
			hint = 'closes today'
		elif r.evt_dte == r.evt_end:
			hint = 'only today'
		else:
			if convert_text_date(next_evt_open_date(r)) > today:
				hint = 'next'
			else:
				if dtg > 0: 'also'
				hint += ' on today'

	elif r.dtg_int == 1:
		if r.evt_dte == tomorrow and r.evt_dte < r.evt_end:
			hint = 'starts tomorrow'
		elif r.evt_end == tomorrow and r.evt_dte < r.evt_end:
			hint = 'closes tomorrow'
		elif r.evt_dte == r.evt_end:
			hint = 'only tomorrow'
		else:
			if dtg > 1: hint = 'also '
			hint +=  'on tomorrow'

	elif r.evt_dte < today:
		if r.dtg_int < dtg: hint = 'also '
		hint += 'next'

	else:
		if r.evt_dte < r.evt_end:
			hint = 'starts'
		else:
			hint = 'on'

	return hint

def next_ven_open_day(venue):
    ''' find first open day for venues '''
    
    days = ''
    v = venue
    if v.mon_op != '00:00': days += 'Mo '
    if v.tue_op != '00:00': days += 'Tu '
    if v.wed_op != '00:00': days += 'We '
    if v.thu_op != '00:00': days += 'Th '
    if v.fri_op != '00:00': days += 'Fr '
    if v.sat_op != '00:00': days += 'Sa '
    if v.sun_op != '00:00': days += 'Su '
    return days.strip()

def get_event_days(r):
	''' days of week of event returned as text '''
	days = ''
	if not r.ven_tme:
		if r.mon: days += 'Mo '
		if r.tue: days += 'Tu '
		if r.wed: days += 'We '
		if r.thu: days += 'Th '
		if r.fri: days += 'Fr '
		if r.sat: days += 'Sa '
		if r.sun: days += 'Su '
		days = days.strip()
	else:

		days = next_ven_open_day(r.venue)
	return days


@require_http_methods(["GET","POST"])
def event(request, **kwargs):
	''' prepares database query parameters for get_stuff '''

	t_start = datetime.datetime.now()

	today = timezone.now().date()
	search_qry, orig_qry = '', ''
	ending = today + datetime.timedelta(days=7)
	results, dict_filters, photoclick = [], {}, {}
	found_stuff, filtered = True, False
	pop_request, pop_reset = False, False
	landing_page, stamp, social = False, False, None
	max_reveal = 20
	request_pg = 1
	dtg = 0
	min_pg, pg_a, pg_b, pg_c, pg_d, pg_e = 1, 1, 2, 3, 4, 5
	page_nos = ['min_pg','pg_a','pg_b','pg_c','pg_d','pg_e','max_pg']
	landings = ['/listings','/listings/','/']
	socials = ['facebook','twitter']

	#get path; remove any timestamp and extraneous stuff
	http_path = request.META['PATH_INFO'].lower()
	http_path = scrub_http_path(http_path)
	orig_path = http_path #to save later

	if is_photoclick(request):
		http_path = re.sub(r'&sta\d+_\d+&mp','',http_path,flags=re.I)
		stamp = True
		for s in socials:
			if re.search(r''+s,str(request.META),flags=re.I):
				social = s
				break

	# check if resets
	reset = is_reset(request)
	if 'pop=true' in http_path:
		pop_reset = True


	if reset and not pop_reset: pass

	else: #get queries typed in search box
		search_qry = ''
		try:
			try:
				orig_qry = request.POST['query']
				search_qry = request.POST['query'].lower()
			except: 
				orig_qry = request.GET['query']
				search_qry = request.GET['query'].lower()

			orig_qry = orig_qry.replace(r'{search_term_string}',r'')
			search_qry = search_qry.replace(r'{search_term_string}',r'')
			search_qry = search_qry.split(' ')

		except: pass
		
		finally:
			#also add all of query as typed as user may have
			#typed eg part of venue name, event name etc
			if search_qry != '':
				if orig_qry not in search_qry: search_qry.append(orig_qry)
	
		#get query filters and hashtags		
		if '/listings/' in http_path or '/events/' in http_path:
			dict_filters = get_query_filters(http_path)

			#cases where qry= typed directly in browser
			if orig_qry == '':
				if 'orig=' in dict_filters.keys():
					if dict_filters['orig='] != '':
						orig_qry = dict_filters['orig=']
				
	if search_qry != '': 
		dict_filters['qry='] = search_qry
		dict_filters['orig='] = orig_qry
	else:
		if 'qry=' in dict_filters.keys():
			del dict_filters['qry=']

	#set for scrolling
	if http_path in landings and orig_qry == '': landing_page = True

	
	#so can hide the 'Reset events' button if false
	if dict_filters: filtered = True

	# set if popular request ie commented, recommended
	if 'pop=' in  dict_filters.keys():
		if dict_filters['pop='] == 'true':
			pop_request = True

	t_mid_5 = datetime.datetime.now()

	results, r_count, count_msg, message, dtg = \
							get_stuff(request,dict_filters,pop_request)

	t_mid_50 = datetime.datetime.now()

	#social media link click - only do if stamp in url
	#to avoid doing with every request as urlrequest is time costly
	if stamp and r_count >= 1:
		photoclick = get_photoclick(http_path,orig_path,results,
						message,dict_filters,social)

	cities = None
	go_get_cities = False #assume we have results with cities
	if r_count == 0: 
		found_stuff = False
		go_get_cities = True #collate all cities
	else:
		cities = results.filter().values_list('venue__ven_cty',flat=True) \
						.order_by('venue__ven_cty').distinct('venue__ven_cty')


	t_mid_60 = datetime.datetime.now()


	# pagination
	max_pg = math.ceil(r_count / max_reveal)

	for p in page_nos:
		if p in request.GET.keys():
			request_pg = int(request.GET[p])
			pg_a,pg_b,pg_c,pg_d,pg_e = get_pg(request_pg, max_pg)

	start_reveal = (request_pg - 1) * max_reveal
	end_reveal = start_reveal + max_reveal
	results = results[start_reveal:end_reveal]


	t_mid_80 = datetime.datetime.now()

	#record query
	try:
		if orig_qry != '':
			terms = '' #need to sort this
			record_query(request, query=orig_qry, filters=dict_filters, 
					terms=terms, results=r_count, message=message)
	except: pass

	filter_cty, filter_met, filter_dte, filter_tme = '','','',''
	try: filter_met = dict_filters['met=']
	except: pass
	try: filter_cty = dict_filters['cty=']
	except: pass
	try: filter_dte = dict_filters['dte=']
	except: pass
	try: filter_tme = dict_filters['tme=']
	except: pass


	# convert results to JSON
	events = []
	for r in results:
		e = {
		'evtRef': 		r.evt_ref,
		'nextDateHint':	next_date_hint(r,dtg),
		'nextDate': 	next_evt_open_date(r),
		'fromDate': 	r.evt_dte.strftime(' %A, %d %B'),
		'toDate': 		r.evt_end.strftime(' %A, %d %B'),
		'days': 		get_event_days(r),
		'fromTime': 	r.tme_beg,
		'toTime': 		r.tme_end,	
		'title': 		r.evt_nam,
		'meta': 		r.meta_tag.meta_tag,
		'descr':		r.descr.capitalize(), # need func to cap 1st char in sentence
		'img':			listing_img(r),
		'venName': 		r.venue.ven_nam,
		'venAddr': 		r.venue.ven_add,
		'venCity':		r.venue.ven_cty,
		'venZip':		r.venue.ven_zip,
		'venCtr':		ctr_dict[r.venue.ven_ctr],
		'tags':			list(r.evt_tag.all().values_list('tag',flat=True)),
		'recCount': 	r.rec_cnt,
		'comCount': 	r.com_cnt,
		'website': 		r.inf_url,
		}

		e = json.dumps(e)
		events.append(e)


	context = dict({
					'events':events, 'orig_qry':orig_qry,
					'count_msg':count_msg, 'message':message,
					'filter_dict':dict_filters,
					'cities':cities,'dtg':dtg,
					'filt_cty':filter_cty,'filt_met':filter_met,
					'filt_dte':filter_dte,'filt_tme':filter_tme,
					'ending':ending,'media_url':media_url,
					'filtered':filtered,'cur_pg':request_pg,
					'pg_a':pg_a,'pg_b':pg_b,'pg_c':pg_c,
					'pg_d':pg_d,'pg_e':pg_e,
					'min_pg':min_pg,'max_pg':max_pg,
					'landing_page':landing_page,
					'listings_page':True,
					'found_stuff':found_stuff,
					'photoclick':photoclick,
					}, 
					**global_context(request,msg=message,qry=search_qry,
							go_get_cities=go_get_cities))

	# ensure results cities gets used
	try: context['cities'] = cities
	except: pass
	
	# dump as json so js can use it
	cities_ = {}
	if context['cities']:
		C = list(context['cities'])
		for c in C:
			cities_[c] = {'name':c}
		context['cities'] = json.dumps(cities_)


	# dump as json so js can use it
	metas_ = {}
	if context['metas']:
		M = list(context['metas'])
		for c in M:
			metas_[c] = {'name':c}
		context['metas'] = json.dumps(metas_)



	t_end = datetime.datetime.now()

	'''
	_5 = round((t_mid_5-t_start).total_seconds(),4)
	_50 = round((t_mid_50-t_mid_5).total_seconds(),4)
	#_55 = round((t_mid_55-t_mid_50).total_seconds(),4)
	#_57 = round((t_mid_57-t_mid_55).total_seconds(),4)
	_60 = round((t_mid_60-t_mid_50).total_seconds(),4)
	#_70 = round((t_mid_70-t_mid_60).total_seconds(),4)
	_80 = round((t_mid_80-t_mid_60).total_seconds(),4)
	_end = round((t_end-t_mid_80).total_seconds(),4)
	_all = round((t_end-t_start).total_seconds(),4)


	print('-'*40)
	print('to 5'.ljust(7),_5,'secs'.ljust(12),'{:.1%}'.format(_5/_all))
	print('to 50'.ljust(7),_50,'secs'.ljust(12),'{:.1%}'.format(_50/_all))
	#print('to 55'.ljust(7),_55,'secs'.ljust(12),'{:.1%}'.format(_55/_all))
	#print('to 57'.ljust(7),_57,'secs'.ljust(12),'{:.1%}'.format(_57/_all))
	print('to 60'.ljust(7),_60,'secs'.ljust(12),'{:.1%}'.format(_60/_all))
	#print('to 70'.ljust(7),_70,'secs'.ljust(12),'{:.1%}'.format(_70/_all))
	print('to 80'.ljust(7),_80,'secs'.ljust(12),'{:.1%}'.format(_80/_all))
	print('to end'.ljust(7),_end,'secs'.ljust(12),'{:.1%}'.format(_end/_all))
	print('to all'.ljust(7),_all,'secs')
	'''

	return render(request,"nexus/listings.html",context)


def lock_account(request):
	''' locks account after a set number of attempts '''

	trace = 'password_locked'
	authenticated, email = authenticate_poster(request)

	try: #avoid error if account doesn't exist
		if Account.objects.filter(email=email).exists():
	
			#record in current lock outs
			locks = Locked.objects.filter(user=email)

			if len(locks) == 0: #not in database
				Locked.objects.create(user=email,route=trace)

				#record in history log
				Lockouts.objects.create(user=email,method=trace)

				#record in user's log
				me = Account.objects.get(email=email)
				me.locked = True
				log = me.log
				me.log = log+"LOCKED:"+\
						datetime.datetime.now().strftime(strftime)+\
						":::"+trace+":::\n"
				me.save()
			return
	except:
		pass

def unlock_account(email,trace=''):
	''' unlock account '''

	#delete from log
	me = Locked.objects.get(user=email)
	me.delete()

	#record in user's log
	me = Account.objects.get(email=email)
	me.locked = False
	log = me.log
	me.log = log+"LOCK_RELEASE:"+\
			datetime.datetime.now().strftime(strftime)+\
			":::"+trace+":::\n"
	me.save()

	return

def hash_password(pw_input):
	''' hash and salt password input '''
	try: pw_input = pw_input.encode('utf-8')
	except: pass
	hashed = bcrypt.hashpw(pw_input, bcrypt.gensalt())
	hashed = hashed.decode()
	return hashed

def check_password(me, pw_input):
	''' check password input matches encrypted saved '''
	
	try: enc_pw = pw_input.encode('utf-8')
	except: enc_pw = pw_input

	#check if new_pw/enc_pw matches saved/enc_hash
	enc_hash = me.password.encode('utf-8')
	match = bcrypt.hashpw(enc_pw, enc_hash) == enc_hash
	return match

def create_logs(request,me):
	''' create login records '''

	email = me.email
	cookie = request.COOKIES['csrftoken']
	c = 0
	
	try:
		session = request.COOKIES['sessionid']
	except: #in case no sessionid
		session = request.COOKIES['csrftoken']

	#update cookie, session if already logged in or else create new entry
	if is_logged_in(email=email):
		l = Logged_In.objects.filter(user=me)
		l.update(cookie=cookie)
		l.update(session=session)
		#l.update(meta = request_route_unscramble(request))
	else:
		try:
			c = Logged_In.objects.last()
			c = c.id
		except: #no one's logged in
			c = 0
		Logged_In.objects.create(
			id = c + 1, #need id, else = None raising Errors later
			user = me,
			cookie = cookie,
			session = session,
			#meta = request_route_unscramble(request)
		)

	me.log = me.log + "LOGIN:" + \
			datetime.datetime.now().strftime(strftime)+\
					":::\n"
	me.save()
		
	#set session expiry to when browser closes
	request.session.set_expiry(0)
	
	#retrieve login and pass to day log
	l = Logged_In.objects.get(user=me)
	Logins.objects.create(user=email,login=l.created)

	return

def ref_id(request,field,**kwargs):
	''' derives reference ids for model fields '''

	refid_error = 'refid_error'
	my_account = Account.objects.none()

	if 'account' in kwargs.keys():
		my_account = kwargs['account']
		my_id = my_account.id

		def acc_refid(my_id):
			refid = alphabase(my_id,base_set=base_set,max_char=8)
			refid = str(len(base_set))+'-'+refid
			return refid

		if field == 'account': 
			refid = acc_refid(my_id)
		
		if field == 'venue':
			if 'obj_id' in kwargs.keys():
				obj_id = kwargs['obj_id']
				#first store numeric obj_id
				if Venue.objects.filter(id=obj_id).exists():
					orig_obj_id = obj_id
				obj_id = alphabase(obj_id,base_set=base_set,max_char=12)
			else:
				obj_id = refid_error + '-' + field

			try:
				ven_country = request.POST['ven_ctr']
			except:
				#if created from Admin page then an id exists
				if Venue.objects.filter(id=orig_obj_id).exists():
					ven_country = Venue.objects.get(id=orig_obj_id).ven_ctr
				else:
					pass
			refid = my_account.acc_ref + '-VEN-' + obj_id + '-' + ven_country

		if field == 'event':
			#if specific date passed then use that
			if 'obj_id' in kwargs.keys(): 
				obj_id = kwargs['obj_id']
				obj_id = alphabase(obj_id,base_set=base_set,max_char=12)
			else:
				obj_id = refid_error + '-' + field
			refid = my_account.acc_ref + '-EVT-' + obj_id

		if field == 'feedback':
			if 'obj_id' in kwargs.keys(): 
				obj_id = kwargs['obj_id']
				obj_id = alphabase(obj_id,base_set=base_set,max_char=12)
			else:
				obj_id = refid_error  + '-' + field
			refid = my_account.acc_ref + '-FEED-' + obj_id
	
	else:
		if field=='account':		
			refid = noaccount_refid
		elif field == 'venue': 
			refid = noaccount_refid
		elif field=='event':
			if 'obj_id' in kwargs.keys(): 
				obj_id = kwargs['obj_id']
				obj_id = alphabase(obj_id,base_set=base_set,max_char=12)
			else:
				obj_id = refid_error  + '-' + field
			refid = noaccount_refid + '-EVT-' + obj_id
		else:
			refid = refid_error

	return refid

#TO FIX: RESULTS IN \U0027 ERRORS REPLACING CAPS AND LETTER U'S
#WHEN PYTHON RETURNS TEXT BACK IN HTML INPUT BOX E.G. AFTER FORM ERROR
#ONLY AFFECTS REMOTE ENVIRONMENT
def clean_apostrophes(text):
	''' replace all non-regular apostrophes causing is_valid errors '''

	regular = '\u0027'
	irregular = re.compile(r'[\u2018\u2019\u02BC\u02BD\u02BB\u02EE\u201A\u201B\u201C\u201D\u201F\uFF07]')
	cleaned = re.sub(irregular, regular, text)
	return cleaned

def simple_new_account_checks(request, aForm):
	''' simple checks before creating new account '''

	err , pass2fail = '', True
	authenticated, email = authenticate_poster(request)

	#reset flag if passwords match
	if request.POST['password1'] == request.POST['password2']:
		pass2fail = False

	#check passwords match
	if request.POST['password1'] != request.POST['password2']:
		err = messages['password_mismatch']

	#check if email is free (exclude account simply refreshing webpage)
	elif not authenticated:
		if Account.objects.filter(email=aForm.data['email']).exists():
			err = messages['email_taken']

	#check if email is free
	elif aForm.data['password'] == '': err = messages['no_password']

	#check if email is free
	elif len(aForm.data['password']) < valid_length('password')[0][0] or \
		len(aForm.data['password']) > valid_length('password')[0][1]: 
		err = messages['pw_length']

	elif 'terms' not in request.POST.keys(): err = messages['terms_not_ticked']

	return err, pass2fail

def create_new_account(request, aForm):
	''' return context for setting up new accounts '''

	pass2fail, err, err_msg = True, '', messages['incorrect_login']
	authenticated, email = authenticate_poster(request)	

	#don't carry on if already logged in eg user refreshing window
	if authenticated: pass2fail = False

	#should be a POST so if not then return to login page
	elif request.method != 'POST': 
		return authenticated, email, pass2fail, err_msg
	
	else:
		#check passwords match
		err_msg, pass2fail = simple_new_account_checks(request, aForm)

		if err_msg != '':
			return authenticated, email, pass2fail, err_msg

		else:
			#first clean apostrophes if any to avoid validation errors
			aForm.data['name'] = clean_apostrophes(aForm.data['name'])

			if aForm.is_valid(): 

				#housekeeping and then save
				pre_hash = aForm.data['password']
				new_account = aForm.save(commit=False)	
				new_account.password = hash_password(pre_hash)	
				new_account.active = True
				new_account.log = "CREATED:" + \
					datetime.datetime.now().strftime(strftime) + \
					":::\n"
				new_account.save()

				#get new account's auto-id and assign own ref id
				refid = ref_id(request,'account',account=new_account)
				new_account.acc_ref = refid
				new_account.save()

				#log user in
				create_logs(request,new_account)
				authenticated, err = True, ''
				email = new_account.email

			else:
				pass

	return authenticated, email, pass2fail, err, 

def unpack_kwargs(kwargs, *args):
	''' grab values in kwargs or return blank '''
	unpacked = []
	for arg in args:
		if arg in kwargs.keys():
			unpacked.append(kwargs[arg])
		else:
			unpacked.append('')
	return unpacked

def get_refid(ref, model):
	''' split id to get account reference '''

	if model == 'account':
		pattern = re.compile(r'(\d.*-[A-Z])-.*')
	if model == 'venue':
		pattern = re.compile(r'(\d.*-[A-Z])-VEN-.*')
	if model == 'event':
		pattern = re.compile(r'(\d.*-[A-Z])-EVT-.*')
	
	refid = re.findall(pattern,ref)
	if len(refid) > 0: #as is normally returned in a list
		refid = refid[0]
	return refid 

def update_fields(request, me, passwords):
	''' updates account fields prior to data clean '''

	err = ''
	new_pw = passwords['new_pw']
	typ_pw = passwords['typ_pw']

	#active status changes
	#checkbox in POST: 'on'=checked and no-key=unchecked
	if 'active' in request.POST.keys(): me.active = True
	else: me.active = False

	#name changes
	if request.POST['new_name'] != '': me.name = request.POST['new_name']
	
	#check if email already exists
	if request.POST['new_email'] != '':
		if Account.objects.filter(email=request.POST['new_email']).exists():
			err = "This email already exists and is unavailable"
		else:
			me.email = request.POST['new_email']

	#password changes
	my_password = request.POST['password']
	new_pw = request.POST['new_pass']
	match = check_password(me, new_pw) #if new_pw = current
	if len(new_pw) > 0 and match == False:
		new_pw = new_pw.encode('utf-8')
		me.password = hash_password(new_pw)

	#reconstitute account form
	aForm = AccountForm({
			'name':me.name,
			'email':me.email,
			'password':me.password,
			'active':me.active,				
			'terms':me.terms,
		})

	return me, aForm, err

def do_tags(case,formTag,event):
	''' check tags to avoid duplicates; attach to event ''' 

	invalid = ['', None, 'None', []]

	#clear old tags if updating
	if case == "update": event.evt_tag.clear()

	new_tags = formTag.save(commit=False)
	if new_tags.tag:
		temp = new_tags.tag.split(';')
		if temp != ['']:
			copy = temp[:]
			temp = []
			for c in copy:
				try:
					if c[0] == '#': c = c[1:] #remove any leading hash
				except:
					pass
				if c.strip() not in invalid:
					temp.append(title_text(c.strip()))

			tags = Tag.objects.all()
			for tag in tags:
				if tag.tag in temp:
					event.evt_tag.add(tag)
					temp.remove(tag.tag)
			if len(temp) > 0:
				for t in temp:
					event.evt_tag.create(tag=t)

	return event

def is_posted(request,eForm,vForm,**kwargs):
	''' check if event already posted to avoid duplication 

	avoids duplication from page refresh but not from fresh submits
	or fresh add event page which generated a new csrf
	'''

	posted = False
	rec = ''
	post = request.POST
	evt_nam = eForm.data['evt_nam']
	evt_dte = eForm.data['evt_dte']
	evt_tme = eForm.data['tme_beg']
	evt_ven = vForm.data['ven_nam']

	if 'CONTENT_LENGTH' in request.META.keys():
		code = request.META['CONTENT_LENGTH']
	else:
		code = '000000'
	
	try:
		csrf = request.POST['csrfmiddlewaretoken']
		rec = csrf + '_' + code + '_' + str(evt_dte) + '_' + \
				str(evt_tme) + '_' + str(evt_nam) + '_' + str(evt_ven)
	except:
		rec = 'nocsrf' + '_' + code + '_' + str(evt_dte) + '_' + \
				str(evt_tme) + '_' + str(evt_nam) + '_' + str(evt_ven)

	#if code exists then it's been posted else create a record of it
	rec = rec[-100:]
	if Posted.objects.filter(record=rec).exists():
		posted = True

	return posted, rec

def get_weekdays(e, daylist):
	''' get days of week to set to True for event '''

	#we do this so listed Days on listings page is correct else
	#you might get MTWTFSS for a <7day event
	#note: 'daylist' comes in as e.mon,e.tue .... Boolean objects 

	first, last = e.evt_dte, e.evt_end

	#with enum we get array [0,1,2,3,4,5,6] to match daylist [True,False ...]
	enum = [d[0] for d in list(enumerate(daylist))]
	interval, int_days = (last - first).days, []

	if interval > 5: 
		if e.ven_tme: #if set to use venue time
			v = e.venue
			ven_days = [v.mon_op,v.tue_op,v.wed_op,v.thu_op,v.fri_op,
						v.sat_op,v.sun_op]
			for i in range(7):
				if ven_days[i] != "00:00": daylist[i] = True
				else: daylist[i] = False
		else:
			pass #so use as submitted

	elif interval == 0: #if one day event
		for i in range(7):
			#set date to True everything else to False
			if enum[i] == first.weekday(): daylist[i] = True
			else: daylist[i] = False

	#for events lasting 2 to 6 days
	else:
		#get day of week in the event date range: 0=Mon,1=Tue ....
		for x in range(interval+1):
			int_days.append((first + datetime.timedelta(days=x)).weekday())
		#set e.day to True if its enum position is in event date range
		for i in range(7):
			if enum[i] in int_days: daylist[i] = True
			else: daylist[i] = False

	#if still no matching weekdays above then daylist is now all False
	#so set event date range to True
	#e.g. weekday submitted all unchecked or checked outside event dates 
	if not all(daylist):
		for i in int_days: daylist[i] = True

	return daylist

def photo_resize(file_max, file_size, wd, ht):
	''' rezise/compress photo to a give max '''

	#formula
	#--------------------------------------
	#target_size = target_wd * target_ht
	#typical wd/ht ratio = numerator/denominator
	#so target_wd =  numer/denom * target_ht
	#so target_size = numer/denom * target_ht * target_ht = n/d * target_ht^2
	#target_ht ^ 2 = target_size * denom/numer
	#target_ht = (target_size * denom/numer) ^ (0.5)
	#target_wd = numer/denom * target_ht

	margin = 0.999

	if file_size > file_max * margin:
		target_size = file_max * margin
		numer, denom = wd, ht

		target_ht = (target_size * denom / numer ) ** 0.5
		target_wd = target_ht * numer / denom
		wd, ht = int(target_wd), int(target_ht)

	return wd, ht

def get_feedback(count,**kwargs):
	''' feedback on event creation ''' 

	plural = ''
	action = 'added'
	if 'updated' in kwargs.keys(): 
		action = 'updated'

	if count <= 1:
		plural = ' event ' + action + '. '
	else:
		plural = ' events ' + action + '. '

	feedback = str(count) + plural + messages['event_success']

	return feedback

def post_fill_forms(request,**kwargs):
	''' populate forms with POST data '''

	ven_edit = False

	#instantiate variables
	eForm, vForm, tForm = None, None, None

	#deal with my_venues edits 
	if 'ven_edit' in kwargs.keys():
		ven_edit = kwargs['ven_edit']

	if ven_edit == True:
		vForm = VenueForm(request.POST.copy())
		return vForm

	else:
		#use copy to edit QueryDict
		eForm = EventForm(request.POST.copy(), request.FILES)
		vForm = VenueForm(request.POST.copy())
		tForm = TagForm(request.POST.copy())

		#get metatag
		try:
			meta_select = request.POST['meta_tag']
		except:
			meta_select = ''

		return eForm, vForm, tForm, meta_select

def check_if_venue_times(request,venue=None):
	''' checks if any venue times exist '''

	exist = False
	times = ['mon_op','tue_op','wed_op','thu_op','fri_op','sat_op','sun_op']

	if venue == None: #we get times from request form eg new venues
		try:
			list_ = [True for t in times if request.POST[t] != '00:00']
		except:
			pass
	else:
		#here we are passed a venue eg new venue, 
		#no ven times b/c use as_input in tme_beg when ven was setup
		list_ = []
		ven = Venue.objects.get(id=venue)
		for t in times:
			attr = getattr(ven, t)
			list_.append(attr != '00:00')

	if any(list_): exist = True

	return exist

def check_if_venue_open(venue, weekday):
	''' check if venue open on a certain weekday '''
	
	is_open = False
	days = {0:'mon_op',1:'tue_op',2:'wed_op',3:'thu_op',
			4:'fri_op',5:'sat_op',6:'sun_op'}
	
	ven = Venue.objects.get(id=venue)
	attr = getattr(ven, days[weekday])
	if attr != '00:00': is_open = True
	return is_open

def validate_event(request, forms, **kwargs):
	''' validate event fields '''

	good, form_errors, other_nots = False, [], []
	as_input = False
	today = datetime.date.today()

	#test event forms, get errors if invalid
	not_valid = [f for f in forms if not f.is_valid()]

	#venue times
	if 'ven_select' in kwargs.keys():

		#check venue errors where not in venue form
		if not kwargs['ven_select']:

			#flag for error if as_input but no time selected
			if request.POST['tme_beg'] == '00:00' and \
				request.POST['evt_tme_select'] == 'as_input':
				as_input = True
				other_nots.append('tme_beg')

			#flag for error if new venue and use ven_dflt but no ven_times
			if request.POST['evt_tme_select'] == 'ven_dflt' and \
				request.POST['ven_nam'] != '':
					times_given = check_if_venue_times(request)
					if not times_given: other_nots.append('ven_tme_dflt')

		else:
			#flag for error if my_venue + use ven_dflt and no ven_times
			if request.POST['evt_tme_select'] == 'ven_dflt' :
				times_given = check_if_venue_times(request,kwargs['venue'])
				if not times_given: other_nots.append('ven_tme')

			#flag for error if my_venue + as input but no input
			if request.POST['evt_tme_select'] == 'as_input' :
				as_input = True
				if request.POST['tme_beg'] == '00:00':
					other_nots.append('tme_beg')

	
	#event dates check
	event_date, end_date = '', ''
	try: event_date = reformat_date(request, "first")
	except: pass
	try: end_date = reformat_date(request, "end")
	except: pass

	if not event_date: 
		other_nots.append('evt_dte')
	else:
		if not end_date:
			end_date = event_date

		if end_date < event_date:
			other_nots.append('evt_end_ev')
		elif end_date < today:
			other_nots.append('evt_end_td')

	#event time start
	if as_input and request.POST['tme_beg'] == '00:00':
		other_nots.append('tme_beg')

	#event time end
	if 'tme_end' in request.POST.keys():
		if request.POST['tme_end'] != '00:00':
			if request.POST['tme_end'] <= request.POST['tme_beg']:
				other_nots.append('tme_end')


	#venue country
	if 'ven_ctr' in request.POST.keys():
		if request.POST['ven_ctr'] == 'ZZ' or \
			'--' in request.POST['ven_ctr']:
			other_nots.append('ven_ctr')

	#meta tags
	if request.POST['meta_tag'] == '':
		other_nots.append('meta_tag')


	#url errors
	url = request.POST['inf_url']
	if url != '':
		if 'http' not in url or \
			'//' not in url or \
			'.' not in url or \
			('www' in url and url.count('.') < 2):
			other_nots.append('inf_url')
			
	#get form errors
	if len(not_valid) != 0 or len(other_nots) != 0: 
		form_errors, good = get_form_errors(not_valid,other_nots)
	else:
		good = True

	return form_errors, good

def standard_add_event_context(request, kwargs):
	''' context that appears in all add_event views '''

	meta_select = ''
	use_ven_dflt = False
	can_edit = False

	#create empty forms and unpack kwargs
	eForm, vForm = EventForm(), VenueForm()
	tForm, mForm = TagForm(), MetaTagForm()
	me, forms, errors = unpack_kwargs(kwargs,'me','forms','errors')
	good, msg, show_venue = unpack_kwargs(kwargs,'good','msg','show_venue')
	authenticated, user = unpack_kwargs(kwargs,'authenticated','user')

	#we have to create an html select box and get any meta selected
	meta_selected = unpack_kwargs(kwargs,'meta_selected')[0]
	metas = [m.meta_tag for m in Meta_Tag.objects.filter(use_meta=True)]
	metas = sorted(metas)
	metas.insert(0,"Select tag")

	if not good: #pass back already entered details
		for f in forms:
			if 'evt_nam' in f.fields: eForm = f
			if 'ven_nam' in f.fields: vForm = f
			if 'tag' in f.fields: tForm = f
			if 'meta_tag' in f.fields: mForm = f
		
		if not meta_selected: #if user did not put in own meta 
			eForm.fields['meta_tag'] = metas
		elif 'meta_select' in kwargs.keys(): 
			meta_select = kwargs['meta_select']

	if me != '':
		kwargs['authenticated'] = True
		eForm.fields["venue"].choices = list_my_venues(request,me)

	try: #b/c won't exist for POSTs at login
		if request.POST['evt_tme_select'] == 'ven_dflt': 
			use_ven_dflt = True
	except:
		pass

	if authenticated: can_edit = True

	context = dict({
	
		'event':eForm,'tag':tForm,'venue':vForm,'metatag':mForm,
						'meta_list':metas,'meta_select':meta_select,'msg':msg,
						'show_venue':show_venue,'errors':errors,
						'can_edit':can_edit,
						'ven_btn_text':html_buttons['ven_btn_text'],
						'use_ven_dflt':use_ven_dflt,'user':user},)

	return context

def load_event(ref):
	''' load an event for update '''

	new_kwargs = {}
	event = Event.objects.get(evt_ref=ref)
	for f in event._meta.get_fields():
		new_kwargs[f.name] = getattr(event, f.name)
	eForm = EventForm(new_kwargs)

	#load venue form
	new_kwargs = {}
	venue = event.venue
	for f in venue._meta.get_fields():
		if f.name in VenueForm().fields:
			new_kwargs[f.name] = getattr(venue, f.name)
	vForm = VenueForm(new_kwargs)
	vForm.data['ven_ref'] = venue.ven_ref

	#load tags form
	new_kwargs = ''
	tags = event.evt_tag.select_related()

	for t in tags:
		new_kwargs += t.tag+'; '
	tForm = TagForm({'tag':new_kwargs})

	#load metatag form
	metatag = event.meta_tag
	mForm = MetaTagForm({'meta_tag':metatag})

	return eForm, vForm, tForm, mForm

def add_event_get_context(request, **kwargs):
	''' prepare context for new event form '''

	authenticated, email = authenticate_poster(request)
	if authenticated:
		me = Account.objects.get(email=email)
	
	kwargs['show_venue'] = True
	kwargs['authenticated'] = False
	kwargs['msg'] = 'Add your event below'
	user = unpack_kwargs(kwargs,'user')[0]

	#existing users (possibly) have my_venues to display
	if user == 'existing':				
		kwargs['show_venue'] = False
		kwargs['authenticated'] = True

	elif user == 'new':
		kwargs['authenticated'] = True

	context = standard_add_event_context(request,kwargs)

	if authenticated and 'edit_event' in request.GET.keys():
		eForm,vForm,tForm,mForm = load_event(request.GET['edit_event'])
		eForm.fields["venue"].choices = list_my_venues(request,me)
		context['event'] = eForm
		context['venue'] = vForm
		context['tag'] = tForm
		context['meta_select'] = mForm.data['meta_tag'].meta_tag
		context['msg'] = "Edit your event below"

	return context

def add_event_post_context(request, **kwargs):
	''' prepare context for posted event form '''

	evt_msg = ''
	me, good, user = unpack_kwargs(kwargs,'me','good','user')
	kwargs['msg'] = 'Add your event below'
	evt = unpack_kwargs(kwargs, 'evt_name')[0]
	new_venue_added = False

	if request.POST['ven_nam'] != '' or \
		request.POST['ven_cty'] != '' or \
		request.POST['ven_ctr'] != '':
		new_venue_added = True

	#inform if event record already exists or has been added
	if good:
		if evt == None:
			pass
		else:
			kwargs['msg'] = "Event '" + evt.evt_nam + \
							"' was added. Add more below."
		if user == 'anon': 
			kwargs['show_venue'] = True
		else: kwargs['show_venue'] = False

	else:
		kwargs['msg'] = "Please correct errors shown"
		if user == 'anon': kwargs['show_venue'] = True
		elif new_venue_added: kwargs['show_venue'] = True

	context = standard_add_event_context(request,kwargs)

	return context

@require_http_methods(["POST"])
def delete_event(request, **kwargs):
	''' delete event '''

	authenticated, email = authenticate_poster(request)
	me = None
	if authenticated:
		me = Account.objects.get(email=email)
		refid = request.POST['delete_event']
		e = Event.objects.filter(evt_ref=refid)[0]
		evt_nam = e.evt_nam
		msg = 'Your event "'+evt_nam.title()+'" was deleted'
		e.delete()

	context = my_events_contexts(request,me,msg=msg)
	context = dict(context,**global_context(request))
	return render(request,"nexus/my_events.html",context)

def load_venue(ref):
	''' load a venue for update '''

	#load venue form
	new_kwargs = {}
	venue = Venue.objects.get(ven_ref=ref)
	for f in venue._meta.get_fields():
		if f.name in VenueForm().fields:
			new_kwargs[f.name] = getattr(venue, f.name)
	vForm = VenueForm(new_kwargs)
	vForm.data['ven_ref'] = venue.ven_ref
	
	return vForm

@require_http_methods(["POST"])
def delete_venue(request, **kwargs):
	''' delete venue '''

	authenticated, email = authenticate_poster(request)
	me = None
	if authenticated:
		me = Account.objects.get(email=email)
		refid = request.POST['delete_venue']
		v = Venue.objects.filter(ven_ref=refid)[0]
		ven_nam = v.ven_nam
		msg = 'Your venue "'+ven_nam.title()+'" was deleted'
		v.delete()

	context = my_venues_contexts(request,me,msg=msg)
	context = dict(context,**global_context(request))
	return render(request,"nexus/my_venues.html",context)

@require_http_methods(["GET", "POST"])
def feedback(request):
	''' user feedback '''

	authenticated, email = authenticate_poster(request)
	if email != '': me = Account.objects.filter(email=email)[0]

	if request.method == 'GET':
		fForm, msg = FeedbackForm(), messages['feedback'][0]
		context = dict({'feed':fForm,'msg':msg},**global_context(request))

	if request.method == 'POST':
		fForm = FeedbackForm(request.POST.copy())

		#switch all apostrophes to ASCII u0027 to avoid validation error
		fForm.data['title'] = clean_apostrophes(fForm.data['title'])
		fForm.data['feedback'] = clean_apostrophes(fForm.data['feedback'])

		if fForm.is_valid():
			feed = fForm.save()
			feed.title = title_text(feed.title)
			refid = ref_id(request,'feedback',obj_id=feed.id,account=me)
			feed.feed_ref = refid

			#post to database
			if authenticated == True:
				feed.user = email
				feed.save()

				#save ref in user account
				feeds = me.feedback
				me.feedback = feeds + feed.feed_ref + ':::' + \
								feed.created.strftime(strftime) + \
								':::' + feed.title + '\n'

			else:
				feed.user = 'No-account'
				feed.save()

			msg = messages['feedback'][1]
			context = dict({'feed':FeedbackForm(),'msg':msg},
					**global_context(request))

		else:
			
			err, good = get_form_errors([fForm], other_nots=[])
			msg = messages['feedback'][0]
			context = dict({'feed':fForm,'errors':err,'msg':msg},
						**global_context(request))
		
	return render(request,"nexus/feedback.html",context)

@require_http_methods(["GET", "POST"])
def privacy(request):
	''' user feedback '''

	context = dict(**global_context(request))
		
	return render(request,"nexus/privacy.html",context)

@require_http_methods(["GET", "POST"])
def loginpage(request,**kwargs):
	''' GET requests at login '''
	
	errors, err_msg = '', ''
	aForm = AccountForm() #empty instance in case
	
	if 'errors' in kwargs.keys(): 
		errors = kwargs['errors']
		aForm = AccountForm(request.POST.copy())
	else:
		aForm = AccountForm(request.GET)

	if 'err_msg' in kwargs.keys(): err_msg = kwargs['err_msg']
	
	aForm.errors.clear()
	context = dict({'account':aForm,'msg':messages['case_sensitive'],
					'errors':errors, 'err_msg':err_msg}, 
					**global_context(request))
	return context

@require_http_methods(["GET","POST"])
def logout(request,**kwargs):
	''' log out and remove from logged_in '''

	authenticated, email = authenticate_poster(request)

	if email != '' and email != no_account:
		me = Account.objects.get(email=email)
	
		#update account log
		trace = 'logout'
		if request.GET.get('route') != None:
			route = request.GET.get('route')
		else:
			route = ''
		route = route + ', ' + trace
		logs = me.log
		me.log = logs+"ROUTE:"+route+":::\n"+"LOGOUT:"+\
					datetime.datetime.now().strftime(strftime)+":::\n"
		me.save()

		#get logged in record and delete
		user_log = Logged_In.objects.get(user=me)
		login = user_log.created
		user_log.delete()

		#update day log
		try:
			me = Logins.objects.get(login=login)
			me.route = route
			#me.meta = request_route_unscramble(request)
			me.logout = datetime.datetime.now() #!python object; no format!!
			me.save()
		except:
			pass

		#flush session data so can't be reaccessed from user browser
		request.session.flush()

	context = loginpage(request)
	return render(request,"nexus/loginpage.html",context)

def show_account(request,**kwargs):
	''' return context to view account details and some stats ''' 

	authenticated , email= authenticate_poster(request)

	if authenticated:

		me = Account.objects.get(email=email)
		meme = grab_me(request)

		evt_count = meme['my_evt_count']
		live = meme['live_count']
		coming_up = meme['coming_up']

		my_clicks = Click.objects.filter(acc_ref=me.acc_ref) \
								.aggregate(Sum('clicked'))

		try: #in case no live events to avoid div by 0 error
			coming_stats = {7:round(coming_up[7]/live*100),
							30:round(coming_up[30]/live*100)}
		except:
			coming_stats = 0

		ending_stats = {7:round(coming_up["7_end"]/7),
						30:round(coming_up["30_end"]/30)}

		#account details to show
		data = {
			'name':me.name,
			'email':me.email,
			'password':me.password,
			'active':me.active,
			'created':me.created,
			'clicks':my_clicks['clicked__sum'],
			}
		
		active_msg = messages["active_account"]
		inactive_msg = messages["inactive_account"]
		context = dict({'can_edit':True,
					'data':data,'authenticated':authenticated,
					'active':active_msg, 'inactive':inactive_msg,
					'evt_count':evt_count, 'live':live,
					'coming_up':coming_up,
					'coming_stats':coming_stats,
					'ending_stats':ending_stats},
					**global_context(request))
	else:
		error = messages['forbidden']
		return loginpage(request,errors=error)

	return context

def edit_account(request):
	''' return context to show page for changing details 

	actual saving to database handled by my_account
	'''
	
	authenticated, email = authenticate_poster(request)
	me = Account.objects.get(email=email)

	if authenticated:

		err = "Change your details below"

		#retrieve account details			
		aForm = AccountForm({
				'name':me.name,
				'email':me.email,
				'active':me.active,				
				})

		#we don't need to show errors at this point
		aForm.errors.clear()
		
		active_msg = messages["active_account"]
		inactive_msg = messages["inactive_account"]
		context = dict({'can_edit':True,
				'account':aForm, 'email':email, 'name':me.name,
				'active':active_msg, 'inactive':inactive_msg, 'err':err},
				**global_context(request))

	else:
		return event(request, error)
	
	return context

@require_http_methods(["GET", "POST"])
def delete_account(request):
	''' delete account '''

	msg, trace, case = '', '', ''
	meme = grab_me(request)
	me = meme['me']
	authenticated, email = authenticate_poster(request)

	if request.method == 'GET':
		err = messages['account_del']

	if request.method == 'POST':

		password = request.POST['del_password']

		#check password matched hash
		match = check_password(me, password)

		if authenticated and match:
			#log in deleted
			user = Deleted_Account(user=email)
			user.feedback = request.POST['feedback']
			user.log = me.log
			user.save()
			me.delete()
			msg = 'Your account has been deleted'
			error = msg
			logout(request,logmeout=True) #logout but come back here
			context = loginpage(request)
			return render(request,"nexus/loginpage.html",context)
		
		else:
			err = 'Details not authenticated'

	context = dict({'err':err,'can_edit':True,
					'name':me.name,'email':email},
			**global_context(request))

	return render(request,"nexus/account_del.html",context)

@require_http_methods(["GET","POST"])
def my_events_view(request,ref):
	''' account holder view individual event '''

	authenticated, email = authenticate_poster(request)

	if authenticated:
		name = Account.objects.get(email=email).name
		event = Event.objects.filter(evt_ref=ref)
		context = dict({'event':event,'name':name,'email':email,
				'no_description':messages['no_description'],},
				**global_context(request))
		return render(request,"nexus/my_events_view.html",context)

	else:
		error = messages['forbidden']
		logout(request,logmeout=True) #logout but come back here
		return loginpage(request,errors=error)

@require_http_methods(["GET", "POST"])
def my_events(request,**kwargs):
	''' shows user events '''

	msg = ''
	account = Account.objects.none()
	authenticated, email = authenticate_poster(request)
	me = Account.objects.get(email=email)

	#show events
	if authenticated:	
		if 'msg' in kwargs.keys():msg = kwargs['msg']	
		context = my_events_contexts(request,me,msg=msg)
		context = dict(context,**global_context(request))
		return render(request,"nexus/my_events.html",context)

	else: #if all else fails
		logout(request,logmeout=True) #logout but come back here
		return logpage(request,errors=error)

@require_http_methods(["GET","POST"])
def my_venues_view(request,ref):
	''' account holder view individual event '''

	authenticated, email = authenticate_poster(request)

	if authenticated:
		name = Account.objects.get(email=email).name
		venue = Venue.objects.filter(ven_ref=ref)
		e_ = Event.objects.filter(venue=venue[0])
		e_count = e_.count()
		e_live = e_.filter(evt_end__gte=today).count()
		context = dict({'venue':venue,'name':name,'email':email,
				'no_description':messages['no_description'],
				'e_count':e_count,'e_live':e_live, 'can_edit':True},
				**global_context(request))
		return render(request,"nexus/my_venues_view.html",context)

	else:
		error = messages['forbidden']
		logout(request,logmeout=True) #logout but come back here
		return loginpage(request,errors=error)

@require_http_methods(["GET", "POST"])
def my_venues(request,**kwargs):
	''' shows user venues for My Account'''

	meme = grab_me(request,get_links=False)
	me = meme['me']
	email = meme['email']
	authenticated = meme['authenticated']
	error = ''

	#show venues
	if authenticated == True:
		msg = ''
		if 'msg' in kwargs.keys():
			msg = kwargs['msg']		
		context = my_venues_contexts(request,me)
		trace = context['trace']
		context = dict(context,**global_context(request))
		return render(request,"nexus/my_venues.html",context)

	else: #if all else fails
		logout(request,logmeout=True) #logout but come back here
		return logpage(request,errors=error)

@require_http_methods(["GET", "POST"])
def login(request):
	''' login new and existing accounts '''
	
	authenticated, good_pass = False, False
	email, msg = '', messages['logged_in_msg']
	errs1 = messages['incorrect_login']
	errs2 = messages['login_error']
	errors = (errs1, errs2) #separated above so def_msg works
	other_nots = []

	#visiting the page
	if request.method == 'GET': 
		context = loginpage(request)

	elif request.method == 'POST':
		
		#authenticate existing accounts and open up add events
		if '/login/existing/' in request.META['PATH_INFO']:
			authenticated, email = authenticate_poster(request)
			password = request.POST['password_']

			try:
				me = Account.objects.get(email=email)
				good_pass = check_password(me, password)
			except:
				pass

			if authenticated and good_pass:
				create_logs(request, me)
				context = add_event(request,from_login=True)
			else: context = loginpage(request,errors=errors[0])

		#authenticate new accounts and open up add events
		elif '/login/new/' in request.META['PATH_INFO']:

			#b/c browser forces user to input in email/password fields
			#even when these fields are not required eg login vs new acct
			#login form now uses input boxes
			#so instead of
			#aForm = AccountForm(request.POST.copy())
			#we'll manually fill in form with POST data
			aForm = AccountForm({
						'name':request.POST['name'],
						'email':request.POST['new_email'],
						'password':request.POST['password1'],
						'terms':request.POST['terms']
					})

			authenticated, email, pass2fail, err = \
								create_new_account(request,aForm)
			if authenticated and not pass2fail:
				good_pass = True
				context = add_event(request,from_login=True)

			else:
				if pass2fail: other_nots = ['password2']
				errors, good = get_form_errors([aForm],other_nots)
				context = loginpage(request,errors=errors,err_msg=err)

		else: context = loginpage(request)

	#re-display loginpage if not GET or POST
	else: context = loginpage(request)

	if authenticated and good_pass:
		return render(request,"nexus/add_event.html",context)
	else:
		context['authenticated'] = False #override global_context
		return render(request,"nexus/loginpage.html",context)

@require_http_methods(["GET","POST"])
def update_venue(request,**kwargs):
	''' update venue details '''

	#grab user credentials
	authenticated, email = authenticate_poster(request)
	me = Account.objects.get(email=email)
	name = me.name
	upd_ven_meth = ''

	if authenticated:
		part_of_save_event = False
		vForm = VenueForm()

		if request.method == 'GET':

			if 'edit_venue' in request.GET.keys():
				ref = request.GET['edit_venue']
				vForm = post_fill_forms(request,ven_edit=True)
				vForm = load_venue(ref)
				msg = "Edit your venue"
				context = dict({'venue':vForm,'ven_ref':ref,
							'ven_edit':True,'can_edit':True,
							'email':email, 'name':name, 
							'ven_edit_msg':msg,}, 
						**global_context(request))
				return render(request,"nexus/add_event.html",context)

			if 'venue_events' in request.GET.keys():
				ref = request.GET['venue_events']
				ven = Venue.objects.get(ven_ref=ref)
				ven_events = Event.objects.filter(venue=ven)
				msg = "Events at " + ven.ven_nam
				context = my_events_contexts(request,me,msg=msg,ven=ven)
				context = dict(context,**global_context(request))
				return render(request,"nexus/my_events.html",context)

		elif request.method == 'POST':

			if 'part_of_save_event' in kwargs.keys():
				part_of_save_event = True
				ref = kwargs['ref']
				vForm = kwargs['vForm']

			elif '/my_venues/update/' in request.META['PATH_INFO']:
				upd_ven_meth = 'update'
				ref = request.POST['ven_ref']
				vForm = post_fill_forms(request,ven_edit=True)
			
			else: return login(request)

			ven = Venue.objects.get(ven_ref=ref)

			for k in ven._meta.get_fields():
				if k.name != 'ven_ref' and k.name in vForm.data.keys():
					val = getattr(ven, k.name)
					new = vForm.data[k.name]
					if val != new: setattr(ven, k.name, new.strip())
				
			ven.save()

			if part_of_save_event:
				return ven
			else:
				msg = 'Venue ' + ven.ven_nam + ' was successfully updated'
				context = my_venues_contexts(request,me,msg=msg,
							upd_ven_meth=upd_ven_meth)
				context = dict(context,**global_context(request))
				return render(request,"nexus/my_venues.html",context)

		else: 
			return login(request)
	else: return login(request)

def save_venue(request,vForm,eForm,authenticated,me):
	''' save venue form and assign it to event '''

	ref = vForm.data['ven_ref']
	
	#if existing venues
	if ref != 'None' and Venue.objects.filter(ven_ref=ref).exists():
		ven = update_venue(request,ref=ref,vForm=vForm,part_of_save_event=True)
		ven.save()

	else:	
		new_venue = vForm.save()
		vid = new_venue.id
		refid = ref_id(request,'venue',obj_id=vid,account=me) #get unique id
		new_venue.ven_ref = refid
		new_venue.ven_cty = new_venue.ven_cty.strip()
		new_venue.save()
		eForm.data['venue'] = vid
		eForm.full_clean() #needed for vid to be properly assigned

	if authenticated == True:
		#add choices to form
		eForm.fields["venue"].choices = list_my_venues(request,me)

	return eForm

def save_event(request, eForm, vForm, tForm, metatag, **kwargs):
	''' save event '''

	update = False 

	def set_dtg(e):
		#set list order: note ignores where ven_tme = True
		e.dtg_int = \
			max(0,(e.evt_dte - datetime.date.today()).days)
		e.dtg_num = e.dtg_int + random.random()
		return e

	#grab user credentials
	authenticated, email = authenticate_poster(request)

	if authenticated or email == no_account:
		me = Account.objects.get(email=email)

	new_event = None
	no_venue_selected = ['', 'nothing']

	#continue with saving only if record doesn't already exist
	posted, rec = is_posted(request, eForm, vForm)
	try:
		update = kwargs['update']
	except:
		pass

	if update:

		evt = Event.objects.get(evt_ref=request.POST['evt_ref'])

		#list fields as fields.keys is .iter object
		fields = []
		for k in eForm.fields.keys():
			fields.append(k)
		
		#don't iterate over these fields or are object instances
		exclude = ['account','venue','meta_tag']

		#can't get 'photo' in eForm.data.keys
		#so we do this separately
		if request.FILES:
			val = getattr(evt, 'photo')
			new = request.FILES.get('photo')
			setattr(evt, 'photo', new)
		
		for k in eForm.data.keys():

			if k in fields and k not in exclude:
				val = getattr(evt, k)
				new = eForm.data[k]
				#convert all checkboxes to True/False
				if new == 'on': new = True
				if new == 'off': new = False
				if val != new:
					setattr(evt, k, new)
					
			if k == 'venue':
				val = getattr(evt, k)
				new = eForm.data['venue']
				new = Venue.objects.get(id=new)
				eF = save_venue(request,vForm,eForm,authenticated,me)
				if val != new: setattr(evt, k, new)

			if k == 'meta_tag':
				val = getattr(evt, k)
				new = eForm.data['meta_tag']
				try:
					new = Meta_Tag.objects.get(meta_tag=new)
					eF = save_venue(request,vForm,eForm,authenticated,me)
					if val != new: setattr(evt, k, new)
				except:
					pass

		#set list order: note ignores where ven_tme = True
		evt = set_dtg(evt)

		evt.save()

		return evt

	if not posted and not update:
		#save venue form details to eForm if venue not from user saved list
		#or an anonymous user; attach venue to eForm
		if 'venue' in request.POST.keys():
			if request.POST['venue'] in no_venue_selected: 
				eForm = save_venue(request,vForm,eForm,authenticated,me)
		else:
			eForm = save_venue(request,vForm,eForm,authenticated,me)
		
		#save other details
		new_event = eForm.save(commit=False) 
		new_event.account = me

		#set the weekdays to match given event day range
		#we do this so listed Days on listings page is correct else
		daylist = [new_event.mon,new_event.tue,new_event.wed,new_event.thu,
					new_event.fri,new_event.sat,new_event.sun]

		#set flag if using venue default time
		if authenticated: #only applies to account holders
			if request.POST['evt_tme_select'] == 'ven_dflt': 
				new_event.ven_tme = True

		#return True/False for each day of week
		new_event.mon,new_event.tue,new_event.wed,new_event.thu, \
		new_event.fri,new_event.sat,new_event.sun = \
		get_weekdays(new_event, daylist)
		
		#need this to do Many2Many tags
		new_event.save()

		#save tags and meta-tags to event
		new_event = do_tags('new', tForm, new_event)
		new_event.meta_tag = Meta_Tag.objects.get(meta_tag=metatag)

		#use custome Title case to avoid Ben'S if using Python's fxn
		new_event.evt_nam = title_text(new_event.evt_nam)

		#finally save account and derive an id and then save event
		new_event.account = me
		refid = ref_id(request,'event',obj_id=new_event.id,account=me)
		new_event.evt_ref = refid #note: not saved yet

		#set list order: note ignores where ven_tme = True
		new_event = set_dtg(new_event)

		new_event.save()

		#now retrieve any photo saved and resize to file limit
		#we do it here as there isn't any simple way to do it at validation
		#resizing will be done by changing width, height
		if new_event.photo:
			ph = new_event.photo
			wd = ph.width
			ht = ph.height
			file_size = ph.file.size
			size_max = image_file_limit

			#open file in PIL using absolute path
			#file retrieved relative to current working directory
			#cwd = sqwzl from where manage.py is run
			f_path = os.path.join(os.getcwd()+'/media/'+ph.name)
			ph = Image.open(f_path)

			#resize and save file using same name
			new_wd, new_ht = photo_resize(size_max, file_size, wd, ht)
			ph = ph.resize((new_wd, new_ht))
			ph.save(f_path)
		
		#first line record to check against refresh resubmits
		Posted.objects.create(record=rec)
	
	return new_event

@require_http_methods(["GET", "POST"])
def add_event(request,**kwargs):
	''' process and render context for new event '''

	context, user , me, evt_nam = {}, "anon", '', ''
	use_ven_dflt, meta_selected, venue_select = False, True, False
	update_evt = False
	authenticated, email = authenticate_poster(request)
	from_login = False

	if 'from_login' in kwargs.keys(): 
		from_login = kwargs['from_login']
		if from_login: authenticated = True

	if authenticated:
		me = Account.objects.get(email=email)
		if Event.objects.filter(account__email=email).exists():
			user = "existing"
		else: user = "new"

	if request.method == 'GET' or from_login:
		if '/my_events/update/' in request.META['PATH_INFO']:
			context = dict(add_event_get_context(request,user=user,me=me,
						forms=[],errors=[]),upd_evt_meth='update',
						**global_context(request))
		else:
			context = dict(add_event_get_context(request,user=user,me=me,
						forms=[],errors=[]),**global_context(request))	
		
		if from_login: return context
		
	elif request.method == 'POST':
		eForm, vForm, tForm, meta_select = post_fill_forms(request)

		if meta_select == '': 
			meta_selected, meta_select = False, 'Other'

		#sort dates
		event_date = reformat_date(request, "first")
		try: end_date = reformat_date(request, "end")
		except: end_date = event_date
		if end_date == None: end_date = event_date
		eForm.data['evt_dte'] = event_date #use database formatted date
		eForm.data['evt_end'] = end_date

		forms = [eForm,vForm,tForm]
		
		if not authenticated: #none account users	
			errors, good = validate_event(request,forms)

			if good:
				evt = save_event(request,eForm,vForm,tForm,meta_select)
				context = dict(add_event_post_context(request,user=user,
							me=me,forms=[],errors=[],good=good,
							meta_select=meta_select,evt_name=evt),
							**global_context(request))
			else:
				context = dict(add_event_post_context(request,user=user,
							me=me,forms=forms,errors=errors,good=good,
						meta_select=meta_select,meta_selected=meta_selected),
							**global_context(request))
		
		else: #for account holders
			#if no country selected remove the default so error can be raised 
			#but if venue selected from user's list remove vForm
			venue = None
			if request.POST['venue'] != 'nothing':
				forms.remove(vForm)
				venue_select, venue = True, request.POST['venue']

			errors,good = validate_event(request,forms,
							ven_select=venue_select,venue=venue)

			if good == True:
				if '/my_events/update/' in request.META['PATH_INFO']:
					update_evt = True

				evt = save_event(request,eForm,vForm,tForm,meta_select,
					update=update_evt)

				if evt is not None: evt_nam = evt.evt_nam

				if update_evt:
					msg = "Your event "+evt_nam+" was updated"
					context = dict({'authenticated':authenticated,},
							**my_events_contexts(request,me,
							 good=good,msg=msg))
				else:
					context = dict(add_event_post_context(request,user=user,
							me=me,forms=[],errors=[],good=good,
							meta_select=meta_select,evt_name=evt,),
							**global_context(request))

			else:
				context = dict(add_event_post_context(request,user=user,
							me=me,forms=forms,errors=errors,good=good,
						meta_select=meta_select,meta_selected=meta_selected,
							upd_evt_meth='update'),
							**global_context(request))

	else: #should not get here but in case ...
		error = messages['add_event_fail']
		return loginpage(request,errors=error)

	if update_evt:
		return render(request,"nexus/my_events.html",context)
	else:
		return render(request,"nexus/add_event.html",context)

@require_http_methods(["GET", "POST"])
def email_reset_password(request, email, password):
	''' send email to reset password '''

    # Manually open the connection
	#connection = mail.get_connection()
	#connection.open()

	# Construct an email message that uses the connection
	subject = 'Password reset'
	body = messages['new_pw_confirm'] + password.decode('utf-8')
	from_email = 'contact@sqwzl.com'
	to_email = email

	#reset_email = mail.EmailMessage(subject, body, 
	#				from_email, [to_email], connection=connection)

	#send using connection; can include as many messages as you like
	#connection.send_messages([reset_email,])
	
	#manually close the connection
	#connection.close()

	#################################################################
	#hack below as using above + settings.py errors
	#possible Django:Zoho problems need to recheck/review
	#http://stackoverflow.com/questions/18335697/send-email-through-zoho-smtp
	import smtplib
	from email.mime.text import MIMEText

	password = 'yQz4Ri7^7!81'

	msg = MIMEText(body)
	msg['Subject'] = subject
	msg['From'] = from_email
	msg['To'] = to_email

	# Create server object with SSL option
	server = smtplib.SMTP_SSL('smtp.zoho.com', 465)

	# Perform operations via server
	server.login(from_email, password)
	server.sendmail(from_email, [to_email], msg.as_string())
	server.quit()

	return

def password_request(request):
	''' jobs to reset password '''

	#get account
	authenticated, email = authenticate_poster(request)

	if email == '':
		trace = 'pw_reset_no_email'
		error = messages['incorrect_login']
		return logpage(request,errors=error,trace=trace)

	try:
		account = Account.objects.get(email=email)
	except:
		trace = 'login_reset_no_account'
		error = messages['incorrect_login']
		return logpage(request,errors=error,trace=trace)

	#set account password to a random temporary password
	temp_pw = passwords(length=10).encode('utf-8')
	account.password = hash_password(temp_pw)
	
	#log it and save
	log = account.log
	account.log = log+"PASSWORD_RESET:"+\
			datetime.datetime.now().strftime(strftime)+\
			":::\n"
	account.save()

	#if locked: record lock release event and unlock account
	try:
		trace = 'LOCK_RELEASE'
		unlock_account(email,trace)
	except:
		pass

	#send email
	email_reset_password(request,email,temp_pw)

	error = messages['new_pw']
	trace = 'email_reset_pw'
	return logpage(request,errors=error,trace=trace)

def password_error(request, me, passwords):
	''' catch common input error '''
	
	match, pw_unmatch = False, False
	my_password = passwords['my_password']
	new_pw = passwords['new_pw']
	typ_pw = passwords['typ_pw']

	#catch typical password entry errors
	match = check_password(me, my_password)
	if len(my_password) == 0 or not match:
		err = 'Please enter your correct password'
		common_error = True

	elif len(new_pw) == 0 and len(typ_pw) > 0 or \
			len(new_pw) > 0 and len(typ_pw) == 0 :
		err = "Please complete both password boxes"
		pw_unmatch, common_error = True, True

	elif new_pw != typ_pw:
		err = "Your new password entries don't match"
		pw_unmatch, common_error = True, True

	else:
		common_error, err = False, ''
	
	return pw_unmatch, common_error, err

def my_account(request,**kwargs):
	''' show account details, validate changes to details '''

	new_name, new_email, err, err_field = '', '', '', ''
	context, valid = {}, {}
	authenticated, email = authenticate_poster(request)
	try:
		me = Account.objects.get(email=email)
	except:
		authenticted = False

	if authenticated:

		#populate a standard form; may be overridden later
		if request.POST: aForm = AccountForm(request.POST)
		else: aForm = AccountForm(request.GET)
		
		#edit account details - show editable fields
		if '/my_account/reset/' in request.META['PATH_INFO']:
			context = edit_account(request)
			return render(request,"nexus/account_reset.html",context)

		#validate changes
		elif '/my_account/save_changes/' in request.META['PATH_INFO']:

			#populate
			my_new_email = request.POST['new_email']
			passwords = {
						'my_password':request.POST['password'],
						'new_pw':request.POST['new_pass'],
						'typ_pw':request.POST['retype_pass']
						}
			active_msg = messages["active_account"]
			inactive_msg = messages["inactive_account"]

			#catch typical password entry errors
			pw_unmatch, pw_error, err = password_error(request, me, passwords)
			if pw_error:
				if pw_unmatch: err_field = 'pw_unmatch'
				else: err_field = 'curr_pass'
				aForm.errors.clear() #we will use err instead
				context = dict({'account':aForm, 'err':err,
								'err_field':err_field,
								'email':email, 'name':me.name,
								'active':active_msg,'inactive':inactive_msg},
								**global_context(request))

			else: #authenticated=True; clean new fields, save if ok
				new_pw = request.POST['new_pass']
				pw_input = request.POST['password']

				if request.POST['new_name'] != '': 
					valid['name'] = request.POST['new_name']
					new_name = valid['name']
				if request.POST['new_email'] != '': 
					valid['email'] = request.POST['new_email']
					new_email = valid['email']
				if request.POST['new_pass'] != '': 
					valid['password'] = request.POST['new_pass']

				for new in valid.keys():			
					try: validate(valid[new], new)
					except ValidationError as e:
						err = 'Please correct errors below. '
						err += e.messages[0]
						err_field = new
						break

				if err == '':
					#err doesn't catch diplicate emails which is unique=True 
					me, aForm, duplicate_email_error = \
						update_fields(request,me,passwords)
	
					if duplicate_email_error == '':
						if new_pw != '': me.password = hash_password(new_pw)
						me.save()
						err = "Your details were changed"

					else: err, err_field = duplicate_email_error, 'email'

				context = dict({'name':me.name, 'new_name':new_name,
								'email':me.email,'new_email':new_email,
								'account':aForm,
								'err':err,'err_field':err_field,
								'active':active_msg,'inactive':inactive_msg},
								**global_context(request))

		else:
			context = show_account(request)
			return render(request,"nexus/account.html",context)

	else: return login(request)

	return render(request,"nexus/account_reset.html",context)

@require_http_methods(["POST",])
def event_clicks(request):
	''' record event clicks '''
	event_ref = request.POST['clicks']
	instance = Click.objects.get_or_create(evt_ref=event_ref)
	instance = instance[0] #as get_or_create creates a tuple
	instance.clicked = F('clicked') + 1
	instance.meta = request.META
	instance.acc_ref = get_refid(event_ref,'account')
	instance.save()
	return event(request)


@require_http_methods(["POST",])
def event_comments(request):
	''' checks if user has asked for page to be reset '''
	
	ip, cookie, comments = None, None, None
	exists, no_cookie = False, False
	com_cnt = 0
	posting = False
	event_ref = ''

	#event_ref = request.POST['recommend']
	if 'add_comment' in request.POST.keys():
		posting = True
		event_ref = request.POST['add_comment']
	else:
		event_ref = request.POST['view_comment']

	#get cookie
	try:
		cookie = request.COOKIES['csrftoken']
	except:
		pass

	#get ip
	if 'HTTP_X_REAL_IP' in request.META.keys():
		ip = request.META['HTTP_X_REAL_IP']
	elif 'HTTP_X_FORWARDED_FOR' in request.META.keys():
		ip = request.META['HTTP_X_FORWARDED_FOR']
	elif 'HTTP_HOST' in request.META.keys():
		ip = request.META['HTTP_HOST']


	#check if this user/ip has already commented - check if needed
	if not cookie:
		no_cookie = True

	else:	

		if not posting: # viewing comments

			comments = Event_Comment.objects.filter(evt_ref=event_ref) \
											.order_by('-date')
			comments = list(comments.values_list('text',flat=True))
			com_cnt = len(comments)

			e = Event.objects.get(evt_ref=event_ref)
			e.com_cnt = com_cnt
			e.save()
			
			comments = '=com='.join(comments)

	
		else: # posting a comment

			comment = request.POST['input']
			
			# check if same comment already posted by poster
			R = Event_Comment.objects.filter(
					cookie=cookie,evt_ref=event_ref,text=comment)
			if R:
				R = R[0]
				exists = True

			if not exists:
				if ip:
					R = Event_Comment.objects.filter(
							ip=ip,evt_ref=event_ref,text=comment)
					if R:
						R = R[0]
						exists = True

			if not exists: # create

				instance = Event_Comment.objects.get_or_create(
							cookie=cookie,
							evt_ref=event_ref,
							text=comment,
							meta=request.META)
				instance = instance[0] #as get_or_create creates a tuple
				if ip: instance.ip = ip
				instance.save()

				#record count in Event
				try:
					e = Event.objects.get(evt_ref=event_ref)
					e.com_cnt = e.com_cnt + 1
					e.save()
					com_cnt = e.com_cnt
					comments = Event_Comment.objects.filter(
											evt_ref=event_ref) \
											.order_by('-date')
					comments = list(comments.values_list('text',flat=True))
					comments = '=com='.join(comments)
				except:
					pass

	data = {'com_cnt': com_cnt,'no_cookie':no_cookie, 'comments':comments}

	return JsonResponse(data)


@require_http_methods(["POST",])
def recommended(request):
	''' checks if user has asked for page to be reset '''
	
	ip, cookie = None, None
	exists, recommending, no_cookie = False, True, False
	rec_cnt = 0

	event_ref = request.POST['recommend']

	#get cookie
	try:
		cookie = request.COOKIES['csrftoken']
	except:
		pass

	#get ip
	if 'HTTP_X_REAL_IP' in request.META.keys():
		ip = request.META['HTTP_X_REAL_IP']
	elif 'HTTP_X_FORWARDED_FOR' in request.META.keys():
		ip = request.META['HTTP_X_FORWARDED_FOR']
	elif 'HTTP_HOST' in request.META.keys():
		ip = request.META['HTTP_HOST']

	#check if this user/ip has already recommended this event
	if not cookie:
		no_cookie = True

	else:	
		R = Recommend.objects.filter(cookie=cookie,evt_ref=event_ref)
		if R:
			R = R[0]
			exists = True

		if not exists:
			if ip:
				R = Recommend.objects.filter(ip=ip,evt_ref=event_ref)
				if R:
					R = R[0]
					exists = True

		if exists:
			if R.yes: #already recommended
				R.yes = False #unrecommend
				recommending = False
			else: #perhaps recommended, unrecommended, recommending again
				R.yes = True
			R.save()

		else: #does not exist, create new record
			instance = Recommend.objects.get_or_create(
						cookie=cookie,
						evt_ref=event_ref,
						yes=True,
						meta=request.META)
			instance = instance[0] #as get_or_create creates a tuple
			if ip: instance.ip = ip
			instance.save()

		#record count in Event
		try:
			e = Event.objects.get(evt_ref=event_ref)
			if recommending:
				e.rec_cnt = e.rec_cnt + 1
			else:
				e.rec_cnt = e.rec_cnt - 1
			e.save()
			rec_cnt = e.rec_cnt
		except:
			pass

	data = {'rec_cnt': rec_cnt,'no_cookie':no_cookie, 'has_rec':recommending}

	return JsonResponse(data)

@require_http_methods(["GET","POST"])
def promotions(request):
	''' promotion '''

	live_prom_ref = 1
	prom = Promotion.objects.get(id=1)
	tags = News_Tag.objects.all()
	trace = 'promotions'
	msg = ''
	current_prom = "Valentine Bubbles Give-Away"

	#create new form
	if request.method == 'POST':
		sForm = SubscriberForm()
		sForm = SubscriberForm(request.POST.copy())

		#check for errors
		if request.POST['email']=='' or \
			request.POST['handle_twitter']=='' and \
			request.POST['handle_facebook']=='':
			msg = 'Please make sure you have input a corect email address AND either a Facebook or Twitter handle'

		#or if already submitted
		if Subscriber.objects.filter(email=request.POST['email']).exists():
			msg = "This email has already been submitted"

		#save if valid
		elif msg == '' and sForm.is_valid():
			msg = "Thank you. Your entry was successful!"
			new_sub = sForm.save()
			
			#add @ to missing handles
			if request.POST['handle_facebook'] != '':
				if request.POST['handle_facebook'][0] != '@':
					new_sub.handle_facebook = '@'+ \
						request.POST['handle_facebook'].strip()
			if request.POST['handle_twitter'] != '':
				if request.POST['handle_twitter'][0] != '@':
					new_sub.handle_twitter = '@'+ \
						request.POST['handle_twitter'].strip()

			#add current promotion to subscriber
			prom = Promotion.objects.get(name=current_prom)
			new_sub.promotion.add(prom)

			#add any newsletter themes subscriptions
			themes = News_Tag.objects.all()
			for t in themes:
				try:
					if request.POST[t.tag] == 'on':
						new_sub.news_tag.add(t)
				except:
					pass

			#add any city/town peferences
			try:
				if request.POST['city'] != '':
					new_sub.city = request.POST['city']
			except:
				pass
			
			new_sub.save()
		
		else:
			msg = 'Please make sure you have input a corect email address AND either a Facebook or Twitter handle'

	context = {'subForm':SubscriberForm,
				'promotion':prom,
				'tags':tags, 'msg':msg,
				'img_prefix':img_prefix,
				'urls':urls,
				}

	return render(request,"nexus/promotions.html",context)

@require_http_methods(["GET","POST"])
def submit_photo(request):
	''' submit photo journal '''

	context = {'submit_photo':True, **global_context(request)}

	return render(request,"nexus/submit_photo.html",context)