import unicodedata, functools, operator, socket
import re, datetime, random, time, math, statistics
import os, sys, http.client, json, lxml, html5lib, copy, heapq
import urllib.request, urllib.parse
from urllib.error import  URLError, HTTPError
from collections import Counter, defaultdict

import django
from django.conf import settings
from django.db.models import Q, F, Sum

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# need to set this as rawscrape SubTxt is running outside of Django
#os.environ["DJANGO_SETTINGS_MODULE"] = "collector.settings"
#sys.path.insert(0, '/Volumes/Private/Projects/Django/collector/collector') 
#django.setup()

# import post django setup
from scraper.models import Scraped, Seed, Tag, Meta_Tag, Tagged_Events, Event
from scraper.dates import date_patterns
import scraper.global_variables as G

# debugging directives
print_tags = ''
print_doclist = 'y'
print_urls = ''

tr_dupl = ''
tr_con_date = ''
tr_date = ''
tr_time = ''
tr_img = ''

# to save errors down in files for later review
base_dir = os.path.dirname(os.path.dirname(__file__))

# Model objects
objects_list = { # model,values_list field
	'metas': (Meta_Tag.objects.all(),'meta_tag'),
	'tags': (Tag.objects.all(),'tag'),
	'prior': (Tagged_Events.objects.all(),'event'),
	'scraped': (Scraped.objects.all(),'evt_nam'),
	'seeds': (Seed.objects.all(),'seed'),
	'events': (Event.objects.all(),'event'),
}

# Model objects values
values_list = defaultdict()
for model, objs in objects_list.items():
	values_list[model] = objs[0].values_list(objs[1],flat=True)


def nearby_years(lookaround=10):
	''' creates list of years around the current year'''
	
	this_yr = G.today.year
	years = {this_yr} # initialize as set to avoid dupl in range()
	
	steps = [1, -1]
	lookaround += 1  # b/c of zero-base; setoff from curr yr
	for step in steps:
		if step < 0: lookaround = -lookaround
		for i in range(0,lookaround,step):
			years.add((this_yr + i))
	return sorted(list(years))


def read_url(url,js_site,brow):
	''' reads url page 		
		output will be a bytes object
		we can do string like methods as long as objects are all bytes
	'''

	htmltext = ''
	url = url.strip()

	print("Next up: ", url)

	print("...... reading")

	if js_site:

		# site content needs browser as js built
		# don't quit browser in case recaptcha callback"
		print("...... start browser")
		if brow.lower() == 'chrome': browser = webdriver.Chrome()
		else: browser = webdriver.Safari()
		print("...... waiting before grab")
		browser.implicitly_wait(30) #before grabbing html
		print("...... get url")
		browser.get(url) # navigate to the page
		print("...... return innerHTML")
		htmltext = browser.execute_script("return document.body.innerHTML")

	else:

		# use header User Agent as some sites hate scripts (Error:Forbidden) 
		req = urllib.request.Request(url, data=None, headers={
		    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/602.3.12 (KHTML, like Gecko) Version/10.0.2 Safari/602.3.12'
					}	
				)

		try:
			with urllib.request.urlopen(req, timeout=30) as f:
				print('status: ',f.status)
				print('reason: ',f.reason)
				print(f.info())
				htmltext = f.read()

		except socket.timeout:
			print('socket timeout')
			htmltext='socket timeout'

		except TimeoutError:
			print("timed out")
			if hasattr(e, 'reason'): print('reason: ', e.reason)
			htmltext='timed_out'

		except URLError as e:
			print('failed_request')
			if hasattr(e, 'reason'): print('reason: ', e.reason)
			htmltext='failed_request'

		except UnicodeEncodeError:
			print("unicode error")
			htmltext='unicode error'		

		except HTTPError as e: print('code: ',e.code)
	
	return htmltext


def is_not_valid_url(url,test):
	''' range of tests to validate url to scrape is appropriate'''
	url = url.lower()
	boolean = False
	typ = G.webpage_url_tests[test] # get terms for this 'test'
	if test == 'is_old_page':
		# add prior years; 20 is arbitrary
		typ += [str(n) for n in nearby_years(lookaround=20) 
						if n < G.today.year]

	#print(110,test)
	if test == 'is_not_english':
		if 'lang=' in url and 'lang=en' not in url:
			boolean = True
	elif test == 'is_event_page':
		# here we try to catch events pages when a listings page already exists
		# event pages will usually list out event name separeted by eg. '-'
		# we want to avoid case: events/page_2 types OR /calendar_month_april
		# so check for minimum \W 
		# though we'll miss single titled events or \W < minimum
		if any(indicator in url for indicator in G.indicative_event_page):
			if url[-1] == '/': url = url[:-1] # remove trailing slash
			u = url.split('/')[-1]
			# eg https://boo.com/events/the-brighton-soul-train
			# but not the '=20' in http://boo.com/events/page=20
			if 'page' not in u:
				y = re.findall(r'\W',u)
				if '=' in y:
					y.remove('=')
				if len(y) >= 3:
					boolean = True
	elif any(t in url for t in typ):
			boolean = True
	return boolean


def strip_chars(txt,ignore_multi_mark=False,ignore_pos_links=True):
	''' strips leading spaces/characters '''

	tmp, char = [], ''
	repl_strips = ('/p','/a','>',' ..')
	sub_strips = ('/span',) #nb tuple
	strips = G.strips
	pos_links = G.pos_links
	all_months = G.all_months

	txt = txt.strip()

	# ignore pos_links so can be captured by concat_starts/ends
	if ignore_pos_links:	
		if any(txt.startswith(l) for l in pos_links) or \
			any(txt.endswith(l) for l in pos_links):
			return txt

	# also, if applicable, ignore markers suggesting multi-dates
	# split over several lines
	# case: 1, \n 3 & \n 7 July, \n 15 Sep ....
	if ignore_multi_mark:
		if any(re.search(r'\d+.*?'+mm+r'\s*$',txt,flags=re.I) for 
									mm in G.multi_date_markers) or \
			any(re.search(r''+mth+r'.*?'+mm+r'\s*$',txt,flags=re.I) for 
								mth in G.all_months for 
								mm in G.multi_date_markers):

			return txt

		
	while len(txt) > 0 and (txt[-1] in strips or txt[0] in strips):
		for s in strips:
			txt = txt.strip(s)
			txt = txt.strip()

	# for multi-char strips can't use strip(chars)
	# as it'll take each char and then do a strip of that in turn
	# eg 'petra'.strip('/a') becomes 'petr' - not what we want
	for x in repl_strips:
		if txt.endswith(x) or txt.startswith(x):
			txt = txt.replace(x,'')
	for s in sub_strips:
		txt = txt.replace(s,'')

	# finally
	txt = txt.strip()

	return txt


def strip_text(txt,what):
	''' remove what from text '''
	if isinstance(what,str):
		what = [what]
	for w in what:
		txt = txt.replace(w, '')
	txt = strip_chars(txt)
	return txt


def strip_quotes(txt):
	''' remove quotes '''
	txt = re.sub(r"'",'',txt) #no space for apostophe or quotes
	txt = re.sub(r'"','',txt) #no space for apostophe or quotes
	txt = txt.strip()
	return txt


def remove_numbers(txt):
	''' remove numbers '''
	txt = re.sub(r'[0-9]','',txt)
	txt = txt.strip()
	return txt


def remove_parentheses(txt):
	''' remove enclosing parenthesis - round and square '''
	txt = re.sub(r'[\(\)\[\]]','',txt)
	txt = txt.strip()
	return txt


def remove_spaces(txt):
	''' replace multiple spaces with a single space '''
	txt = re.sub(r'\s+',' ',txt)
	return txt


def remove_punctuation(txt,rm_dig=False):
	''' remove punctuation from txt '''
	puncts = G.puncts
	for p in puncts:
		txt = re.sub(r''+p,' ',txt)

	for s in G.strips:
		try: txt = re.sub(r''+s,'',txt)
		except: pass

	txt = strip_quotes(txt)
	txt = remove_parentheses(txt)
	if rm_dig: #remove digits
		txt = remove_numbers(txt)
	txt = remove_spaces(txt)
	txt = txt.strip()
	return txt


def strip_currencies(txt):
	''' strips currencies/price '''
	
	currencies = G.currencies
	
	if isinstance(txt,int): txt = str(txt)
	if not isinstance(txt,str): return txt
	
	if any(re.search(r'^'+c,txt) for c in currencies):
		txt = '' # remove if currency starts line
	elif any(c in txt for c in currencies):
		for c in currencies:
			finds = re.findall(r''+c+r'.*?\d+?\.?\d{0,2}/?\d*\.?\d{0,2}',txt)
			if finds:
				for f in finds:
					txt = txt.replace(f,'')
	return txt


def strip_varnish(txt):
	''' removes sections not commonly part of proper title '''
	# used in Tagged Events to save down unvarnished event titles for later
	# comparisons to ensure events from same venue aren't duplicated
	# case: earlier scrape yielded: 'GMT Promotions present Nutcracker'
	# case: new scrape yields: 'Nutcracker'
	# it's the same event just differently worded
	varnish = ['presents','present']
	for v in varnish:
		if v in txt:
			txt = txt.split(v)[1].strip()
	return txt


def strip_common(txt):
	''' removes common/descr words incl metas '''
	
	is_str = isinstance(txt, str)
	is_list = isinstance(txt, list)
	
	metas = values_list['metas']
	common_ = ['tour','plus','support','guest','guests','more']
	common_ += G.conjunctions + G.descr_like + list(metas) 
	for c in common_:
		if is_str:
			txt = re.sub(r'\b'+c+r'\b','',txt,flags=re.I)
			txt = remove_spaces(txt) # replace multi spaces with single
			txt = strip_chars(txt)
		elif is_list:
			if c in txt:
				txt.remove(c)
	return txt


def is_img_link(txt):
	''' determine if url is an image link 
		note: textcase in img links are unchanged
	'''
	is_ = False
	if isinstance(txt, str):
		if G.img_linker in txt:
			is_ = True
	return is_


def setup_for_loop(doclist):
	''' case: Fri 29; more likely than 29 Fri '''
	tmp = doclist[:]
	doclist = []
	return tmp, doclist


def check_doclist_len(doclist,**kwargs):
	''' remove lines below min or above max para len '''

	min_len, max_len = 3, 1000

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist or is_img_link(t) or t in G.pos_links:
			doclist.append(t)
		elif len(t) < min_len:
			try:
				t_ = int(t) # we want to keep possible date/month integers
				if 1 <= t_ <= 31:
					doclist.append(t)
			except: continue
		elif len(t) > max_len: continue
		else: doclist.append(t)
	return doclist


def get_time_suffix(time):
	''' get suffix for time '''
	time_suffixes = G.time_suffixes
	time = time.lower()
	suffix = None
	if any(s in time for s in time_suffixes):
		for s in time_suffixes:
			if s in time:
				suffix = s
				break
	else:
		suffix = 'hrs'
	return suffix


def get_time_tokens(time):
	''' get hr/min tokens for time '''
	time = time.lower()
	tokens = []
	r =  re.search(r'(\d{1,2})[:|.]*(\d{0,2})',time)
	if r:
		if r.group(1) and r.group(2):
			tokens = [int(r.group(1)), int(r.group(2))]
		elif r.group(1): #no mins eg 6pm so use 0 for 00
			tokens = [int(r.group(1)), 0]

		# for minutes round down to nearest quarter
		tokens[1] = (tokens[1] // 15) * 15
	return tokens


def convert_text_time(time):
	''' change times into 00:00 format '''

	converted = None

	# split <from> - <to> times; put single time in list
	times = [] 
	if '-' in time:
		times = time.split('-')
		times = [t.strip() for t in times]
	else:
		times = [time]

	for i in range(len(times)):

		t = times[i]

		# get suffix and time
		suffix = get_time_suffix(t)
		tokens = get_time_tokens(t)

		# deal with hour and reconstruct time to format
		if tokens:
			if suffix in ['am','a.m']:
				if tokens[0] >= 12:
					tokens[0] = 0
			
			elif suffix in ['pm','p.m']:
				if tokens[0] < 12:
					tokens[0] += 12
				elif tokens[0] >= 24:
					tokens[0] = 0				
			
			elif suffix in ['hrs','hr']:
				if tokens[0] >= 24:
					tokens[0] = 0

			times[i] = str(tokens[0]).zfill(2)+':'+str(tokens[1]).zfill(2)

		else: # eg random chars like 6Am capture from 6Amblah
			times[i] = None

	# join up times to remake string; if either is None, skip else NoneType err
	if None not in times:
		converted = ' - '.join(times)

	return converted


def hrs_mins_check(hrs, mins):
	''' check if hours:mins are valid '''
	
	valid = False

	# mins should end in multiples of 15: this is an assumption
	# to help distinguish from years: obvs an issue in 2030 A.D! 
	valid_mins = ['00','15','30','45']

	if not isinstance(hrs, int):
		try: hrs = int(hrs)
		except: return valid

	if not isinstance(mins, str):
		try: mins = str(mins)
		except: return valid

	if hrs < 24:
		if mins in valid_mins:
			valid = True
		else:
			mins = int(mins)
			if mins < 60 and mins % 10 == 0:
				valid = True

	return valid


def basic_time_test(txt):
	''' quick contextual test for time '''
	
	basic = False
	descr_len = 50
	max_dig = 4

	if txt == None or len(txt) == 0 or \
		not re.search(r'\d+',txt):
		basic = False

	elif any(s in txt for s in G.time_suffixes):
		basic = True

	elif re.search(r'(?<!\d)\d{2}:\d{2}(?!\d)', txt):
		basic = True

	elif len(txt) > descr_len:
		# post {2}:{2} above dates + series of times > len=50 can pass
		basic = True

	elif re.search(r'\d+',txt) and \
		('/' in txt or \
		re.search(r'\d+[\:|\.]\d+[\:|\.]\d+', txt)):
		# catch date types: 10/12 or 10.1.19
		basic = False

	elif not any(s in txt for s in G.time_suffixes) and \
		not any(s in txt for s in G.time_separators) and \
		not re.search(r'\d{4}',txt):
		# \d{4} to exempt 1100 - 1700
		basic = False

	# to catch 1100-1700 types
	# we'll test for date types 1720 - 1860 and that both tokens pass
	elif re.search(r'(\d+?\s*-\s*\d+?)', txt):
		finds = re.findall(r'(\d{4}\s*-\s*\d{4})', txt)
		if finds:
			found = finds[0]
			token = found.split('-')
			token = [tok.strip() for tok in token]
			basics = []
			
			for tok in token:
				hrs = int(tok[:2])
				mins = int(tok[2:])
				basic = hrs_mins_check(hrs, mins)
				basics.append(basic)
			if all(basics):
				basic = True

	# 09.50 types; assume will have leading zero for <10
	elif re.search(r'(\d{1,2}[\.|\:]\d{1,2})', txt):
		finds = re.findall(r'(\d{1,2}[\.|\:]\d{1,2})', txt)
		if finds:
			token = None
			found = finds[0]
			if '.' in found: token = found.split('.')
			if ':' in found: token = found.split(':')
			if token:
				hrs = int(token[0])
				mins = int(token[1])
				basic = hrs_mins_check(hrs, mins)

	elif re.search(r'^\d+$', txt):
		dig = re.search(r'^(\d+)$', txt)
		dig = dig.group(1)
		if len(dig) != 4: #only valid case: 2200 with no separators 
			basic = False
		else:
			hrs = int(dig[:2]);
			mins = int(dig[2:])
			basic = hrs_mins_check(hrs, mins)
		
	return basic


def basic_time_token_test(token):
	''' check if time token passes muster '''
	
	basic = True
	
	if not re.search(r'\d+',token):
		basic = False # can't be time if no numbers
	elif any(re.search(suff+r'\b', token) for suff in G.time_suffixes):
		pass # passes b/c contains am/pm etc
	else:
		# try just numbers as number plus non-suffix is invalid
		dig = None
		try:
			# of type 2200; nb will fail if can't do int()
			dig = str(int(token))
		except:
			# of type 22:30 without suffix
			dig_sep = re.search(r'(\d{1,2})[\:\.](\d{1,2})',token) 
			if not dig_sep:
				basic = False # as can't be number with non-suffix text

		if dig:

			if len(dig) != 4: # we dont want 10, 320, 98743 etc
				basic = False
			else:
				# we need to avoid year 2020 which is the year
				# being interpreted as time 20:20
				# so we'll look around the current year as a check
				if int(dig) in nearby_years(lookaround=2):
					basic = False
				else:
					hrs = int(dig[:2]); mins = int(dig[2:])
					basic = hrs_mins_check(hrs, mins)

		elif dig_sep:
			hrs = dig_sep.group(1); mins = dig_sep.group(2)
			basic = hrs_mins_check(hrs, mins)

	return basic


def match_time_suffix(txt):
	''' match from with to suffix in case: 6 - 8pm '''

	for suff in G.time_suffixes:
		no_suff = re.search(r'(\d{1,2}[.|:]*\d{0,2})\s*-\s*(\d{1,2}[.|:]*\d{0,2}'+suff+'+)',txt, flags=re.I)

		if no_suff:
			matched = no_suff.group(0)
			unsuffed = no_suff.group(1)
			suffed = no_suff.group(2)

			# suff the unsuffed 
			# suffix may be diff btw from and to
			try: unsuff_hr = int(unsuffed[:2])		# 10 - 6pm or 10:20 - ...
			except: unsuff_hr = int(unsuffed[:1])	# 7 - 6pm
			try: suff_hr = int(suffed[:2])			# ... - 11pm
			except: suff_hr = int(suffed[:1])		# ... - 1pm
				
			# case: 10 - 3pm
			if suff == 'pm':
				if unsuff_hr > suff_hr:
					if unsuff_hr == 12:
						suff = 'pm' # 12pm - 6pm
					else:
						suff = 'am' # to get: 10am - 3pm

			elif suff == 'am':
				if unsuff_hr > suff_hr:
					if unsuff_hr == 12:
						suff = 'am' # 12am - 6am
					else:
						suff = 'pm' # to get: 10pm - 2am

			now_suffed = unsuffed + suff
			txt = txt.replace(matched, now_suffed + ' - ' + suffed)

	return txt


def get_time(txt,as_input=True):
	''' get event times from text '''

	# as_input = True: get time as originally in doclist eg 3pm
	# as_input = False: convert time from 3pm to 15:00 

	# lowercase b/c cal funcs use this
	# and we haven't done the general .lower() yet
	txt = txt.lower() 

	orig, origs = None, []
	time, times = None, []

	if is_img_link(txt) or \
		txt is None or \
		isinstance(txt,int):
		return None

	# prep
	if isinstance(txt,list): txt = txt[0]

	# make patterns for time regex
	p2, p4 = r'\d{1,2}', r'\d{4}'
	suffixes = '|'.join(G.time_suffixes)
	seps = '|'.join(G.time_separators)

	# pattern generator
	def make_pattern(seps,suffixes):
		''' generator for patterns '''

		patterns = [

				# case: 8.15pm or 20:30
				r'(?<!\d)('+p2+r'['+seps+']*'+p2+r'\s*['+suffixes+r']*)\D*',

				# case 12pm
				r'(?<!\d)('+p2+r'\s*['+suffixes+r']*)\D*',

				# case: 2030
				r'(?<!\d)('+p4+r')\D*',

				]
		for p in patterns:
			yield p


	# split into tokens
	if basic_time_test(txt):

		tokens = txt.split()
		for tok in tokens:

			if not basic_time_token_test(tok): 
				continue
		
			# get all times
			for pattern in make_pattern(seps,suffixes):
				found = re.findall(pattern, tok, flags=re.I)
				if found:
					for f in found:
						origs.append(f)
						tok = tok.replace(f,'')
						if not as_input:
							times.append(convert_text_time(f))

	#recast as string
	if origs: orig = ','.join(origs)
	if times: time = ','.join(times)

	if as_input:
		return orig
	else:
		return time


def remove_ordinals(doclist,**kwargs):
	''' remove ordinals incl 'th of [mth] '''

	ordinals = G.ordinals

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		# don't call possibe_date else circular ref shown below
		# this -> possible_date -> strip_time -> strip_dates -> this 
		if is_img_link(t) or \
			t.lower() in ordinals or \
			not possible_date(t):
			doclist.append(t)
		
		else:
			if any(o in t.lower() for o in ordinals):
				for o in ordinals:
					ords = \
					re.findall(r'(\d{1,2}\s*'+o+r'\s*o*f*\s*)(?![a-zA-Z])', t)

					# nb. lookahead to avoid 2 Thursday becoming '2 ursday'
					if ords:
						for r in ords:
							r_ = re.sub(o, '', r, flags=re.I)
							t = re.sub(r, r_, t, flags=re.I)
							t = t.strip()
				doclist.append(t)
			else:
				doclist.append(t)

	return doclist


def strip_dates(txt):
	''' strips obvious dates from txt '''

	months = G.all_months

	if txt is None or \
		not isinstance(txt, str):
		return txt
	
	# by now we should have months represented as text
	# else this function won't work
	# note that we won't catch dow on own line
	# for that run: strip_dow()
	# don't call possible_date() from here else circular ref:
	# this -> possible_date -> strip_time -> this
	if not any(mth in txt for mth in months):
		return txt
	
	else:

		txt = remove_ordinals([txt])[0]

		for mth in months:

			# can't use date_patterns as that uses
			# [a-zA-Z]{3,9} which can catch things like
			# 'concert' in 'concert 23 jan 2020'
			# we'll also do years separately to not confuse with time
			patts = [	r'(\d{1,2}\s' + mth + r')',
						r'(' + mth + r'\s\d+)',
					]

			for patt in patts:
				if mth in txt:
					finds = re.findall(patt, txt)

					if finds: 
						for f in finds:
							txt = txt.replace(f, '')

		# here b/c the year is likely attached to found month
		years = nearby_years(lookaround=10)
		years = [str(yr) for yr in years]
		for yr in years:
			txt = txt.replace(yr,'')

	# clean up
	for l in G.pos_links:
		linked = ' ' + l + ' '
		if linked in txt:
			txt = txt.replace(linked, '') 
	
	txt = remove_spaces(txt)
	txt = txt.strip()
	txt = strip_chars(txt)

	return txt


def strip_time(txt,strip_dates_too=False):
	''' strips time from any text '''

	markers = G.time_markers + G.time_suffixes
	signs = G.time_signs
	mal_end = [':','.','-']
	eras = G.eras
	pos_links = G.pos_links

	if is_img_link(txt) or txt is None: return txt

	# check for time: returns tuple (original, conversion to 24hr) or None
	orig, time = None, None
	linked_end = False
	try:
		positions = []
		orig = get_time(txt)

		# now we know there's time in text
		# we can strip the orig time (not conversion) from txt
		# this might leave a trailing 'end' to be stripped if case:
		# Blah - time or Blah <from time> to <to time>
		# but if trailing end is not b/c of time strip and was there before
		# then we want to leave for concat_ends() 
		if any(txt.endswith(l) for l in pos_links):
			linked_end = True

		# replace original time in text
		origs = orig.split(',')
		
		# find where times are in txt and test for joins
		# replace time joins with '-'
		for o in origs:
			positions.append(txt.find(o))

		for p in range(1, len(positions)):
			subset = txt[positions[p-1]:positions[p]]
			for pos in pos_links:
				if pos in subset:
					if pos == '-': continue # no need to replace
					subset_ = subset.replace(pos, ' - ')
					txt = txt.replace(subset, subset_)
			
		# replace original time in text
		for o in origs:	
			txt = re.sub(o,'',txt,flags=re.I)

	except: return txt # failed i.e. get_time retuned None

	#remove signs and pre_markers
	for m in markers:
		txt = re.sub(r'\b'+m+r'\b', '', txt, flags=re.I)
	for s in signs: txt = txt.replace(s, '')
	txt = remove_spaces(txt)
	txt = txt.strip()	

	# strip out dates
	if strip_dates_too: 
		txt = strip_dates(txt)

	# strip ends if txt was not originally end linked
	if not linked_end:
		for l in pos_links:
			if txt.endswith(l):
				txt = txt.strip(l)
				txt.strip()
	
	# clean up
	txt = remove_spaces(txt)
	txt = strip_chars(txt)

	return txt 


def get_mth(txt,get_year=False):
	''' get month in a text, can also serve as a check '''

	d_yr, d_mth, done = None, None, False

	if isinstance(txt, str) and not is_img_link(txt):

		txt = strip_time(txt)

		# else mth is text
		for mth in G.all_months:
			if re.search(r'\b'+mth+r'\b',txt):
				d_mth = mth
				done = True
				break

		# check if mth is number case; d/m/y dates	
		if not done:
			for s in G.date_separators:
				chk = \
				re.findall(r'(\d{1,2})'+s+r'(\d{1,2})'+s+r'{0,1}(\d{0,4})',txt)
				if chk:
					mths = list(G.mths_dict.keys())
					mth = chk[0][1] # British-style dates where mth is 2nd item
					for m in mths:
						if G.mths_dict[m][0] == int(mth):
							d_mth = m
							done = True

	if get_year:
		try:
			d_yr = re.findall(r'(\d{4})',txt)[0]
		except:
			pass
		return d_mth, d_yr
	else:
		return d_mth


def can_be_mth_head(txt):
	''' check if txt can be month head '''

	#we expect mth head to be of the type:
	#<month>, <month year> or
	#'Events in <month>$' or '^<month yr> at the <venue>'

	can = False	
	mth = get_mth(txt)
	
	if mth:

		digits = re.findall(r'(\d)',txt)
		if digits:
			if len(digits) != 4:
				#eg March 21, 2019 or March 21 or 12 March => not mth heads
				return can

		for m in G.venue_markers: # eg Events 'at the'
			txt = re.sub(r'.*(\b'+m+r'\b.*$)','',txt,flags=re.I)

		for m in G.header_markers: # eg Events 'in' June 
			txt = re.sub(r'\b'+m+r'\b','',txt,flags=re.I)

		txt = re.sub(mth,'',txt,flags=re.I)
		txt = re.sub(r'[0-9]','',txt) # remove numbers
		txt = strip_chars(txt)

		# we want no other text
		if len(txt) == 0: can = True

	return can


def has_date_text(txt):
	''' finds any text with mth or dow '''
	has_ = False
	txt = txt.lower()
	for period in G.mth_dow:

		# check for dow or months but ignore 'weekend, weekday'
		if period in G.weekdays: continue
		if re.search(r'\b'+period+r'\b',txt):
			has_ = True
			break
	return has_


def possible_date(txt):
	''' check if text/numbers likely to be date '''
	
	pos_date = False
	max_len = 100 # likely random date buried in descr

	if not isinstance(txt, str): return pos_date

	# prepare text
	txt = strip_time(txt)
	txt = strip_currencies(txt)


	if ':::' in txt: 
		txt = txt[:txt.find(':::')]

	# return stuff unlikely to be dates
	if not re.findall(r'\d+',txt) or \
		any(c in txt for c in G.currencies) or \
		re.search(r'(\(\d{2,4}\))',txt) or \
		is_img_link(txt) or \
		'u+' in txt or \
		len(txt) > max_len:
		return pos_date


	# make patterns for date
	p2, p4 = r'\d{1,2}', r'\d{4}'

	def make_pattern(s):
		''' generator for patterns '''

		patterns = [

				# case: 8.10.17
				r'(?<!\d)('+p2+s+p2+s+p2+r')\D*$',

				# case: 8.10.2017
				r'(?<!\d)('+p2+s+p2+s+p4+r')\D*$',

				# case: 8.10
				r'(?<!\d)('+p2+s+p2+r')\D*$',

				# case: 2018-04-16
				r'(?<!\d)('+p4+s+p2+s+p2+r')\D*$',

				# case: 04-jun-2018
				r'(?<!\d)('+p2+s+r'[a-zA-Z]{3,9}'+s+p4+r')\D*$',

				# case: June|Thursday 5[th]
				r'([a-zA-Z]{3,9}'+s+p2+r'\D+)',
				r'([a-zA-Z]{3,9}'+s+p2+r'$)',

				# case: Jan. 20; not jan 2020
				r'([a-zA-Z]{3,9}\.*\s*\d{1,2})(?!\d)',

				# case: 5[th] Dec
				r'('+p2+r'\s*[a-zA-Z]{0,2}\s*[a-zA-Z]{3,9})',

				# case: 5[th] of
				r'('+p2+r'\s*st)(?!\w)',	r'('+p2+r'\s*nd)(?!\w)', 
				r'('+p2+r'\s*rd)(?!\w)',	r'('+p2+r'\s*th)(?!\w)', 
				r'('+p2+r'[a-zA-Z]{2}\sof)',

				]

		for p in patterns:
			yield p


	#check using separators: note includes space separator
	for s in G.date_separators:

		if not pos_date: # not found yet in loop
			patts = make_pattern(s)
			
			for p in patts:
				found = re.search(p,txt)
				
				if found:

					if s != '\s':
						# case: 18/10/2020 or 17/10
						if re.search(r'\d{1,2}'+s+r'\d{1,2}(?![a-zA-Z])', txt):
							pos_date = True
							break

					elif re.search(r'[a-zA-Z]{3,9}',txt):
						# month names
						if any(per in txt for per in G.mth_dow) and \
							has_date_text(txt):
							pos_date = True
							break

					elif any(re.search(r'\d{1,2}\s*'+o+r'(?!\w)',txt) for 
											o in G.ordinals):
						# case 18th of January
						pos_date = True
						break

					elif s == '\s':
						# cases: 23 11 2019, 2019 12 01, 23 11
						# b/c checked at replace_digit_with_text()
						# and there we already have spaces
						# #\w avoids post codes eg B5 1XY
						if re.search(
					r'(?!<\d)\d{1,2}'+s+r'\d{1,2}'+s+r'\d{4}(?!\d)',txt) or \
							re.search(
					r'(?!<\d)\d{4}'+s+r'\d{1,2}'+s+r'\d{1,2}(?!\d)',txt) or \
							re.search(
					r'(?!<\d)\d{1,2}'+s+r'\d{1,2}(?!\d)(?!\w)',txt):
							pos_date = True
							break
	
	return pos_date


def strip_not_text(txt,keep):
	''' remove words not in what from text 
		primarily for stripping lines to check for dates
		don't use this if you need dashes as joins
	'''

	puncts = G.puncts + G.quote_marks

	# create list of words to remove
	if isinstance(keep,str):
		keep = [keep]
	words = re.findall(r'[a-zA-Z]+',txt,flags=re.I)
	
	# sort by longest before removals
	sorted(words, key=len)
	for w in words:
		w = w.strip()
		if w not in keep:
			txt = re.sub(r'\b'+w+r'\b','',txt)

	# remove all remaining special chars or free standing words
	# nb not using re.sub(r'\W',' ',txt) to avoid '-' in 20 Feb - 21 Feb
	finds = re.findall(r'(\s{2,}\D+)',txt)
	for f in finds:
		if f.strip() not in keep:
			txt = re.sub(f,'',txt) 	# free standing words
	for punct in puncts:
		txt = re.sub(r''+punct,'',txt)	# incl likes of '!' not in strip_chars
	txt = txt.strip()
	
	# handle '- blah' as in '20 february Luke Jazz trio - february residency' 
	# remove '- february in the above 
	# split by ' - ' and work backwards testing we don't remove dates
	if ' - ' in txt:
		txt = txt.split(' - ')
		for t in reversed(txt):
			if not possible_date(t) and \
				not re.search(r'\d{1,2}',t):
				txt.remove(t)

		# reconstitute as text
		if len(txt) > 1:
			txt = ' - '.join(txt)
		else:
			txt = txt[0]

		# clean up
		txt = remove_spaces(txt)
		txt = txt.strip()

	# remove trailing dashes
	while any(txt.endswith(dash) for dash in G.dashes):
		txt = txt[:-1]
		txt = txt.strip()

	txt = strip_chars(txt)

	return txt


def is_address(txt):
	''' looks like an address '''

	is_ = False

	street_signs = ['road','street','avenue']

	# ignore img & time txt as could end per case: Blah 3am
	if get_time(txt) or is_img_link(txt) or possible_date(txt):
		return is_

	# ignore if has words that might indicate title eg tags in : 
	# to avoid case: 5s in 'Playtime for Under 5s being picked up as post code
	# note > regex massively expensive: 
	# 	any(re.search(r'\b'+tag+r'\b',txt) for tag in values_list['tags']
	if txt in values_list['tags'] or \
		any(txt.startswith(tag+' ') for tag in values_list['tags']) or \
		any(txt.endswith(' '+tag) for tag in values_list['tags']) or \
		any(' ' + tag + ' ' in txt for tag in values_list['tags']):
		return is_ 

	# check for street signs
	# will work for most things but will be false +ve for show '7th Avenue'
	# should catch full adress where post/zip may not be final elems 
	elif any(re.search(r'\d+.*?'+r'\b'+sign+r'\b', txt) 
								for sign in street_signs):
		is_ = True

	elif any(re.search(r'.*?'+r'\b'+sign+r'\b.*?[a-zA-Z]{1,2}\d{1,2}', txt) 
								for sign in street_signs):
		# case: Blah Theatre, Randle Street, POST CODE
		is_ = True

	elif re.search(r'(?<!\w)[a-zA-Z]{1,2}\d{1,2}\s*$',txt) or \
			re.search(r'(?<!\d)\d{1,2}\s*[a-zA-Z]{1,2}\s*$',txt) or \
			re.search(r'\d{5,}$',txt):
			# nb here we expect post/zip to be on own line or final elems
			# else might catch dates, descr and other stuff 
			# post/zip codes: eg SE17, 3PA, 10110;
			is_ = True

	elif txt in G.countries:
		is_ = True

	return is_


def is_descr(txt):
	''' txt looks like a description '''
	
	is_ = False
	min_len, threshold, min_words = 50, 5, 8
	txt = txt.lower()
	descr_words = G.conjunctions + G.descr_like
	found = []

	# we try to get to essential descr text
	# strip time, months and digits
	txt = strip_time(txt)
	txt = re.sub(r'\d','',txt)
	for mth in G.all_months:
		txt = txt.replace(mth,'')
	txt = remove_spaces(txt)
	txt = txt.strip()
	
	# ignoring this at mo as stuff ending in strip chars is unlikely to 
	# be title and by leaving them in here they might pass is_descr
	# and thus not qualify as title
	#txt = strip_chars(txt)

	if is_img_link(txt) or \
		' ' not in txt or \
		is_address(txt) or \
		len(txt) < min_len: 
		return is_

	# unlikely if it starts with a quote mark
	quote_marks = G.quote_marks + G.star_quotes + G.non_regex_quotes
	if txt[0] in quote_marks: 
		return is_
		
	# test for conjunctions / joining words > test also for puncts ending as
	# can have short part descr that don't have conjuctions
	# eg "Think you've got the brains? Well, we've got the quiz!"
	if not any([re.search(r'\b'+c+r'\b',txt) for c in G.conjunctions]) and \
		not any(re.search(r''+punct+r'$',txt) for punct in G.puncts):
		return is_

	# text has ignore_desc but check against longer len
	for ign in G.ignore_descr:
		if re.search(r'\b'+ign+r'\b',txt,re.IGNORECASE) and \
			len(txt) < min_len * 2:
			return is_

	# starts with an invalid term
	if any(txt.startswith(i) for i in G.descr_inval_starts):
		return is_

	# several words suggest descr
	# search for min_words: re.findall is expensive so using ' '
	if not possible_date(txt):
		if ' ' in txt and txt.count(' ') < min_words - 1:
			return is_
		else:
			is_ = True


	# if ends with a full stop then likely a descr
	# also exclamation but that's a more possible as title esp kids evts
	val_ends = ['.','!']
	if txt[-1] in val_ends:
		is_ = True


	# we'll check against words that indicate genuine description
	if is_:
		found = 0
		threshold = 5
		for wd in descr_words:
			finds = re.findall(r'\b'+wd+r'\b',txt)
			found += len(finds)

		# if ens in punctuation then likely a descr else test threshold
		if any(re.search(r''+punct+r'$',txt) for punct in G.puncts):
			pass
		elif found < threshold:
			is_ = False

	return is_


def concat_descriptions(doclist,**kwargs):
	''' concatenates desc r looking lines '''

	puncts = G.puncts

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t) or t in G.pos_links:
			doclist.append(t)

		else:

			t_ = doclist[-1]

			if is_descr(t) and is_descr(t_):
				# strip possible 'Blah , ...' which might indicate
				# removed read more link leading to longer descr
				t_less = t[:-5]
				t__less = t_[:-5]
				if t__less in t_less:
					# if prior line in this, replace with this
					doclist[-1] = t 
				else:
					doclist[-1] += ' ' + t

			elif any(t.endswith(p) for p in puncts) and \
				any(t_.endswith(p) for p in puncts):
				# sentences
				doclist[-1] += ' ' + t

			else: doclist.append(t)

	return doclist


def is_quote(string):
	''' remove quotes - mostly reviews '''
	
	is_ = False
	likely_len = 30
	quote_marks = G.quote_marks + G.non_regex_quotes
	star_quotes = G.star_quotes

	if is_descr(string): 
		return is_

	# usually of type: "Fantastic" - Guardian or '*** Brilliant'
	# while titles in quotes don't usually (but can) have text after
	for star in star_quotes:
		if star not in string: continue
		finds = string.count(star)
		if finds >= 2:
			is_ = True
			break

	if not is_:
		for q in quote_marks:
			
			if q not in string: 
				continue
			
			if not is_:
				beg = time.time()
				finds = re.search(r'^'+q+r'.*'+q+r'(.*$)', string)			
				if finds:
					if len(finds.group(1)) > 0:
						# there's text post quotes eg 'Brilliant' - Metro
						is_ = True
						break

					elif len(string) > likely_len:
						# no text post quotes but string is long 
						# case: music album review quotes can be long
						is_ = True
						break

					else:
						# short string - could be event title eg for kids
						continue

				# assume titles in quotes are shortish-ish
				elif not finds and len(string) > likely_len:
					for q in quote_marks:
						if string[0] == q:
							is_ = True
							break

				# some quote marks don't respond well to regex
				elif not finds:
					for q in G.non_regex_quotes:
						if string.startswith(q):
							is_ = True
							break

	return is_


def remove_duplicated_lines(doclist):
	''' removes duplicated lines '''
	
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		if not doclist:
			doclist.append(t)

		elif get_time(t) and not get_time(doclist[-1]) or \
			get_time(doclist[-1]) and not get_time(t):
			# avoid mth \n date=7 \n time=7pm being mistaken for repeated
			doclist.append(t)

		else:	
			# rather than if t == doclist[-1]
			# might get: Blah blah ... \n Blah blah
			# deal with ellipsis and such endings
			last_t_minus = doclist[-1].rstrip('.!?')
			this_t_minus = t.rstrip('.!?')
			if last_t_minus in this_t_minus or \
				this_t_minus in last_t_minus:
				if len(last_t_minus) >= len(this_t_minus):
					continue
				else:
					doclist.pop()
					doclist.append(t)
			else:
				doclist.append(t)
	return doclist


def remove_prior_events(doclist,**kwargs):
	''' remove lines suggesting old/past/previous events '''

	# bigger prob with art galleries where lists of old exhibitions
	# are still shown on page with some event dates but not the years
	#start half-way down to avoid top of page news, article dates etc

	past = ['past','previous']
	types = ['event','exhibition','gig','production']
	min_past = 2 # more than 2 prior years may indicate old lines
	found, found_line, pos_date_found, past_break = [], None, False, False

	top_mths = {}

	def remove_lines(doclist,found_line):
		while len(doclist) > found_line:
			doclist.pop()
		for j in range(6): # add fake lines so get_title loop works
			doclist.append('fake ' + str(j))
		return doclist


	# it's possible to have a long page preample
	# this can interfere with splitting into halves to find repeats
	# delete up to half-way yo first date if preamble > X
	# X should leave enough room for trav_up loop
	doclen = len(doclist)
	first_date_row = 0
	if doclen > 200:
		for i in range(len(doclist)):
			if possible_date(doclist[i]):
				first_date_row = i
				break
		partway = math.floor(first_date_row*0.5)
		doclist = doclist[partway:]

	# check if prior months repeated in bottom half
	# but only for long doclens to avoid chopping small doclists
	# with many events of same month/year
	doclen = len(doclist)
	partway = math.floor(doclen*0.5)
	if doclen > 200:
		for i in range(partway):
			d = doclist[i]
			if possible_date(d):
				mth, year = get_mth(d,get_year=True)
				top_mths[mth] = i # last ref line

		check = None
		gap = math.floor(doclen/3)
		for i in range(partway, doclen):
			d = doclist[i]
			if len(found) < min_past:
				if possible_date(d):
					mth,year = get_mth(d,get_year=True)
					if mth:
						if mth in top_mths and \
							i - top_mths[mth] > gap:

							# check if month is for following year
							if year:
								if int(year) < G.today.year + 1:
									# not folowing year so prior month
									found.append(i)
								else:
									# later than this year so keep
									pass
							else:
								found.append(i)


			else:
				# note down line
				found_line = min(found)
				break

	if found_line: 
		doclist = remove_lines(doclist, found_line)



	# we can also look for past years
	# wrt art galleries with long list of past exhibitions
	# this will miss the past exh in the top section
	doclen = len(doclist)
	partway = math.floor(doclen*0.25)
	found, found_line = [], None
	for i in range(partway, doclen):
		d = doclist[i]
		if len(found) < min_past:
			if possible_date(d):
				finds = re.findall(r'(20\d{2})(?!\d)',d)
				if finds:
					# pick last one to avoid 
					# '<date/prior yr> to <date/next yr>'
					f = finds[-1]
					if int(f) < G.today.year: 
						found.append(i)
		
		else:
			# note down line of first prior year found
			found_line = min(found)
			break

	if found_line:
		doclist = remove_lines(doclist, found_line)


	# another method is to search for e.g. 'past events' and delete all below
	# need to avoid cases where such descriptions are top page nav links
	# so we'll check we have at least x dates before activating delete
	doclen = len(doclist)
	partway = math.floor(doclen*0.5)
	found, found_line = [], False
	for i in range(doclen):
		d = doclist[i].lower()

		# check for dates
		# ignore reg_evts which have the date duplicated
		# ignore ines with this_yr as could be d/last_yr - d/this_yr
		if possible_date(d):
			if G.reg_marker not in d and \
				str(G.today.year) not in d:
				found.append(i) 

		if any(p in d for p in past):
			for p in past:
				for typ in types:
					p_typ = p + ' ' + typ

					if len(found) >= min_past and \
						re.search(r''+p_typ+r's*',d,flags=re.I):
						found_line = i
						past_break = True
						break
				if past_break: break
		if past_break: break

	if found_line:
		doclist = remove_lines(doclist, found_line)

	return doclist


def insert_missing_space(txt):
	''' insert spaces between phrases '''

	txt = remove_spaces(txt) # catch any '    ' types

	# between date and month eg 15June
	no_space = re.findall(r'(\d{1,2}[a-zA-Z]{3,9})',txt)
	for no_ in no_space:
		char = \
			re.search(r'(\d{1,2})([a-zA-Z]{3,9})',no_)
		try:
			if any(mth in char.group(2) for mth in G.all_months):
				spaced = char.group(1) + ' ' + char.group(2)
				txt = re.sub(no_ , spaced, txt)
		except:
			pass

	# between words and commas eg Nov 5th,2018
	finds = re.findall(r'(,\S)',txt)
	if finds:
		for f in finds:
			txt = txt.replace(f, ', '+f[1:])

	return txt


def remove_erase_from(doclist):
	''' remove extraneous in 'Blah Blah class=more_blah' '''
	# we want the class=etc removed
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not is_img_link(t):
			t = t.lower()
			if any(i in t for i in G.erase_from_docline):
				for i in G.erase_from_docline:
					if i in t:
						
						# if we can find the form 
						# class='blah' title='blah'>
						# then take this out as there could be 
						# valid text we want after the >
						finds = re.findall(r'('+i+r'.*\>)',t)
						if finds:
							for f in finds:
								t = t.replace(f,'')
						else:
							# otherwise take everything from class= out
							t = t.split(i)[0]

		t = t.strip()
		if t:
			doclist.append(t)
	return doclist


def reset_unbalanced_parenthesis(string):
	''' makes open and close parenthesis equal '''

	parens = (('(',')'),('{','}'))

	if isinstance(string,str) and string != '':
		for paren in parens:

			op = paren[0]
			cl = paren[1]
		
			open_ = string.count(op)
			close_ = string.count(cl)
			
			if open_ == close_:
				return string
			
			else:		
				# create any necessary extra bracks
				if open_ > close_:
					for d in range(open_ - close_):
						string += cl

				if close_ > open_:
					for d in range(close_ - open_):
						string = op + string

	return string


def remove_rave_reviews(doclist):
	''' remove quotes from critics '''

	quote_marks = G.quote_marks
	star_quotes = G.star_quotes

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t):
			doclist.append(t)
		else:
			# remove quotes - can get mistaken for titles
			# but event titles can be in quotes
			# we'll always check from the line after in case
			# quotes split over 2 lines: 1. quote; 2. author
			if is_quote(doclist[-1]):

				if doclist[-1][0] in star_quotes:
					if doclist[-1][-1] in quote_marks:
						# starts with stars and ends with a quote
						# assume case: **** 'Brilliant'
						# and author on next line
						# so remove quote and don't add author
						doclist.pop()
						continue		

					else:
						# starts with stars and presumably ends with words
						# assume case: **** 'Brilliant' - The Herald
						# so author on prior line
						# remove prior and add this line
						doclist.pop()
						doclist.append(t)


				elif doclist[-1][0] in quote_marks:

					if doclist[-1][-1] in quote_marks:
						# starts and ends in quotes
						# could be title or simply a quote
						# assume quote if current line is just text
						# assume title if current line is a date
						if possible_date(t) or get_time(t):
							doclist.append(t)
						else:
							doclist.pop()

					else:
						# presumably ends in an alpha char
						# assume quote and quthor on prior line
						doclist.pop()
						doclist.append(t)
						continue

				elif is_quote(t):
					# last line and this one are quotes
					# potentially a list of review quotes
					# remove last line and don't add this one
					doclist.pop()
					continue

				else:
					doclist.pop()
					doclist.append(t)
					continue

			else:
				if is_quote(t):
					# don't add if current line is a quote
					continue

				else:
					doclist.append(t)
	return doclist


def remove_addresses(doclist):
	''' remove address '''
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not is_address(t):
			doclist.append(t)
	return doclist

def strip_html(doclist):
	''' remove html lines '''
	# nb that we have seen calendars with date cells incl html
	# so be carefuly aggressive about strips
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist or is_img_link(t):
			doclist.append(t)
		else:
			# skip if starts with or includes html terms
			# or class symbol '.' in text - nb id # could be legit title
			if any(t.startswith(html) for html in G.list_html) or \
				t.startswith('.') or re.search(r'\s\.',t):
				continue

			elif any(incl_h in t for incl_h in G.list_includes_html):
				incl_found = False
				for incl in G.list_includes_html:
					pos = re.search(incl, t)
					if pos:
						# get position of incl and excise
						pos = pos.span()[0] 
						t = t[:pos].strip()
						if len(t) > 0:
							doclist.append(t)
							incl_found = True
							break

				if not incl_found:
					doclist.append(t)

			else:
				doclist.append(t)
	return doclist


def remove_chars_from_pos_dates(doclist):
	''' remove extraneous chars from pos date '''

	# catch case: 'wed . 6'

	replace = ['·', '.', ',']
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist:
			doclist.append(t)
		else:
			for r in replace:
				for day in G.all_days:
					finds = re.findall(r'('+day+r'\s*'+r+r'\s*\d+)',t, 
							flags=re.I)
					if finds:
						for f in finds:
							f_ = f.replace(r,'')
							t = t.replace(f,f_)
			t = remove_spaces(t)
			doclist.append(t)
	return doclist	


def clean_doclist(doclist,**kwargs):
	''' clean up checks - funcs here expect string input '''

	print('.'*9, 'start clean doclist')
	
	beg = time.time()
	doclist = remove_erase_from(doclist)
	end = time.time()
	print('.'*12, 'remove erase from: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = [scrub_strings(t) for t in doclist]
	end = time.time()
	print('.'*12, 'scrub strings: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = [t for t in doclist if t != ''] # b/c scrub_str can return ''
	end = time.time()
	print('.'*12, 'remove blanks: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = [strip_chars(t,ignore_multi_mark=True) for t in doclist]
	end = time.time()
	print('.'*12, 'strip chars: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = remove_rave_reviews(doclist)
	end = time.time()
	print('.'*12, 'remove rave reviews: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = remove_addresses(doclist)
	end = time.time()
	print('.'*12, 'remove addresses: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = remove_duplicated_lines(doclist)
	end = time.time()
	print('.'*12, 'remove duplicated lines: ', str(round(end-beg,1))+'s')

	return doclist


def clean_line_breaks(doclist,**kwargs):
	''' clean up doclist from line breaks '''

	beg = time.time()
	print('...... start clean line breaks: ')

	headroom = 6
	min_len, max_len = 1, 9999
	done = False

	# in rare cases for simple webpages we may have a single line doclist
	# where eg <br/> used within single <div>
	if len(doclist) == 1:
		doclist = doclist[0].split('\n')

	# remove very long or short lines not pos_links or numbers
	doclist = check_doclist_len(doclist)

	# clean
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		# remove asterisk as leads to regex errors; strip and clean spaces
		while '*' in t:
			t = t.replace('*','')

		t = strip_chars(t); t = remove_spaces(t)

		if len(t) > 0:

			if not doclist or is_img_link(t) or t in G.pos_links:
				doclist.append(t)

			elif re.search(r'^\D{1}$',t): 
				continue # single non-digit
			
			elif re.search(r'^\W+$',t):
				continue

			elif re.search(r'\+\d+',t) and \
				'gmt' not in t.lower() and \
				not possible_date(t) and \
				not any(mth in t.lower() for mth in G.all_months):
				# case: phone numbers; avoids date/time
				continue

			elif re.search(r'\w{20,}',t):
				# case: div#yola-panel-inner-I68a1cfb2d1a146ca82d16a71fd24104d
				# unlikely such long strings from I68 ... are valid
				continue

			elif re.search(r'\d{20,}',t): # long numbers
				continue

			elif re.search(r'^[a-zA-Z]{1}\s[a-zA-Z]{1}$',t):
				# case: 'n p'
				continue

			else:
				doclist.append(t)

	end = time.time()
	print('.'*9, 'initial scrub: ', str(round(end-beg,1))+'s')

	# final and clean
	beg = time.time()
	doclist = strip_html(doclist)
	end = time.time()
	print('.'*9, 'strip html: ', str(round(end-beg,1))+'s')
	
	beg = time.time()
	doclist = remove_duplicated_lines(doclist)
	end = time.time()
	print('.'*9, 'remove dupl lines: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = [insert_missing_space(d) for d in doclist]
	end = time.time()
	print('.'*9, 'insert missing space: ', str(round(end-beg,1))+'s')

	beg = time.time()
	doclist = [reset_unbalanced_parenthesis(d) for d in doclist]
	end = time.time()
	print('.'*9, 'reset unbal paren: ', str(round(end-beg,1))+'s')	

	beg = time.time()
	doclist = remove_chars_from_pos_dates(doclist)
	end = time.time()
	print('.'*9, 'remove stuff from dates: ', str(round(end-beg,1))+'s')	

	beg = time.time()
	doclist = clean_doclist(doclist) # do now; we'll call again at process end
	end = time.time()
	print('.'*9, 'clean doclist: ', str(round(end-beg,1))+'s')

	return doclist


def convert_to_long_year(text):
	''' if date of type '18; change to 2018 '''
	apostr_yr = re.findall(r"(\'\d{2})",text)
	for apos in apostr_yr:
		apos_ = apos[1:] # strip leading apostrophe
		apos_ = int('20'+apos_) # convert to full year
		if G.today.year - 2 < apos_ <= G.today.year + 2:
			text = re.sub(apos, str(apos_), text)
	return text


def remove_day_count_info(text):
	''' remove things like 3-days etc 
	case: 'Photography course 3-days'
	'''
	dur = ['day']
	for d in dur:
		finds = re.findall(r'(\d+\s*-*\s*'+d+r's*)',
							text,flags=re.I)
		if not finds:
			finds = re.findall(r'(half-*\s*'+d+r's*)',
							text,flags=re.I)

		if finds:
			for f in finds:
				text = re.sub(f,'',text,flags=re.I)
	return text


def fix_multiple_and_dates(text):
	''' case: Sat 14 and Sun 15 July; replace 'and' with comma '''
	if possible_date(text):
		if ' and ' in text:
			and_finds = re.findall(r'\d{1,2}.*and.*\d{1,2}',text)
			for and_ in and_finds:
				# fix parens in case regex chops off a bracket
				and_ = reset_unbalanced_parenthesis(and_)
				and_comma = re.sub('and', ',' , and_)
				text = re.sub(and_, and_comma, text)
	return text


def scrub_strings(string,ignore_multi_mark=False):
	''' basic corrections to strings stuff '''

	if is_img_link(string): return string

	# strip
	string = string.strip()

	# convert to lower case
	# makes stuff cleaner and easier later on
	# nb. img_links excepted above as it's imp to keep these
	# as scraped else they won't be found on website
	if isinstance(string, str): string = string.lower()

	# return pos_links as needed for concatenation functions
	if string in G.pos_links: return string

	if string:
		# remove long digit segment unlikely to be dates eg 0700300900
		if not get_time(string) and re.search(r'\d{5,}',string):
			string = ''

		# remove long sequence of digits 
		# eg '24 3000, 14 Sep 2019, <more dates>'
		max_digs = 48 # eg 13.12.2018 - 15.01.2019 0730-2100(2x this type)
		finds = re.findall(r'\d',string)
		if len(finds) > max_digs:
			string = ''

	# lines beginning with these unlikely to be relevant
	not_starts = G.ignore_starts
	if not possible_date(string) and \
		any(string.startswith(n) for n in not_starts):
		string = ''

	# short_days kept in here so runs b4 scrub to take out
	# integers in case <yr>\n<yr>\n<yr>\n<Sat>\n<02>\n<Jun>
	# if short_days removed here we lose the 02 Jun date
	if string and string != '':

		# reset missing parens so regex doesn't fail
		string = reset_unbalanced_parenthesis(string)
		
		if string not in G.short_mths and \
			string not in G.short_days:

			# patterns to replace
			# we'll remove [...] and {...} lines as rarely relevant
			# but sometimes used and if left in, it fails ignore_doclist
			# remove tag instances of < Blah >
			patterns = [r'(\n)', r'(\\\\)', r'(- -)', r'.*(\{.*\}).*',
						r'(<\/*.*>)', r'.*(\[.*\]).*',
						r'(\-*\s*sold out)',r'(\-*\s*fully booked)']

			for patt in patterns:
				finds = re.findall(patt,string,flags=re.I)
				if finds:
					for f in finds:
						string = string.replace(f,'')

			# remove doctag prefixes
			if any(re.search(r'^'+d,string,flags=re.I) for d in G.doctags):
				for d in G.doctags:
					# remove d only at beginning of string so not using re.sub
					if re.search(r'^'+d,string,flags=re.I):
						string = strip_chars(string[len(d):])
						break

			# remove event duration - more likely at end of line
			# also remove word just before: lilely to be 'duration' etc
			mins = re.search(r'(\w+\s\d+\s*mins*$)',string,flags=re.IGNORECASE)
			if mins: string = re.sub(mins.group(1),'',string,flags=re.I)

			#standardise dash
			string = standardise_dashes(string)

			# convert apostrophe dates eg " '18 " to long form '2018'
			string = convert_to_long_year(string)

			# sometimes \d\m with no spaces eg 15Jun; insert space
			string = insert_missing_space(string)
		
			# remove things like 3-days etc
			string = remove_day_count_info(string)

			# case: Sat 14 and Sun 15 July; replace 'and' with comma
			string = fix_multiple_and_dates(string)

			# strip string
			string = strip_chars(string,ignore_multi_mark=True)

	return string


def replace_digit_with_txt(txt):
	''' replace mth digit with text where only digits like 28 10 2017 '''

	if not possible_date(txt): 
		return txt

	mths_dict = G.mths_dict

	for sep in ['/', '-', '.']:
		txt = txt.replace(sep,' ')
	
	# for digits only
	try:
		txt = int(txt)
		txt = list(mths_dict.keys())[txt-1]
	except: txt = str(txt)

	# to avoid regex catching eg 0 051 and picking 05 as May
	tmp = txt.split()
	for t in tmp:
		if len(t) not in [1,2,4]: # acceptable d, dd, mth, yr
			return txt

	# in case we have yyyy mm dd
	finds = re.findall(r'(?!<\d)\d{4}\s\d{1,2}\s*\d{1,2}$',txt)
	if finds:
		find = finds[0].split()
		if len(finds) == 3:
			txt = find[2] + '  ' + find[1] + ' ' + find[0]

	# continue now we know we have d m y
	txt = remove_spaces(txt)
	mth = re.match(r'\d{1,2}\s(\d{1,2})\s*\d{0,4}$',txt)
	mth_txt = ''
	if mth:
		mth = int(mth.group(1))
		if mth < 13: 
			mth_txt = list(mths_dict.keys())[mth-1]	
		else:
			return txt #n ot a month
		
		# need to avoid replacing date as in
		# 11 11 2017 going to Nov Nov 2017
		# note may only have 01 10 and no year
		_txt = txt.split(' ')
		txt = _txt[0]+' '+mth_txt
		if len(_txt) == 3: 
			if re.search(r'^\d{4}$',str(_txt[2])): 
				# case 05 06 2018
				pass
			elif re.search(r'^\d{2}$',str(_txt[2])):
				# short year type eg 18 for 2018
				_txt[2] = '20' + _txt[2]
			txt = txt +' '+_txt[2]
	
	return txt


def in_ignore_doclist(line):
	''' line is in ignore_doclist '''
	
	line = line.lower()
	in_ = False
	ignores = G.ignore_doclist

	if line in ignores: 
		in_ = True

	elif line.strip() in G.ignore_line:
		in_ = True 
	
	elif any(re.search(r'('+ign+r')',line) for ign in G.ignore_specials):
		in_ = True
	
	else:
		# not using re.search(r'\b'+ign+r'\b') as massively expensive
		if any(line.startswith(ign+' ') for ign in ignores) or \
			any(line.startswith(ign+':') for ign in ignores) or \
			any(line.endswith(' '+ign) for ign in ignores) or \
			any(' '+ign+' ' in line for ign in ignores):
			in_ = True

		elif re.match(r'\d+\sshow',line) or \
			re.match(r'\d+\sevent',line):
			# case: 5 shows in march << avoid read as '5 march'
			in_ = True

	return in_


def get_org_ignores(organiser=None):
	''' get org ignores '''

	org_ignore = []

	if organiser:
		org_ignore = organiser.exclude
		if org_ignore not in ['', None]:
			org_ignore = org_ignore.lower()
			try:
				org_ignore = org_ignore.split(';')
				org_ignore = \
					[i.lower().strip() for i in org_ignore if i.strip() != '']
			except:
				org_ignore = [org_ignore]

			# sort by longest words so long ignores are removed first
			org_ignore.sort(key=len,reverse=True) 

	return org_ignore



def remove_ignores(doclist,organiser=None,**kwargs):
	''' remove items in ignore doclist '''

	org_ignore = []

	metas = values_list['metas']
	metas = [m.lower() for m in metas]
	org_ignore = get_org_ignores(organiser)
	
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t):
			doclist.append(t)
			continue

		# next deal with org.exclude
		if org_ignore is not None:
			if any(ign in t for ign in org_ignore):
				for ign in org_ignore:
					if ign in t:
									
						if doclist[-1] == '-':
							# case: blah \n - \n ign 
							#(we also don't need the '-')
							doclist.pop()

						# to avoid errors
						ign = re.sub(r'(\(.*\))','',ign) 
						ign = ign.replace('+','\+')
						ign = ign.replace('|','\|')

						finds = re.findall(r'(-*\s*'+ign+r')',t,flags=re.I)
						finds = [f.strip() for f in finds]

						if finds:
							for f in finds:
								t = re.sub(f,'',t,flags=re.I)
								t = t.replace('()','')
								t = strip_chars(t)

						if len(t.strip()) < 2:
							t = 'x'

		if any(p in t for p in G.pic_extensions): 
			continue 

		elif 'http' in t: 
			continue # since not an img_link

		elif in_ignore_doclist(t):
			# remove trailing dashes in cases
			# [-1] = blah blah - \n [t] = ign
			# on the page it might look like blah blah - ign
			# if '-' left trailing it will be joined with 
			# something not relevant below
			if any(doclist[-1].endswith(d) for d in G.dashes):
				for d in G.dashes:
					if doclist[-1].endswith(d):
						doclist[-1] = doclist[-1].strip(d)
			continue

		elif t in metas or \
			any(t == m+'s' for m in metas): 
			# skip meta_tags - deciding for now not to use this info
			continue

		else:
			doclist.append(t)

	# nb. > 0 so single date digs pass
	doclist = [strip_chars(t,ignore_multi_mark=True) for 
				t in doclist if len(strip_chars(t)) > 0 
					and t.lower() != 'x']

	return doclist


def scrub_duplicate_images(doclist,**kwargs):
	''' removes duplicate images '''

	# dupl images can interfere with scrub_duplicates
	# nb. func removes xth listing for events with same img eg club nights
	# should be corrected with restack_images()
	done = []
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist or not is_img_link(t):
			doclist.append(t)
		elif t not in done:
			doclist.append(t)
			done.append(t)
		else: pass
	return doclist


def get_rows_with_integers(list_):
	''' get rows where items are integers '''
	rows, ints = [],[]
	for i in range(len(list_)):
		try:
			ints.append(int(list_[i]))
			rows.append(i)
		except:
			continue
	return rows, ints


def get_consecutive_int_rows(list_):
	''' get grouped rows with integer items '''

	groups, r_group, i_group = defaultdict(dict), [], []
	g_num, last_r = 1, None
	
	# add improbable last row so the last group can be captured
	improbable = 999999
	list_.append(improbable)

	# get list of rows with integers
	rows, ints = get_rows_with_integers(list_)

	# parse for consecutive rows
	for r, i in zip(rows, ints):
		
		if not r_group: #new group
			r_group.append(r)
			i_group.append(i)
			last_r = r
		
		else:
			
			# add to group if consecutive
			if r - last_r == 1 and i != improbable:
				r_group.append(r)
				i_group.append(i)
			
			else:
				# save group and reset
				groups[g_num]['rows'] = r_group
				groups[g_num]['ints'] = i_group
				g_num += 1

				r_group, i_group = [], []
				r_group.append(r)
				i_group.append(i)

			last_r = r

	list_.pop() # remove the improbable
	
	return groups


def remove_month_lists(doclist, **kwargs):
	''' remove lists of months '''
	tmp, doclist = setup_for_loop(doclist)
	for i in range(len(tmp)):
		t = tmp[i]
		if not doclist:
			doclist.append(t)
		else:
			
			t_ = doclist[-1]
			if can_be_mth_head(t) and can_be_mth_head(t_):
				doclist.pop()
			else:
				doclist.append(t)

	return doclist


def is_month_head_type(doclist):
	''' check if type to affix month head '''

	# applies if much fewer months than day digits
	# but first we clear up 
	doclist = remove_list_of_numbers(doclist)

	is_ = False
	count_mth = 0
	count_day = 0
	for d in doclist:

		if d == doclist[0]: continue
		
		if can_be_mth_head(d) and \
			not any(dash in doclist[-1] for dash in G.dashes):
			# avoid split dates of type
			# '3 feb - 7' \n 'mar' 
			count_mth += 1
		
		elif d.isnumeric():
			if 1 <= int(d) <= 31:
				count_day += 1
		
		elif d[0].isnumeric() and \
			not any(re.search(r'\b'+dash+r'\b',d) for dash in G.dashes) and \
			not any(re.search(r'\b'+mth+r'\b',d) for mth in G.all_months):
			# avoid '11 april' - clearly not mth_head type date
			dig = re.match(r'(\d{1,2})\s',d)
			if dig:
				if 1 <= int(dig.group(1)) <= 31:
					count_day += 1

	if count_mth > 0 and \
		count_day > 0 and \
		count_mth < count_day * 0.5:
		is_ = True

	return is_


def affix_month_heads(doclist, **kwargs):
	''' add month name to numbers for non calendars '''

	is_ = False
	months_found, digits_found = [], []

	if kwargs['is_calendar']:			return doclist
	if not is_month_head_type(doclist):	return doclist

	# in some cases we have a calendar but month is outside table
	# so we end up with <mth> 28 29 30 1 2 .... 31 1 2 3 < next_mth
	# we identify prior cal month dates and replace
	numerics, heads = [], []
	suspect_prior, suspect_next = [], []

	for i in range(len(doclist)):
		d = doclist[i]

		if d.isnumeric() and 1 <= int(d) <= 31:

			if not heads:
				continue
			
			elif not numerics:
				
				# likely cal date if dd is high
				# case: pos calendar that fails is_calendar
				if int(d) >= 23:
					suspect_prior.append(i)
				else:
					numerics.append(i)

			else:

				# if dd drops then pos new month
				if int(d) < int(doclist[numerics[-1]]):
					
					# if new month found btw last numeric and this one
					# then passes as a nomal mth_head list
					if numerics[-1] < heads[-1] < i:
						numerics.append(i)

					else:
						# pos calendar that failed is_calendar
						# and this is the first few days of next month
						suspect_next.append(i)

				else:
					numerics.append(i)

		elif can_be_mth_head(d):
			heads.append(i)

	# reframe suspect invalid dd
	for num in suspect_prior:
		doclist[num] = 'suspect prior cal mth date: ' + str(doclist[num])
	for num in suspect_next:
		doclist[num] = 'suspect next cal mth date: ' + str(doclist[num])
			
				
	# affix
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist:
			doclist.append(t)

		elif can_be_mth_head(t):
			mth_head = t
			continue

		else:
			# test for date numbers
			try:
				t = int(t)
				if 1 <= t <= 31:
					t = str(t) + ' ' + mth_head
					doclist.append(t)
					continue
				else:
					doclist.append(str(t))
			except:
				doclist.append(t)

	return doclist


def remove_list_of_numbers(doclist,**kwargs):
	''' remove list of numbers '''
	
	del_ = []
	consec_dict = get_consecutive_int_rows(doclist)

	for k, group in consec_dict.items():
		if len(group['rows']) == 1:
			continue
		else:
			del_.extend(group['rows'])

	# delete lines if necessary
	if del_:
		del_.sort()
		for i in range(len(del_)):
			del doclist[max(del_)]
			del_.pop()	

	return doclist


def concat_start_ends(doclist,trav_uo=None,**kwargs):
	''' concat 't' to line before 't_' depending on 'e' & end of t_  '''

	start_ends = G.start_ends + G.pos_links
	time_starts = ['from',]

	# remove duplicate lines following each other
	doclist = remove_duplicated_lines(doclist)

	tmp, doclist = setup_for_loop(doclist)
	for i in range(len(tmp)):

		t = tmp[i]

		if not doclist or is_img_link(t):
			doclist.append(t)

		elif any(c == tmp[i-1].lower() for c in G.currencies):
			# for currencies split over over lines eg GBP \n 5.00
			# to avoid 5.00 being taken as time
			doclist[-1] = tmp[i-1] + t

		elif get_time(t) and \
			any(re.search(r'^\b'+j+r'\b',t,flags=re.I)
				for j in time_starts):
			# add time like 'from 8pm' to prior line of event info
			doclist[-1] += ' ' + t

		elif any(t.startswith(j.strip()+' ') for j in start_ends):

			# using .strip() as some start_ends like ' and'
			# are there to avoid endswith('band') and are
			# not applicable to startswith('and')

			# if a start_end phrase starts current line
			# then add to prior line except
			# 1. prior line is a date: to be handled by join_..()
			# 2. this line is a descr: handled by concat_descr..()
			# 3. this line is time: handled by concat_times()
			if not is_img_link(doclist[-1]) and \
				not possible_date(doclist[-1]) and \
				not doclist[-1].isnumeric() and \
				not is_descr(t) and \
				not get_time(t):
				doclist[-1] += ' ' + t
			else:
				doclist.append(t)

		elif any(doclist[-1].endswith(j) for j in start_ends):
				# append if link in prior line
				# only if prior line does not end with this line
				# case: prior='Blah -' ; this='- blah' ; avoid='Blah - - blah'
				if not doclist[-1].endswith(t):
					doclist[-1] += ' ' + t
				else:
					doclist.append(t)

		# case of multi_dates split over lines with 
		# case: 18 & \n 23 November
		elif any(doclist[-1].endswith(mm) for mm in G.multi_date_markers) and \
			not is_descr(doclist[-1]) and \
			(any(re.search(r'\b'+mth+r'\b', doclist[-1]) for 
								mth in G.all_months) or \
			any(re.search(r'\b'+day+r'\b', doclist[-1]) for 
								day in G.all_days) or \
			re.search(r'\d{1,2}',doclist[-1])):
			doclist[-1] += ' ' + t 

		# multi dates: 1, 5, \n July but not single 1 \n July
		elif re.search(r'\d{1,2}\D+?\d{1,2}$',doclist[-1]) and \
			any(re.search(r'^\b'+mth+r'\b', t) for mth in G.all_months):
			doclist[-1] += ' ' + t 
		else:
			doclist.append(t)

	return doclist


def match_time_suffixes(doclist, **kwargs):
	''' remove space between dig and suffix and match from/to suffix '''

	suffixes = G.time_suffixes
	unsuffed = None

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		# remove any spaces between digits and suffix
		# ! precondition for get_time
		for suff in suffixes:
			split_suff = re.findall(r'(\d+\s'+suff+'+)',t, flags=re.I)
			if split_suff:
				# remove the space
				for s in split_suff:
					s_ = s.replace(' ','')
					t = t.replace(s, s_)

		# now check if time
		if not get_time(t): 
			doclist.append(t)
			continue

		t = match_time_suffix(t)

		doclist.append(t)

	return doclist


def find_years(txt,typ='find'):
	''' return or remove years in text '''

	if txt == None: return txt

	eras = G.eras
	end_with = ['0', '5'] # most times start/end in these mins eg 0715
	timemarks = ['.',':']
	found = []

	years = nearby_years(lookaround=10)
	years = [str(y) for y in years]

	remove, keep = False, False
	if typ == 'remove': remove = True
	if typ == 'keep': keep = True

	# deal with years
	if any(yr in txt for yr in years):
		for yr in years:
			if remove:
				txt = txt.replace(str(yr),'')
			elif keep:
				pass
			else:
				if yr in txt and yr not in found:
					found.append(yr)
	
	# deal with eras
	for e in eras:
		finds = re.findall(r'(\d{1,4}\s*'+e+r')(?![a-zA-Z])', txt)
		for f in finds:
			if remove:
				txt = txt.replace(f,'')
			elif keep:
				pass
			else:
				if f.strip() not in found:
					found.append(f.strip())

	if not any(e in txt for e in eras):
		patts = [r'(\d{4}\s*-\s*\d{4})', r'(\d{4})' ]
		
		for patt in patts:
			finds = re.findall(patt,txt)
			for f in finds:
				if '-' in f:
					f_ = f.split('-')
				else:
					f_ = [f,f]
				
				if any(t in f_ for t in timemarks):
					continue

				else:
					bust = False

					for g in f_:
						g = g.strip() #i n case: '   2019'
						
						if g[0] == 0: # probably phone number
							bust = True

						elif g in ['2005','2010','2015','2020']:
							# ignore pos years that got snagged by '0','5' test
							continue

						elif g[-1] not in end_with:
							# assume year eg 1516
							bust = True
							
						elif int(g[:2]) <= 20 and int(g[2:]) > 59: # eg 1870
							bust = True

					if remove:
						if bust:
							for g in f_:
								txt = txt.replace(g,'')	
					elif keep:
						pass
					
					else:
						for g in f_:
							# nb we've added eras already above
							if g not in found:
								if g.strip() not in found:
									found.append(g.strip())

	# replace text with years found
	if typ == 'find': 
		txt = found

	return txt


def strip_dow(txt, just_from_dates=True, months=False):
	''' remove days of week from text 
		esp as dow in dates might be false +ve title 
		note: sometimes we might want to strip from non-dates
	'''
	
	pos_date = possible_date(txt)
	to_strip = G.all_days
	if months:
		to_strip = G.mth_dow

	# exit if invalid stuff
	if txt is None or not isinstance(txt, str):
		return txt

	if just_from_dates:
		if not pos_date:
			return txt

	for day in to_strip:
		# keep 'every ' as text often meaning less without day
		# case event title: 'every monday is comedy'
		# >> 'every is comedy'
		# also note: not looking for 'mondays' with the 's'
		if day in txt:
			txt = re.sub(r'(?<!every\s)\b'+day+r'\b','',txt,flags=re.I)

	txt = remove_spaces(txt)
	txt = strip_chars(txt)

	return txt


def set_calendar_month_heads(doclist,**kwargs):
	''' set lines that serve as calendar month heads '''

	# important because calendars may have headers of type
	# Jan Feb Mar where Jan=Prior, Feb=current month & calendar, Mar=Next

	if not kwargs['is_calendar']: return doclist

	cal_month_mark = G.cal_month_mark
	long_mths = G.long_mths

	single_calendar = True

	tmp = doclist[:] # not using setup as we don't want to empty docliost
	cal_mths, mth_lines = [], []
	the_mth = ''

	# go through and id months and doclist lines
	for i in range(len(tmp)):
		t = tmp[i]
		if can_be_mth_head(t):
			mth = get_mth(t)
			mth = G.short_long[mth[:3]]
			if mth not in cal_mths:
				cal_mths.append(mth)
				mth_lines.append(i)

	if mth_lines:
		sum_diff = 0
		last_l = None
		for l in mth_lines:
			if not last_l: 
				last_l = l
			else: 
				sum_diff += (l - last_l)
				last_l = l


		if sum_diff / len(mth_lines) > 20:
			single_calendar = False


	if not single_calendar:
		for l in mth_lines:
			doclist[l] = cal_month_mark + doclist[l]


	if single_calendar:

		if len(cal_mths) == 0:
			pass

		elif len(cal_mths) <= 2:
			# if len=1 then that is the month
			# if len=2 then of sort (i) Jan Feb or (ii) Feb Jan
			# if (i) we assume current=Jan and Feb is Next Nav
			# if (ii) we assume current=Feb and Jan is Prev Nav b/c ..
			# .. unusual for Next Nav to come before a Curr Month
			i = mth_lines[0]
			doclist[i] = cal_month_mark + doclist[i]
		
		elif len(cal_mths) > 2:
			# cases of three we assume middle mth is the month
			# if >3; take the first 3 months only

			# set to long months
			cal_mths = [G.short_long[c[:3]] for c in cal_mths]

			#position in doclist
			a, b, c = mth_lines[0], mth_lines[1], mth_lines[2]	

			#position in list of months
			id_a = long_mths.index(cal_mths[0])
			id_b = long_mths.index(cal_mths[1])
			id_c = long_mths.index(cal_mths[2])

			# take care of year ends Dec/Jan
			if id_b < id_a: id_b += 12
			if id_c < id_a: id_c += 12

			if id_c - id_b == 1 and id_b - id_a == 1:
				# case Dec Jan Feb then Current=Jan
				doclist[b] = cal_month_mark + doclist[b]

			elif abs(id_b - id_a) > 20:
				# case id_b is way below in doclist; assume curr=id_a
				doclist[a] = cal_month_mark + doclist[a]

			elif abs(id_c - id_b) > 20:
				# case id_c is way below in doclist; assume curr=id_b
				# here we assume id_a is Prev Nav and id_c = Next Nav
				doclist[b] = cal_month_mark + doclist[b]

			else:
				# take the middle month of the three
				x = statistics.median( [id_a, id_b, id_c] )
				y = ''
				if x == id_a: 
					x = mth_lines[0]					# index
					y = cal_month_mark + cal_mths[0]	# text to insert
				elif x == id_b: 
					x = mth_lines[1]
					y = cal_month_mark + cal_mths[1]
				elif x == id_c: 
					x = mth_lines[2]
					y = cal_month_mark + cal_mths[2]
				doclist[x] = y

	return doclist


def trim_calendar(doclist,**kwargs):
	''' remove lines in prior or following month calendars '''
	
	if not kwargs['is_calendar']: return doclist

	# sometimes we have a giant table containing smaller month tables
	# eg tests Calendar2; here the diff month claendars are all together
	# we don't want to trim this calendar
	# we know this exists as we'll have 2 or more CAL MTH: markers
	count_cal_marks = 0
	for d in doclist:
		if G.cal_month_mark in d:
			count_cal_marks += 1
			if count_cal_marks > 1:
				return doclist

	# strip days of week that might interfere with dig search
	doclist = [strip_dow(t) for t in doclist]

	# find line with lowest number
	# this will be the first date in the calendar that has an event
	low_date = 22
	max_date = 31
	first_date = None
	for t in doclist:
		try:
			dig = int(t)
			if not first_date:				# check only if nothing yet
				if dig >= low_date:			# numbers from 22nd to 31st
					if dig < max_date:		# eg 24th of prior month
						max_date = digit	# set as max	

				elif dig > 0:				# now when 7th of new month
					first_date = dig
					break					# set as first evt date of cal
		except:
			pass

	# now reconstitute calendar skipping prior and following months
	if first_date:

		first_done = False
		tmp, doclist = setup_for_loop(doclist)
		for t in tmp:
			
			if not doclist or is_img_link(t):
				doclist.append(t)

			elif not first_done and not t.isnumeric():
				# capture pre calendar stuff eg headers
				# this will also get prior month event text
				# but not the date so event will not be picked up later
				doclist.append(t)
			
			else:
				try:
					# if numeric - assumptions: date
					# loop through numbers ( assume: prior month) until
					# we get to first date for this mth then set flag
					# if subsequent numbers > first date: should be rest of mth
					# if < first date: should be following month
					dig = int(t)
					if not first_done:
						if dig == first_date:
							doclist.append(t)
							first_done = True
						else:
						 	continue 		# prior month

					elif dig > first_date:
						doclist.append(t) 	# other dates this month

				except:
					# with calendars we have a strict date/int \n event text
					# if item above is not a number
					# then we've reached the end of the calendar
					if doclist[-1].isnumeric():
						doclist.append(t)

	return doclist


def affix_calendar_month(doclist,**kwargs):
	''' add calendar month and year to dig dates '''

	if not kwargs['is_calendar']:
		return doclist

	cal_mth, cal_yr = None, None

	marks = ['events in','events for']
	
	cal_month_mark = G.cal_month_mark

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if cal_month_mark in t:
			cal_mth, cal_yr = get_mth(t, get_year=True)
		
		if not doclist or is_img_link(t):
			doclist.append(t)
		else:
			affix = False
			# catch dates of types: '7' , 'Wed 7'
			if t.isnumeric() or \
				strip_dow(t).isnumeric():
				if cal_mth: t += ' ' + cal_mth
				if cal_yr: t += ' ' + cal_yr

			doclist.append(t)
	return doclist


def fix_mth_head_for_orphan_digits(doclist):
	''' quick concat of mth/head/yr types '''
	
	# so if true mth head we'll get many orphan_dates and few mths

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist or is_img_link(t):
			doclist.append(t)

		elif t.lower() in G.all_months:
			try:
				i = int(doclist[-1])
				if 1 <= i <= 31:  # case 7 /n November
					doclist[-1] = doclist[-1] + ' ' + t
				else:
					doclist.append(t)
			except:
				doclist.append(t)

		elif any(re.search(r''+m+r'\s\d{4}$',t,flags=re.I) for m in G.all_months):
			try:
				i = int(doclist[-1])
				if 1 <= i <= 31:  # case 7 /n November 2018
					doclist[-1] = doclist[-1] + ' ' + t
				else:
					doclist.append(t)
			except:
				doclist.append(t)

		else:
			doclist.append(t)

	return doclist


def convert_slash_dates(doclist, ven_ref):
	''' convert '/' dates; need the three elements d m y: uk style '''

	separators = G.date_separators
	us_date_countries = G.us_date_countries
	if not ven_ref: ven_ref = 'REF-GB'

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		done = False

		if t is None or t.strip() == '':
			continue

		if not doclist or is_img_link(t) or not possible_date(t):
			doclist.append(t)
			continue

		else: # possible dates

			# times can interfere so 
			# we'll work with stripped time text
			# case: 11.30pm 02/09
			tme = get_time(t)
			t_ = strip_time(t)

			if not any(re.search(r''+sep,t_) for sep in separators):
				doclist.append(t)
				continue

			# rest below is where at least one sep in text
			for sep in separators:

				non_regex_sep = None

				if sep == '\.':
					non_regex_sep = '.' # nb as can't use \. in string methods
				
				if sep == '\s' and sep in t_: # no need to do space seps
					doclist.append(t)
					break

				elif not re.search(r''+sep, t_):
					continue

				elif any(
					re.search(r'\b'+mth+r'\b', t_) for mth in G.all_months):
					doclist.append(t)

				else:

					# case: 12/11/2018					
					finds = \
					re.findall(r'(\d{1,2}'+sep+r'\d{1,2}'+sep+r'\d{4})',t_)

					if finds:
						for find in finds:

							if non_regex_sep:
								f = find.split(non_regex_sep)
							else:
								f = find.split(sep)

							if len(f) != 3:
								# then not really date with sep
								continue

							# if us-country then reformat to uk style
							if ven_ref[-2:] in us_date_countries:
								f = str(f[1])+' '+str(f[0])+' '+str(f[2])
								f_ = replace_digit_with_txt(f.strip())

							else:
								f_ = ' '.join(f)
								f_ = replace_digit_with_txt(f_.strip())

							t_ = t_.replace(find, f_)
							
						if tme: t = t_ + ' ' + tme
						else: t = t_

						doclist.append(t)
						done = True
						break

					else:
						# case: 2018/12/9
						finds = \
						re.findall(r'(\d{4}'+sep+r'\d{1,2}'+
											sep+r'\d{1,2})(?!\d{2})',t_)

						if finds: 
							for f in finds:
								if non_regex_sep: 
									# so can split on '.' not '\.'
									f_ = f.split(non_regex_sep)
								else:
									f_ = f.split(sep)

								if len(f_) != 3:
									# then not really date with sep
									continue

								f_ = f_[2] + ' ' + f_[1] + ' ' + f_[0]
								f_ = replace_digit_with_txt(f_.strip())
								t_ = t_.replace(f, f_)
								
							if tme: t = t_ + ' ' + tme
							else: t = t_
							doclist.append(t)
							done = True
							break

						else:

							# case 9/12/19
							finds = \
							re.findall(r'(\d{1,2}'+sep+r'\d{1,2}'+
										sep+r'\d{2})(?!\d{2})',t_)

							if finds:
								for f in finds:
									if non_regex_sep:
										f_ = f.split(non_regex_sep)
									else:
										f_ = f.split(sep)

									if len(f_) != 3:
										# then not really date with sep
										continue
									
									# convert us-style
									if ven_ref[-2:] in us_date_countries:
										f_ = f_[1]+' '+ \
										f_[0] +' '+ '20'+f_[2]
									
									else:
										f_ = str(f_[0])+' '+ \
										str(f_[1]) +' '+ '20'+str(f_[2])
									
									f_ = replace_digit_with_txt(f_.strip())
									t_ = t.replace(f, f_)
								
								if tme: t = t_ + ' ' + tme 
								else: t = t_
								doclist.append(t)
								done = True
								break
							
							else:
								# case 23/12
								finds = \
								re.findall(
									r'(\d{1,2}'+sep+r'\d{1,2})\s*(?!\d)',t_)
								
								if finds:
									for f in finds:

										if non_regex_sep:
											f_ = f.split(non_regex_sep)
										else:
											f_ = f.split(sep)

										if len(f_) != 2:
											# then not really date with sep
											continue

										# convert us-style
										if ven_ref[-2:] in us_date_countries:
											f_ = str(f_[1]) + ' ' + str(f_[0])
											f_ = \
											replace_digit_with_txt(f_.strip())

										else:
											f_ = str(f_[0])+' '+str(f_[1])
											f_ = \
											replace_digit_with_txt(f_.strip())
											
										t_ = t_.replace(f, f_)
										
									# add back time info
									if tme: t = t_ + ' ' + tme
									else: t = t_

									doclist.append(t)
									done = True
									break

			if not done and t != doclist[-1]:
				doclist.append(t)

	return doclist


def convert_dash_text_dates(doclist):
	''' replace dash in text dates with spaces '''

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		if not doclist or is_img_link(t):
			doclist.append(t)

		else:
			finds = re.findall(r'(\d{1,2}-[a-zA-Z]{3,9}-\d{2,4})',t)
			if finds:
				for f in finds:
					f_ = re.sub('-',' ',f)
					t = re.sub(f, f_, t)

			doclist.append(t)

	return doclist


def join_pos_links(doclist):
	''' join lines with indicative split lines link at start or end of line '''

	pos_links = G.pos_links
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		if not doclist or is_img_link(t):
			doclist.append(t)

		elif possible_date(doclist[-1]) and is_descr(t):
			doclist.append(t)

		elif not possible_date(doclist[-1]) and get_time(t):
			doclist.append(t)

		else:
			if t.lower() in pos_links:
				# only join if no possible link in prior line
				# else skip
				if t.lower() not in doclist[-1]:
					doclist[-1] += ' ' + t
					doclist[-1] = remove_spaces(doclist[-1])

			elif any(doclist[-1].endswith(l) for l in pos_links):
				doclist[-1] += ' ' + t
				doclist[-1] = remove_spaces(doclist[-1])

			elif any(t.startswith(l) for l in pos_links):
				doclist[-1] += ' '  + t
				doclist[-1] = remove_spaces(doclist[-1])

			else:
				doclist.append(t)

	return doclist


def fix_empty_from_to(doclist):
	''' fix where 'from' but no 'to' and 'until' but no 'from' '''

	ends = G.end_markers
	starts = G.start_markers

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t) or not possible_date(t): 
			doclist.append(t)

		else:
			t = t.lower()

			# where 'from' but no 'until' or 'to'
			# usually exhibitions: for now set as single date	
			if any(s in t for s in starts) and \
				not any(e in t for e in ends):
				for s in starts:
					if s in t.lower():
						t = re.sub(s,'',t,flags=re.I)
						t = t.strip()
						doclist.append(t)
						break

			# deal where 'until': if no already first_date then
			# insert today's date as first date
			elif any(e in t.lower() for e in ends):
				t_ = t.lower()
				until_true = False
				for e in ends:
					if e in t_ and not until_true:

						# check txt before 'until' is not date
						# AND txt after 'until' has a date
						# case: Blah until <date> ...
						# not: <date> until <8pm | 'cows come home'>
						t_ = t_.split(e)

						if not possible_date(t_[0]) and \
								possible_date(t_[1]):	

							# insert today's date as <from>
							# and replace 'until' with '-' 
							# so convert_text_date() does not fail
							t = t_[0] + ' ' + \
							G.today.strftime('%d %b %Y') + ' - ' + t_[1]
							t = t.strip()

							doclist.append(t)
							until_true = True

						elif possible_date(t_[0]) and \
							possible_date(t_[1]):
							t = t_[0] + ' - ' + t_[1]
							doclist.append(t)
							until_true = True

				if not until_true:
					doclist.append(t)

			else:
				doclist.append(t)

	return doclist


def insert_every_day(doclist):
	''' deal with cases 'Every Thursday' and 'Wednesdays' '''

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		
		if not doclist or is_img_link(t): 
			doclist.append(t)

		elif t.lower() in G.all_days:
			continue

		else:

			ev = ''
			
			for d in G.long_days:

				if t in d or t in ['weekends']:
					continue # eg if line == 'thursdays'

				# we use 'weekends' and not 'weekend' as latter
				# will probably refer to a specific weekend date
				# while former potentially weekends from now-ish
				patterns = [r'(every.*'+d+r')(?!s).*', 
							r'.*('+d+r's).*', 
							r'.*?'+'(weekends)'+r'.*']
				for patt in patterns:
					finds = re.findall(patt, t, flags=re.I)
					if finds:				
						for f in finds:
							f = re.sub('every', '', t, flags=re.I)
							f = re.sub(' on ', '', f, flags=re.I)
							f = f.strip()

							if f not in ev:
								ev += f + ','
						ev = ev.strip(',')

			if ev != '':

				t = strip_chars(t)

				if possible_date(t):
					to_ev = G.reg_marker + ev + G.reg_mark_end + ' ' + t
				
				else:
					to_ev = G.reg_marker + ev + ': ' + \
							G.today_str + ' - ' + G.horizon_str + \
							G.reg_mark_end + ' ' + t

				doclist.append(to_ev)
				continue

			else:
				doclist.append(t)

	return doclist


def remove_start_markers(doclist):
	''' skip start markers '''
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist or is_img_link(t): 
			doclist.append(t)
		elif t in G.start_markers: 
			continue
		else:
			doclist.append(t)
	return doclist


def fix_end_markers(doclist):
	''' add 'end:' date marker to previous line '''

	ends = G.end_markers

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t): 
			doclist.append(t)

		elif not re.search(r'\D',t):
			# add lines with only numbers
			doclist.append(t)

		elif any(e in t for e in ends):

			if possible_date(doclist[-1]):
			
				if t in ends:
					# if on own line: add '-' to previous line
					# to be caught later by join_pos_links()
					doclist[-1] += ' -'
					continue

				elif any(t.startswith(e) for e in ends):
					#case: 'ends 23 June 2019'
					for e in ends:
						if t.startswith(e):
							t = t.replace(e, '')
							t = t.strip()
							doclist[-1] += ' - ' + t
							break

			else:
				doclist.append(t)

		else:
			doclist.append(t)

	return doclist


def reformat_yy_to_yyyy(doclist):
	''' change all yy types to yyyy '''

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if is_img_link(t) or \
			is_descr(t) or \
			not possible_date(t):
			pass
		else:	
			# strip time that might get in the way
			# case 9 Feb 11:00pm
			tme = get_time(t)
			t_ = strip_time(t)

			finds = re.findall(r'\d{1,2}\s+[a-zA-Z]+\s+\d{2}(?!\d+)', t_)
			if finds:
				for find in finds:
					f = find.split()
					if f[1] in G.all_months:
						f_ = f[0] + ' ' + f[1] + ' ' + '20'+ f[2]
						t_ = t_.replace(find, f_) 
					
			if tme: t = t_ + ' ' + tme 
			else: t = t_
		
		doclist.append(t)
	return doclist


def concat_mth_head(doclist,**kwargs):
	''' get mth heads and concat to dates '''

	is_calendar = kwargs['is_calendar']

	reg_marker = G.reg_marker
	mth_head, year_head = None, None

	is_mth_head = is_month_head_type(doclist)

	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:

		if not doclist or is_img_link(t) or reg_marker in t:
			doclist.append(t)

		elif t == doclist[-1]: continue #don't concat same thing

		elif any(re.search(r'\b^'+m+r'\b', t, flags=re.I) for 
					m in G.all_months) or \
			any(re.search(r'\b^'+m+r'\b\s\d{4}', t, flags=re.I) for 
					m in G.all_months) or \
			any(re.search(r'\d{1,2}\s'+m, t, flags=re.I) for 
					m in G.all_months): 

			# if not calendar (as we have the month already)
			# set mth/yr heads at first occurrence
			# ensures no chance of a prev mth being used
			if not is_calendar and not \
				any(re.search(r'\d{1,2}\s'+m, t, flags=re.I) for 
					m in G.all_months):

				if is_mth_head:
					mth_head, year_head = get_mth(t, get_year=True)

			try:
				# check if number on previous line: date or year

				int_ = int(doclist[-1])

				if 1 <= int_ <= 31:
					# case: 9 \n June
					doclist[-1] = doclist[-1] + ' ' + t
					continue

				else:
					doclist.append(t)

			except:
				# there could be a number + text on previous line eg Fri 14 

				if re.search(r'(?<!\d)\d{1,2}$',doclist[-1]) and \
					not get_time(doclist[-1]) and \
					not get_mth(doclist[-1]): 
					# cases: Fri/Blah 14 \n Aug 2018; Starts: 18 \n Aug 2018
					doclist[-1] = doclist[-1] + ' ' + t
					continue


				elif any(re.search(r''+dash+r'\s\d{1,2}$',doclist[-1]) for 
						dash in G.dashes): 
					# cases: 1 feb - 6 \n mar
					doclist[-1] = doclist[-1] + ' ' + t
					continue					

				elif get_mth(doclist[-1]) and \
					re.search(r'\s\d{1,2}$',doclist[-1]) and \
					(any(re.search(r'\b'+l+r'\b',doclist[-1]) 
						for l in G.pos_links)): 
					# case: 14 Jun - 15 \n Jun
					doclist[-1] += ' ' + t
					continue

				elif possible_date(doclist[-1]) and \
						(doclist[-1] in t or t in doclist[-1]):
						# case: Sep 24 \n Sept 24, 2018
						# e.g. date for event shown twice; keep longer one
						if len(t) > len(doclist[-1]):
							doclist[-1] = t
						continue

				elif possible_date(t):
					# we have a date so keep
					doclist.append(t)

				else:
					# we don't want to miss descr or titles that may
					# start with month names but ...
					# leave any current mth head
					if mth_head:
						pass
					else:
						doclist.append(t)

					
		elif re.search(r'^\d+$',t):

			dig = re.search(r'(\d+)$',t).group(1)
			
			if len(t) <= 2 and mth_head:
				# if digit and mth_head then concat; else add to doclist
				if 1 <= int(dig) <= 31:
					t = t + ' ' + mth_head
				doclist.append(t)

			elif len(t) <= 2 and \
				any(doclist[-1]==mth for mth in G.all_months):
				# case mth \n dd
				if 1 <= int(dig) <= 31:
					doclist[-1] = t + ' ' + doclist[-1]
				doclist.append(t)

			elif len(t) == 4 and t[:2] == '20' and possible_date(doclist[-1]):
				#catch years on their own but attached to a date
				doclist[-1] += ' ' + t

			else: #anything else just add to doclist
				doclist.append(t)
				
		elif mth_head:

			finds = None

			if get_time(t):
				finds = re.search(r'^(\d+)(?!\d*[\:|\.|am|pm])(.*)$',t)
			else:
				# types <date> separator <event name>
				# cases: 10 Boogie Class; 11 - Jive Class; 13: Miles Davis Trio
				date_title_seps = ['\s', '-', ':']
				for sep in date_title_seps:
					finds = re.search(r'^(\d+)\s*'+sep+r'\s*(.*)$',t)
					if finds:
						break
				
			if finds:
				a = finds.group(1)
				b = finds.group(2)

				if 1 <= int(a) <= 31:
					if year_head:
						t = a + ' ' + mth_head + ' ' + year_head + ' ' + b
					else:
						t = a + ' ' + mth_head + ' ' + b
					t = remove_spaces(t)

				doclist.append(t)


			# try for type Wed 7; unlikely to be 7 Wed
			elif any(dow in t for dow in G.all_days):
				dow_found = False
				for day in G.all_days:
					finds = \
						re.search(r'('+day+r',*\s*\d{1,2})(?!\d)(.*)$',t)
					if finds:
						t = finds.group(1) + \
							' ' + mth_head + \
							' ' + finds.group(2)
						doclist.append(t)
						dow_found = True
						break

				if not dow_found:
					doclist.append(t)		

			else:
				doclist.append(t)

		else:
			doclist.append(t)

	return doclist


def remove_orphan_digits(doclist):
	''' clean up orphan digits/numbers '''
	tmp, doclist = setup_for_loop(doclist)
	for t in tmp:
		if not doclist:
			doclist.append(t)
		else:
			try:
				int(t)
			except:
				doclist.append(t)
	return doclist


def standardise_dashes(txt):
	''' standardise dashes '''
	if any(dash in txt for dash in G.dashes):
		for dash in G.dashes:
			if dash != '-':
				txt = txt.replace(dash,'-')
	return txt


def standardise_date_joins(docline):
	''' standardise from_ to_ seperators '''
	if possible_date(docline):
		for l in G.pos_links:
			if l in docline and re.search(r'\d+',docline):
				if l in G.dashes: continue
		
				if l[-1]== ' ':
					docline = re.sub(r'('+l+r')', ' - ', docline)
				else: # \W to excl october
					docline = re.sub(r'('+l+r'\W)', ' - ', docline)	
				if l in  G.pos_links_specials:  # e.g. »
					docline = docline.replace(l,' - ')	

				break
	docline = remove_spaces(docline)
	return docline


def concat_dates(doclist,trav_up=None,ven_ref=None,**kwargs):
	''' concatenate date fragmented over several lines '''

	#for d in range(len(doclist)): print(d,doclist[d])

	# strip currencies that might interfere
	doclist = [strip_currencies(line) for line in doclist]

	# skip days of week on their own
	doclist = [d for d in doclist if d.lower() not in G.all_days]

	# quick concat of mth/head/yr types so if true mth head
	# we'll get many orphan_dates and few mths
	doclist = fix_mth_head_for_orphan_digits(doclist)

	#for d in range(len(doclist)): print(d,doclist[d])


	# convert slash dates: 23/10/2019 ng. all digits
	doclist = convert_slash_dates(doclist, ven_ref)

	#for d in range(len(doclist)): print(d,doclist[d])


	# convert dash text dates: 23-march-2023
	doclist = convert_dash_text_dates(doclist)

	#for d in range(len(doclist)): print(d,doclist[d])

	# add marker for 'every' eg Thurs 
	doclist = insert_every_day(doclist)


	#for d in range(len(doclist)): print(d,doclist[d])



	# remove 'starts' on own line
	doclist = remove_start_markers(doclist)

	# fix so 'ends date' on same line as prior line from date
	doclist = fix_end_markers(doclist)

	# add default start date of today if none but there's to date 
	doclist = fix_empty_from_to(doclist)

	#for d in range(len(doclist)): print(d,doclist[d])

	# concat succeeding lines where likely split and indicative link exists 
	doclist = join_pos_links(doclist)

	#for d in range(len(doclist)): print(d,doclist[d])


	# reformat yy to yyyy; imp before concat_mth_head
	# as would be caught there by an inappropriate block
	doclist = reformat_yy_to_yyyy(doclist)

	#for d in range(len(doclist)): print(d,doclist[d])

	# add month names and year heads to date digits
	doclist = concat_mth_head(doclist,**kwargs)

	#for d in range(len(doclist)): print(d,doclist[d])


	doclist = remove_orphan_digits(doclist)

	# set the 'to/until' in <from date< to/until <to Date> to ' - '
	doclist = [standardise_date_joins(d) for d in doclist]

	#for d in range(len(doclist)): print(d,doclist[d])

	# should be no single char lines by now
	doclist = [d.strip() for d in doclist if len(d.strip()) > 1]

	#for d in range(len(doclist)): print(d,doclist[d])

	return doclist


def concat_times(doclist, **kwargs):
	''' concatenate time with date esp times over several lines '''

	trav_up = kwargs['trav_up']
	is_calendar = kwargs['is_calendar']

	last_date, last_date_index, last_date_has_time = None, None, False

	tmp, doclist = setup_for_loop(doclist)
	for i in range(len(tmp)):

		t = tmp[i]

		# check for time
		time = get_time(t)

		# check date
		pos_date = possible_date(t)
		
		if not doclist or is_img_link(t) or \
			(not pos_date and not time):
			doclist.append(t)

		else:
			# record dates to allow later possible time appends
			if pos_date:
				doclist.append(t) # add now so index below is correct
				last_date = t
				last_date_index = len(doclist) - 1 # b/c zero base
				if time:
					last_date_has_time = True 
				else:
					last_date_has_time = False # reset 

			if time and not is_descr(t):

				if not last_date:
					# continue if no date to attach to
					# case: <Time \n Date \n Event Details> <next evt>
					doclist.append(t)
					continue

				else:
					if pos_date:
						# we already have a date on same line with this time
						# but we added this above already so skip
						continue

					elif last_date_has_time or is_calendar:
						# no date on same line and last_date already has time
						# assume t = same date, diff event & time
						# but only if time is within distance of date
						span = 6
						if i - last_date_index <= span:
							date = strip_time(last_date)
							t = date + ' ' + t
							
							# reset last_date_index here as could have
							# long list of times for same date such that
							# later dates fall outside original index
							last_date_index = i

						doclist.append(t)

					elif not last_date_has_time:
						# last_date has no time yet; append this time
						doclist[last_date_index] = \
						doclist[last_date_index] + ' ' + t
						last_date_has_time = True
						last_date_index = i # reset

	return doclist


def remove_repeat_dates(doclist,**kwargs):
	''' remove repeated dates for same event '''

	# do this post concat_times: so for close genuine 2 evts, same day
	# if time given then increases chance of date & time being on same line
	# and thus serving as 2 different dict keys

	# things to note:
	# 1. dates must be spelt the same: so oct 19 != october 19
	# ^^ this is a flaw; b/c some sites have this format for same event
	# 2. will delete 1st date of 2 genuine diff evts
	# >> Salsa 1 Oct, Cha Cha 1 Oct where no time is shown which would have
	# served as to make a unique dict key << this is a flaw

	#where <date> <event details> <date repeated>: remove first date
	date_count, dates, to_del = 0, {}, []
	span, threshold = 6, 6
	for i in range(len(doclist)):
		item = doclist[i]
		if possible_date(item): # nb. we don't check for time
			date_count += 1
			if item not in dates.keys():
				dates[item] = i
			else:
				if abs(dates[item] - i) < span:
					# close enough to look like a repeat
					to_del.append(dates[item])
	
	# delete only if many to_dels to avoid a few same date, diff times events
	# if it's the case event repeats then virtually all events will be affected
	# thus to_del should roughly be about half of all dates
	# we'll have a tolerance around the half target for rogue pos_dates
	tolerance = 0.2
	target = math.floor(0.5 * date_count)
	if target * (1 - tolerance) <= len(to_del) <= target * (1 + tolerance):
		while to_del:
			del doclist[max(to_del)]
			to_del.remove(max(to_del))

	return doclist


def base_venue_url(url):
	''' retrieve base url excl the /<specific page> '''
	base_url = None
	o = urllib.parse.urlparse(url)
	if o.scheme: base_url = o.scheme+'://'+o.netloc
	return base_url


def long_mth(date):
	''' replace short dates eg Jan with long form 
		dates passed should be uk-style d m y
	'''	
	date = replace_digit_with_txt(date)
	mth = get_mth(date) # result is None if mth  
	if mth is None: pass
	elif mth in G.long_mths: pass
	else:
		short_form = mth[:3]
		long_form = G.mths_dict[short_form][1]
		date = date.replace(mth,long_form)
	return date


def reshape(obj):
	''' make date = day month year format 
		we assume digits at end either day or day year
		dates passed in should be space separated
	'''

	if obj is None or \
		obj == '' or \
		isinstance(obj,int): return obj

	is_str = False
	if isinstance(obj,str):
		obj = [obj, '']	# so we can work with lists
		is_str = True	# so we can later restore as string

	for i in range(len(obj)):
		if ' ' in obj[i].strip(): #don't split eg 21.11.2016
			t = obj[i]
			t = remove_spaces(t)
			if re.search(r'^\D+\d{1,2}$',t): #Nov 15
				t = t.split()	
				if len(t) == 2: 
					obj[i] = t[1]+' '+t[0]
			elif re.search(r'^\D+\s+\d{1,2},*\s+\d{4}$',t): # Nov 15 2014
				t = re.sub(',','',t)
				t = t.split()
				if len(t) == 3: 
					obj[i] = t[1]+' '+t[0]+' '+t[2]
			elif re.search(r'^\d{4},*\s+\D+\s+\d{1,2}$',t): # 2019, Nov 15
				t = re.sub(',','',t)
				t = t.split()
				if len(t) == 3: 
					obj[i] = t[2]+' '+t[1]+' '+t[0]
			elif re.search(r'^\D+\s+\d{4},*\s+\d{1,2}$',t): 
				# Nov 2019, 13 << b/c we've removed the 'th' from 13th
				t = re.sub(',','',t)
				t = t.split()
				if len(t) == 3: 
					obj[i] = t[2]+' '+t[0]+' '+t[1]

	if is_str: obj = obj[0]
	return obj


def get_full_dates(txt):
	''' determine full date complement of date month year '''
	
	this_yr, last_yr, next_yr = G.this_yr, G.last_yr, G.next_yr
	links = G.pos_links

	# if not a possible date then exit
	if not possible_date(txt): return [None, None]

	# strip stuff
	txt = strip_chars(txt)

	# if 'from_date -|to|&|: to_date' format; get both dates
	# if date items > 2 then return None as possibly not dates afterall 
	for l in links:
		splitter = l
		if l == 'to':
			splitter = ' ' + l + ' ' # ' ' so not 'to' in october
		if splitter in txt: 
			txt = txt.split(splitter)
			if len(txt) > 2:
				return [None, None]
			else:
				break

	# if we still have a string then assume only <from> date
	# set <to> equal to <from>
	if isinstance(txt, str): txt = [txt, txt]

	txt = [t.strip() for t in txt]
	
	# get months and fix non-existing ones
	from_mth, from_yr = get_mth(txt[0], get_year=True)
	to_mth, to_yr = get_mth(txt[1], get_year=True)

	# if no month, return txt
	if from_mth is None and to_mth is None:
		return [None, None]

	# if all mths, years there then we are all good
	if from_mth is not None and \
		from_yr is not None and \
		to_mth is not None and \
		to_yr is not None:
		txt = [reshape(t) for t in txt]
		txt = [long_mth(t) for t in txt]
		return txt

	# deal with from/to params
	# probably malformed str: case 9 Aug - 17
	# and could be: Aug 9 - 17
	# assume to == from
	if from_mth is not None and to_mth is None:
		if re.search(r'^'+from_mth, txt[0]) or \
			re.search(r'^\d{1,2}\s+'+from_mth, txt[0]):
			to_mth = from_mth
			txt[1] += ' ' + to_mth
		else:
			return [None, None]

	# if no from_mth: set = to_mth
	# case: 3 - 9 Aug
	# if to_yr then add it to from_	
	if from_mth is None and to_mth is not None:
		from_mth = to_mth
		txt[0] += ' ' + from_mth
		if to_yr:
			txt[0] += ' ' + to_yr
			txt = [reshape(t) for t in txt]
			txt = [long_mth(t) for t in txt]
			return txt

	# if nothing then return None
	if from_mth is None and \
		from_yr is None:
		return [None, None]

	# now we have months; time to fix years
	# more complex as may have to go across years
	
	# to determine if to use prior yr or next year
	# we need to know the order of months: jan=1 ...
	mths_dict = G.mths_dict
	fr_mth_index = mths_dict[from_mth[:3]][0]
	to_mth_index = mths_dict[to_mth[:3]][0]
	cur_mth_index = G.today.month

	# cases: 4 Jun - 15 Aug 2019; 4 Nov - 15 Aug 2019
	# if <from> mth <= <to> use to_yr; else use prior_yr
	if from_yr is None and to_yr is not None:
		if fr_mth_index <= to_mth_index:	# from:Jun ; to:Aug
			from_yr = to_yr
		else:								# from:Nov ; to:Aug
			from_yr = str(int(to_yr) - 1)
		txt[0] += ' ' + from_yr
		txt = [reshape(t) for t in txt]
		txt = [long_mth(t) for t in txt]
		return txt

	# cases: 5 Jun 2020 - 9 Sep; 5 Jun 2020 - 3 Mar; 
	# if <from> mth <= <to> use from_yr; else use next_yr
	if from_yr is not None and to_yr is None:
		if fr_mth_index <= to_mth_index:	# from:Jun ; to:Sep
			to_yr = from_yr
		else:								# from:Jun ; from:Mar
			to_yr = str(int(from_yr) + 1)
		txt[1] += ' ' + to_yr
		txt = [reshape(t) for t in txt]
		txt = [long_mth(t) for t in txt]
		return txt

	# if no years then all depends on where in year we are
	# eg curMth Feb: is Aug - Jun event (a) last_yr-this_yr (b) this_yr-next_yr
	# eg curMth Sep: is Jan - Mar event (a) this_yr-this_yr (b) next_yr-next_yr
	# rather than be too clever or complex, assume:
	# 1. if curMth <= <from_mth> : event starts this year
	# 2. if from_ < curMth < to_ : event is this year
	# 3. if curMth >= to_mth and curMth > threshold: event starts next year
	# 4. if curMth >= to_mth and curMth <= threshold: event starts this year
	threshold = 9 # arbitrary choice of September
	if from_yr is None and to_yr is None:

		# case 1: curMth <= from_ : event starts this year
		if cur_mth_index <= fr_mth_index:	# cur:Mar ; from:Sep
			from_yr = str(this_yr)
			txt[0] += ' ' + from_yr
			if to_mth_index < fr_mth_index: # from:Sep ; to:Jan
				to_yr = str(next_yr)
			else:							# from:Sep ; to:Oct
				to_yr = str(this_yr)
			txt[1] += ' ' + to_yr
			txt = [reshape(t) for t in txt]
			txt = [long_mth(t) for t in txt]
			return txt

		# case 2: from_ < curMth < to_ : event is this year
		if fr_mth_index < cur_mth_index < to_mth_index:
			from_yr = to_yr = str(this_yr)
			txt[0] += ' ' + from_yr
			txt[1] += ' ' + to_yr
			txt = [reshape(t) for t in txt]
			txt = [long_mth(t) for t in txt]
			return txt

		# case 3 and 4 : curMth >= to_ ; consider threshold
		if cur_mth_index >= to_mth_index:
			# note also that here curMth > from_

			# case 3: curMth > thresh: event ends next year
			# we assume as it's late in year, venue/org has put up info
			# for next year: 
			# cur:Nov ; thresh:Sep
			if cur_mth_index > threshold:
				
				if fr_mth_index <= to_mth_index:	# from:Feb ; to:Jun
					from_yr = to_yr = str(next_yr)
				else:								# from:Dec ; to:Jun
					from_yr = str(this_yr)
					to_yr = str(next_yr)
				txt[0] += ' ' + from_yr
				txt[1] += ' ' + to_yr

			else:
				# case 4: curMth <= thresh: event starts this year
				# we are still early-ish in the year 
				# cur:Feb ; thresh:Sep
				if fr_mth_index <= to_mth_index:	# from:Feb ; to:Jun
					from_yr = to_yr = str(this_yr)
				else:								# from:Dec ; to:Jun
					from_yr = str(this_yr)
					to_yr = str(next_yr)
				txt[0] += ' ' + from_yr
				txt[1] += ' ' + to_yr
			
			txt = [reshape(t) for t in txt]
			txt = [long_mth(t) for t in txt]
			return txt

	return txt


def has_text(txt):
	''' something with just numbers is unlikely to be a title 
		currently only used for title tests
		review if to be used for descr test 
	'''

	has_ = False
	has_dig = False
	min_len = 3

	# abort if invalid txt
	if not isinstance(txt, str) or \
		len(txt.strip()) == 0:
		return has_

	# strip all digits and special chars
	# if re.search(r'\d',txt):
	txt = remove_punctuation(txt,rm_dig=True)

	# remove month names and DoW
	txt = strip_dow(txt, just_from_dates=False, months=True)

	# remove common joining words
	for c in G.conjunctions:
		txt = re.sub(r'\b'+c+r'\b','',txt,flags=re.I)

	# remove ignore_title to avoid things like 'and is free title' passing
	for c in G.ignore_title:
		txt = re.sub(r'\b'+c+r'\b','',txt,flags=re.I)

	txt = remove_spaces(txt)
	txt = strip_chars(txt)
	txt = txt.strip()
	
	if len(txt) >= min_len:
		has_ = True

	return has_


def get_image_link(img, seed_url):
	''' find lines with images '''

	#set params
	link = None
	base_url = base_venue_url(seed_url)
	pic_extensions = G.pic_extensions
	inval = ['pinterest', #eg need to log in to get pinterest
			'about-us','banner']  

	sources = ['src','srcset','style']
	for s in sources:
		try:
			link = img.get(s)
			if link: break
		except:
			continue

	if not link: return None

	elif not any(re.search(r'.*'+e+'.*',link, re.IGNORECASE) for 
												e in pic_extensions):
		return None

	elif any(i in link for i in inval): return None

	else:
		for e in pic_extensions:

			if link.find(e) != -1:

				if 'http' in link:
					#strip any stuff post file extension
					link = G.img_linker + \
						link[link.find('http'):link.find(e)] + e
					break
				
				elif '//' not in link: #case src='blah-blah.jpg'
					fwd = ''
					split_link = link[:link.find(e)]
					if base_url[-1] != '/' and split_link[0] != '/':
						fwd = '/' #case http://someurlimglink with no fwd
					link = G.img_linker + base_url + fwd + split_link + e
					break

				elif '//' in link: #case: img src='//blah-blah.jpg'
					link = G.img_linker + 'https' + \
						link[link.find('//'):link.find(e)] + e
					break

	return link


def is_calendar_title_like(text):
	''' indicative test if text looks like a title '''

	is_ = True

	# b/c of how ignore_doclist is being used in this func
	# check for event titles that have this
	ignore_cal = ['closed','cancelled','postponed']

	# these here must be before .lower()
	if text is None: return False
	if not isinstance(text, str): return False

	text = text.lower()
	puncts = G.puncts
	ignore_doclist = G.ignore_doclist

	max_len = 200	# enough to catch music events with multiple acts
	max_puncts = 2	# if too many, unlikely to be title
	max_dash = 1	# if more than this then likely a tag holdover

	#should not include any of these characters
	invals = ['{',]

	# strip time, dates and dow
	text = strip_time(text)
	text = strip_dow(text, just_from_dates=False)	# catches solitary dow
	text = strip_dates(text)

	# tests
	# nb not using in_ignore_doclist as that picks up if any ign in text
	# so will use it as if line == any in ignore_
	# reason: some calendar events eg music band names can have elems
	# in ignore_ ... may need to reconsider ignore_doclist itself
	if text in ignore_doclist or \
		text.lower() in G.all_months or \
		any(text.startswith(ign) for ign in ignore_doclist) or \
		any(ign in text for ign in ignore_cal) or \
		re.search(r'^\d+$', text) or \
		len(text.strip()) < 2 or \
		len(text) > max_len or \
		is_quote(text) or \
		len(re.findall(r'-', text)) > max_dash or \
		any(inv in text for inv in invals):
		is_ = False

	# test for puncts
	if is_:
		count_p = 0
		for p in puncts:
			has_punct = re.findall(r''+p, text)
			if has_punct:
				count_p += len(has_punct)
				if count_p > max_puncts:
					is_ = False
					break

	return is_


def create_line_breaks(string,**kwargs):
	''' create line breaks from string and return list '''

	#print(string)

	if string is None or \
		not isinstance(string,str):
		return []
	
	max_len = 9999
	doclist = string.splitlines()
	
	doclist = [d.strip() for d in doclist if 0 < len(d.strip()) < max_len]
	return doclist


def chuck_soup_nodes(souped, seed_url):
	''' remove or replace nodes in soup tree '''

	def replace_tag(img_link, img):
		''' replace img tag with text version '''
		p = souped.new_tag('p')
		p.string = img_link
		img.insert_after(p)
		# replace the img tag with the new contents
		img.unwrap()

	#remove scripts as can cause errors
	beg = time.time()
	scripts = souped.find_all('script')
	if scripts:
		for s in scripts:
			s.decompose()
	end = time.time()
	print('...... remove scripts: ',str(round(end-beg,1))+'s')

	#get_text discards img tags so here we reset img tags as text
	beg = time.time()
	for img in souped.select('img'):
		img_link = get_image_link(img, seed_url)
		if not img_link: 
			continue
		else: replace_tag(img_link, img)
	end = time.time()
	print('...... replace img tags with text: ',str(round(end-beg,1))+'s')

	for tag in ['div','span']:
		beg = time.time()

		#do same thing for background-styles
		styles = souped.find_all(tag,attrs={'style':True})
		for img in styles:
			img_link = get_image_link(img,seed_url)
			if not img_link: 
				continue
			else: replace_tag(img_link, img)

		#remove addresses
		addresses = souped.find_all(tag,attrs={'itemprop':'address'})
		if addresses:
			for addr in addresses:
				addr.decompose()

		end = time.time()
		print('...... remove itemprop addresses ('+tag+'):',
			str(round(end-beg,1))+'s')

	return souped


def attach_event_time(text):
	''' attach calendar event time to event '''

	# case: we have events listed in cells in form
	# 1. <td>evt_name \n time \n\n evt_name \n time</td>
	# 2. <td>time \n evt_name \n\n time \ evt_name</td>
	# attaching time on same line to evt_nam makes it easier
	# to parse later on for each event item

	time_rws = []							# to track where times are
	orig_text = text
	text_ = text.splitlines()				# b/c likely tme \n evt split
	text_ = [t for t in text_ if t != ''] 	# removes \n split as ''
	text = ''								# reset

	# get where times are
	for i in range(len(text_)):
		if get_time(text_[i].lower()):
			time_rws.append(i)
	
	# if nothing: return
	if not time_rws: return orig_text

	# add fake last row so can use [x:] to pick up final list items
	time_rws.append(999) #fake entry so to capture last item
	
	# associate times to event titles
	if time_rws[0] == 0:
		#case 2: [0, 2, 4, 999]
		for i in range(len(time_rws)-1):
			sliced = text_[time_rws[i]:time_rws[i+1]]
			attached = ' '.join(sliced)
			text += attached + '\n\n'

	else:
		# case 1: 1, 3, 5, 999]
		for i in range(len(time_rws)-1):
			sliced = text_[time_rws[i]-1:time_rws[i+1]-1]
			attached = ' '.join(sliced)
			text += attached + '\n\n'

	return text


def strip_img_link_from_text(text):
	''' strips image linke from a text eg background-img for table cell '''
	img_link = G.img_linker
	if isinstance(text, str):
		if img_link in text.lower():
			text = re.sub(r'('+img_link+r'.*?\.[a-z]{2,3})','',text)
	return text


def compile_cell_dates(table):
	''' associate calendar event with correct date and create tags '''

	bs_tags = []		# for BeautifulSoup tags
	tag_texts = []		# to hold mth_headers and paired date, event
	mth_header = None 	# to hold calendar month header if exists
	row_dates = []		# for dates in rows with dates
	row_events = []		# for text in rows with event titles + maybe times

	def pair_date_event_text(tag_texts,row_dates,row_events):
		''' pair date & event text and append to tag_texts '''
		zipped = zip(row_dates, row_events)
		if mth_header not in tag_texts:
			tag_texts.append(mth_header)
		for z in zipped:
			tag_texts.append(z[0])
			tag_texts.append(z[1])
		return tag_texts

	# loop through rows in tables
	for tr in table.find_all('tr'):

		row_type = None

		# if we have a full complement of dates and events
		# from previous 2 rows; then add mth_header and 
		# zipped (date, event) to tag_texts
		# note: works as long as there is at least one row more than table 
		if row_dates and row_events and \
			len(row_dates) == len(row_events):

			tag_texts = pair_date_event_text(tag_texts,row_dates, row_events)

			# reset for next set of rows
			row_dates = []
			row_events = []

	
		# else go hunting for data
		# fetch each cell in the row and 
		# add to row_dates or row_events as appropriate
	
		cells = tr.find_all('td')

		for cell in cells:

			text = cell.get_text().strip()

			# skip obvious
			if is_img_link(text): continue

			# nb. using .lower() as
			# we haven't set string/doclist to lowercase yet
			is_int = text.isnumeric()
			pos_date = possible_date(text.lower())
			title_like = is_calendar_title_like(text.lower())

			# first search for mth_header
			# if we find one then scoot to next row to hunt for dates, events
			if not title_like and \
				any(re.search(r'\b'+mth+r'\b',text.lower()) for 
				mth in G.all_months):

				mth, year = get_mth(text.lower(),get_year=True)
				if mth and year:
					mth_header = mth + ' ' + year
				else:
					mth_header = mth
				break

			# if no mth_header then skip on until we find one
			if not mth_header:
				continue

			# case: '3' or 'Wed 7'
			# if found then we are in a row for dates
			elif is_int or pos_date:
				row_dates.append(text)
				row_type = 'date'
				
			else:
				# for event titles we must not be in a date row
				# and must have dates collected already
				# attach times to events if necessary
				if row_type != 'date' and row_dates:
					if len(row_events) < len(row_dates):
						text = attach_event_time(text)
						row_events.append(text)

	# case where only one table and last row is last event text
	# here the pair_() hasn't been activated
	# do it now
	if row_dates and row_events and not tag_texts:
		tag_texts = pair_date_event_text(tag_texts,row_dates, row_events)			

	# if we have something then build bs tags
	if tag_texts:
		for tag_text in tag_texts:
			if tag_text:
				bs_tag = BeautifulSoup(tag_text,'lxml')
				bs_tags.append(bs_tag)

	return bs_tags


def compile_cell_text(table_cells):
	''' split dte + text in same cell into different tags '''

	bs_tags = []
	tag_texts = []
	evt_date_tags = []

	def cleanup(tag_text):
		tag_text = remove_erase_from(tag_text)
		tag_text = [strip_img_link_from_text(t) for t in tag_text]
		tag_text = [t for t in tag_text if t != '']
		return tag_text


	# collect all the contents of each tag
	for tag in table_cells:

		tag_text = []
		
		children = tag.children

		for child in children:

			# get_text or just the text for navigable strings
			text = None

			try:
				text = child.get_text().strip()

				# it's still possible to have mixed calendar types:
				# with empty days with cell_dates and event dates with text
				# so we test if we can split the text presuming
				# the date will be separated from event text details
				# we extract the date and reconstitute the remaining text 
				try:
					text_ = text.split('\n')
					#print(222,text_)
					for i in range(len(text_)):
						t = text_[i]

						x = t.isnumeric()
						y = possible_date(t)
						if x or y:
							# append the date
							tag_text.append(t)
							#print(240,t)
							
							# clean up the rest and append	
							t_ = text_[i+1:]
							t_ = [r.strip() for r in t_]
							t_ = [r for r in t_ if r]
							if t_:
								tag_text.extend(t_)
							break
						else:
							tag_text.append(text)
				except:
					tag_text.append(text)
		
			except:
				text = child.strip()
				tag_text.append(text)

		tag_text = [t.strip() for t in tag_text if t != '']
	
		tag_text = cleanup(tag_text)
		# check first tag_text not there as python 
		# by reference could have updated the list 
		if tag_text and tag_text != '':
			if tag_text not in tag_texts:
				tag_texts.append(tag_text)

	# if we have something then build bs tags
	if tag_texts:

		mth_header = None # to hold calendar month header if exists

		for tag_text in tag_texts:

			evt_title = ''
			evt_date = None

			for text in tag_text:

				if len(text) > 500: continue

				is_int = text.isnumeric()
				pos_date = possible_date(text)

				# for calendars we should have short dates by now
				if len(text) > 20: # in case type: thursday 22 september
					pos_date = False

				# we may have month head; we only set it once
				if can_be_mth_head(text): 
					mth_header = text

				elif mth_header and is_int or pos_date:
					evt_date = text

				elif is_calendar_title_like(text):
					if text not in evt_title:
						evt_title += text + ', '

				else:
					continue
										
			# collate bs_tags for found items
			if mth_header:
				mth_header_tag = BeautifulSoup(mth_header,'lxml')
				# we expect a mth_header to be listed only once
				if mth_header_tag not in bs_tags:
					bs_tags.append(mth_header_tag)

			if evt_date and evt_title != '':

				evt_date_tag = BeautifulSoup(evt_date,'lxml')
				evt_date_tags.append(evt_date_tag)
				bs_tags.append(evt_date_tag)
				
				evt_title = evt_title.strip()
				evt_title = strip_chars(evt_title)
				evt_title_tag = BeautifulSoup(evt_title,'lxml')
				bs_tags.append(evt_title_tag)

	# if no valid cal dates then return None
	if not evt_date_tags:
		return None

	return bs_tags


def extract_table_contents(table):
	''' get calendar data if exists '''

	# two main types of calendars
	# 1. dates in own rows, events below in own rows
	# 2. dates and events in same cell

	# need diff handling as in (1) must attach
	# correct event in one row to correct date in the row above

	# so we test what type of calendar we have
	# and compile events accordingly 

	dtes 	= ''
	bs_tags = None

	# check what type of calendar
	table_cells = table.find_all('td')
	for tag in table_cells:
		text = tag.get_text().strip()
		if text.isnumeric() or possible_date(text):
			dtes += '1'
		else: dtes += '0'

	# a row of 7 consecutive numerics/dates
	# suggests it's the first kind of calendar (cell_date)
	# but we need enough tds to make a calendar: 
	# at least 28 for February
	cell_date = True
	if '1111111' not in dtes:
		cell_date = False


	if len(dtes) >= 28:
		if cell_date:
			bs_tags = compile_cell_dates(table)
		else:
			bs_tags = compile_cell_text(table_cells)

	return bs_tags


def get_calendars_in_tables(souped):
	''' get data in tables and replace table with new tags 
		using calendar events '''

	found_valid_cal_data = [] # to check if we have cal dates
	
	tables = souped.find_all('table')

	if tables:
				
		for table in tables:

			# check table has data to skip empty tables
			# or nav cal tables with basic data like numeric dates of month
			# note that this will miss genuine cal with very few event entries
			min_table_text = 100
			table_has_data = False
			
			# remove all numbers and dow and month names
			# this should eliminate empty navigation tables
			table_text = table.get_text().strip()
			table_text = re.sub(r'\d','',table_text)

			for period in G.mth_dow:
				table_text = re.sub(r'\b'+period+r'\b','',table_text,
					flags=re.I)
			
			if len(table_text) > min_table_text:
				if re.search(r'[a-zA-Z]+', table_text):
					table_has_data = True

			if table_has_data:

				# return text in the table as bs tags
				# will return None if no cal dates
				# of type 7, 8 etc or Wed 7, 8 Thurs etc
				# will ignore dates of type 7 Dec 2020 unlikely to be cal
				# which are likely div type data structured inside a table 
				bs_tags = extract_table_contents(table)

				if bs_tags is not None:
					
					# parent tag
					cal_div = BeautifulSoup('<div></div>','lxml')

					for bs_tag in bs_tags:
						cal_div.append(bs_tag)
						cal_div.append('\n')

					# attach to tree and then delete the table	
					table.insert_after(cal_div)				
					table.decompose()
					
					found_valid_cal_data.append(True)

				else:
					found_valid_cal_data.append(None)

	return souped, found_valid_cal_data


def create_doclist(souped):
	''' create the doclist from string '''

	doclist = []
	max_len = 1000
	soup_text = souped.get_text()
	soup_lines = create_line_breaks(soup_text)

	for line in soup_lines:
		line = line.strip()	
		if line:
			if len(line) > max_len: continue

			if not doclist:
				doclist.append(line)
			else:
				if doclist[-1] != line:
					doclist.append(line)

	return doclist


def get_doclist(url_num,url,souped,seed_url,**kwargs):
	''' extract images and text from scraped url '''

	organiser = None
	ven_ref = None
	is_calendar = False
	
	a = datetime.datetime.now()
	print('Starting get_doclist: ', a)

	#get trav direction
	if 'test_org' in kwargs.keys():
		if kwargs['test_org']:
			organiser = Seed.objects.get(seed=kwargs['test_org'])
			trav_up = organiser.title_up
			ven_ref = organiser.ven_ref

	else:
		organiser = Seed.objects.get(seed_url=seed_url)
		trav_up = organiser.title_up
		ven_ref = organiser.ven_ref

	# remove nodes we don't want
	souped = chuck_soup_nodes(souped, seed_url)
	
	beg = time.time()
	# for calendar we'll test tables
	# each table is tested in turn to see if it has dates + text
	# replace calendar tables with new tags of calendar events
	# this makes it easier to parse text later
	# copy souped in case tree is modified but we don't have a calendar
	reserve_souped = copy.copy(souped)
	souped, found_valid_cal_data = get_calendars_in_tables(souped)
	if any(found_valid_cal_data):
		is_calendar = True
	else:
		souped = reserve_souped

	end = time.time()
	print('...... check if is_calendar: ', str(round(end-beg,1))+'s')

	
	print('......... is_calendar: ', is_calendar)

	beg = time.time()
	doclist = create_doclist(souped)
	end = time.time()
	print('...... create doclist: ', str(round(end-beg,1))+'s')
	#for d in range(len(doclist)): print(doclist[d])

	# scrub doclist
	refine_doclist = {
	#'' is to specify 'y' for printing
	'clean_line_breaks:':(clean_line_breaks, ''),
	'remove ignores:':(remove_ignores, ''),
	'remove ordinals:':(remove_ordinals, ''),
	'concat descriptions':(concat_descriptions, ''),
	'concat start and ends:':(concat_start_ends, ''),
	'match time suffixes': (match_time_suffixes, ''),
	'set calendar month heads':(set_calendar_month_heads,''),
	'trim calendar to month':(trim_calendar, ''),
	'affix month name to cal days:':(affix_calendar_month, ''),
	'remove month lists': (remove_month_lists, ''),
	'affix month name to non-cal days': (affix_month_heads, ''),
	'concat dates:':(concat_dates, ''),
	'concat times':(concat_times,''),
	'remove repeat dates':(remove_repeat_dates, ''),
	'remove prior events:':(remove_prior_events, ''),
	'check doclist len':(check_doclist_len, ''),
	'remove image duplicates:':(scrub_duplicate_images, ''),
	'clean doclist':(clean_doclist, ''),

	}

	for descr, job in refine_doclist.items():
		beg = time.time()
		doclist = job[0](doclist,is_calendar=is_calendar,
						organiser=organiser,trav_up=trav_up,
						ven_ref=ven_ref)
		
		end = time.time()
		print('.'*6,descr,'[',len(doclist),']',str(round(end-beg,1))+'s')
		if job[1] == 'y': #for debugging
			for line in range(len(doclist)): print(line,doclist[line])


	###############################
	if print_doclist == 'y':
		line_num = 1
		print('\n')
		print(url_num,'>>',url)
		print('='*50)
		for line in doclist:
			print(line_num,line)
			print('-'*50)
			line_num += 1
		print('\n\n')
	
	return doclist


def find_multis(date):
	''' find instances of mutiple dates '''

	#dealing with multiple dates
	#e.g. 12 & 13, 19 Nov
	#e.g. 12, 13, 19 Nov or 12th,13th but not Dec 6th, 2016

	multis, date_mths, sections = [], [], []
	this_yr = datetime.datetime.today().year

	# return date as if no markers
	multi_markers = G.multi_date_markers
	if not any(mul in date for mul in multi_markers):
		return multis
	
	remain = date

	#compile mths in date
	#can have 1 mth only eg 23, 25 Nov
	#or several: eg 23 Oct, 15 & 18 Dec
	finds = re.findall(r'\b'+r'([a-zA-Z]{3,9})'+r'\b',remain)
	for f in finds:

		#so mths are listed in order in date rather than order of eg long_mths
		if f.lower() in G.all_months and \
			f.lower() not in date_mths:
			date_mths.append(f)
	
	# change mmm dd ---> dd mmm
	d_mmm = True
	mth_pos = []
	if any(date.startswith(mth) for mth in date_mths):
		d_mmm = False
		for mth in date_mths:
			mth_pos.append(remain.find(mth)+len(mth)) #where mth is)
		mth_pos.append(999)

	for mth in date_mths:

		it, years, year = None, None, None

		# find long month
		# take care of: jan. 20
		#if mth[-1] == '.': mth = mth.strip('.')
		try: long_mth = G.short_long[mth]
		except: long_mth = mth

		while mth in remain:

			pos = remain.find(mth)+len(mth) #where mth is

			if d_mmm:
				years = find_years(remain)
				it = remain[:pos] # potential digs preceding mth
				prior_dp = 0
				
			else:
				next_mp = mth_pos[1]
				years = find_years(remain)
				it = remain[pos:next_mp] # digs following mth
				
			if years: year = years[0]			
			
			#lookback to only pick up the 25 in '25 Aug' not the 18 in '2018'
			digs = re.findall(r'(?<!\d)(\d{1,2})(?!\d)',it,flags=re.I)

			#now parse date for each 'dd'
			d_pos = None
			for d in digs:

				# where dd is: use span to avoid 21 in 2021 from jan 21, 2021
				d_pos = re.search(r'(?<!\d)'+d+r'(?!\d+)', remain)
				d_pos = d_pos.span()[0]

				if d_mmm:
					if '-' in remain[prior_dp:d_pos]: #eg 23 - 27
						# add to prev line: 23 Mth - 27 Mth
						try: sections[-1] += ' - ' + d + ' ' + long_mth
						except: pass
					else:
						# create d Mth
						new = d + ' ' + long_mth
						if year:
							new += ' ' + year
						sections.append(new)

					prior_dp = d_pos

				else: # mmm_d cases
					if '-' in remain[d_pos:next_mp]: #eg apr 23 - may 27
						try:
							sections[-1] += ' - ' + d + ' ' + long_mth
							if year:
								sections[-1] += ' ' + year
								remain = remain.replace(year,'')
						except: 
							# remove mth as pos we got it wrong and we have
							# apr 23 - may 27 and 2nd mth remaining in 'remain'
							# making 'while ' become infinite
							remain = remain.replace(mth, '')
					else:
						# create d Mth
						new = d + ' ' + long_mth
						if year: 
							new += ' ' + year
							remain = remain.replace(year,'')
						sections.append(new)

			# must be outside for loop
			if d_mmm: remain = remain[pos:]
			else: 
				if d_pos:
					remain = remain[d_pos:]
				else:
					# avoid infinite loop 'while mth in remain'
					remain = remain.replace(mth,'')

		# reset mth_pos
		mth_pos = mth_pos[1:]


	#not multi if singular date
	if len(sections) <= 1: #if singular date
		pass	
	else:
		multis = sections

	return multis


def prep_get_dates(line,line_num,doclen,strip_dates_too=False):
	''' stuff to get line ready for parsing dates '''

	# F=pos date; don't skip & continue the loop this func is in
	# T=This is a certainly not a date
	# replace excludes ',' needed for find_multis()
	continue_ = False 
	replace = ['(',')','[',']','$']

	last_line = max(0,doclen - 1)

	if not possible_date(line):
		continue_ = True
	
	elif line_num > last_line:
		continue_ = True
	
	else:
		#remove stuff eg time component as may be conflated with date
		#eg in '7pm, 5th June 2018' or '5 June 2018 10:00'
		a = strip_currencies(line)
		b = strip_time(a,strip_dates_too)
		c = strip_chars(b)

		d = c
		for r in replace:
			d = d.replace(r,'')
		
		# remove reg_markers and original line 
		if G.reg_marker in d:
			pos = d.find(G.reg_mark_end)
			d = d[:pos]
			d = d.replace(G.reg_marker,'')

		line = d

	return continue_, line


def scrub_found_dates(found):
	''' clean up date patterns found '''

	# by now during concat_dates:
	# slash dates have been converted 
	# us-style dates have been converted
	# yy have been converted to yyyy
	# to/until standardised to ' - '
	# fixed from_ but no to_ ; until_ but no from_

	found = strip_time(found)

	#if of form d-mmm-y or yyyy-mmm-dd replace - with spaces
	dash_dates = re.findall(r'(\d{0,4}-\d{1,2}-\d{0,4})',found)
	if not dash_dates:
		dash_dates = re.findall(r'(\d{0,4}-[a-zA-Z]{0,9}-\d{0,4})',
									found)

	if dash_dates:
		if len(dash_dates) == 1: #case single date
			found = dash_dates[0].replace('-',' ')
			found = replace_digit_with_txt(found)
			found = found.lower()

		if len(dash_dates) == 2: #<from> - <to>
			for i in range(len(dash_dates)):
				dash_dates[i] = dash_dates[i].replace('-',' ')
				dash_dates[i] = \
						replace_digit_with_txt(dash_dates[i])
			found = dash_dates[0] + ' - ' + dash_dates[1]
			found = found.lower()
			
	
	#if of form d mmm. y then remove .
	if re.search(r'(\d{1,2}\s[a-zA-Z]{0,9}\s*\.\s*\d{0,4})',found):
		found = found.replace('.','')

	#if of form mmm. d yyyy remove .
	if re.search(r'([a-zA-Z]{0,9}\.\s\d{1,2},*\s\d{0,4})',found):
		found = found.replace('.','')

	# remove any remaining non relevant chars
	# also now that multis are done
	non_rel = [',']
	for non in non_rel: found = found.replace(non,'')

	found = strip_chars(found)

	return found


def get_dates(doclist,url,ven_ref,patterns):
	''' get any likely event dates from scraped data '''
	
	dates = defaultdict(dict)
	orig_date = ''
	tries, max_tries, max_dates = 0, 100, 100 #max date-like stuff to check 
	line_num, min_date_len, max_date_len = 0, 3, 70 #min to catch case: 5/1
	doclen = len(doclist)

	for line in doclist:

		line_num += 1  
		orig_line = line
		
		#prep dates
		continue_, line = \
			prep_get_dates(line,line_num,doclen,strip_dates_too=False)

		if continue_: continue

		patt_index = 0
		for pattern in patterns:

			found = re.findall(pattern, line, flags=re.I)			
		
			if found:
				found = found[0]

				if not possible_date(found):
					continue
				
				#to avoid unbalanced parenthesis error if regex creates one
				found = reset_unbalanced_parenthesis(found)

				#save date as found
				orig_date = found
				found = found.lower()

				# find multis
				finds = find_multis(found)
				if not finds:
					finds = [found]
			
				#scrub found
				finds = [scrub_found_dates(f) for f in finds]
				finds = [strip_not_text(f,G.all_months) for f in finds]
				
				for f in finds:

					f = remove_spaces(f)
					f = f.strip()

					# create unique dict key
					orig_date = orig_date + ':::Doclist ' + str(line_num)

					dates[orig_date] = {}
					dates[orig_date]['url'] = url
					dates[orig_date]['orig_date'] = orig_date
					dates[orig_date]['date'] = f
					dates[orig_date]['line'] = orig_line
					dates[orig_date]['index'] = line_num
					dates[orig_date]['pattern'] = patterns[patt_index]
					dates[orig_date]['patt_index'] = patt_index
									
				#break as found
				break


	#list all 'dates' found
	#######################################################		
	#print('\n')
	#print('FOUND DATES')
	#print('='*50)
	#for k, v in dates.items():
	#	print(k,'\n',v,'\n\n')
	#######################################################

	return dates


def convert_text_date(text):
	''' convert text date into Python object '''

	text = text.title()

	try:
		converted = datetime.datetime.strptime(text, "%d %B %Y")
	except:
		try: 
			converted = datetime.datetime.strptime(text, "%d%B %Y")
		except:
			try:
				converted = datetime.datetime.strptime(text, "%d %B%Y")
			except:
				converted = False
				return converted

	converted = converted.date()
	return converted


def ignore_what(txt,print_=True):
	''' return if txt contains stuff to ignore '''

	ignored = False
	offence = ''
	if not txt: return True
	orig_txt = txt 	
	txt = strip_chars(txt)

	htmls = G.list_html + G.list_includes_html + G.list_js
	if any(html in txt for html in htmls):
		ignored = True

	if not ignored:
		for ign in G.ignore_in_title:
			if re.search(r'\b'+ign+r'\b',txt.lower()):
				ignored = True
				if print_: 
					print('{:<7}'.format(''),'fails ignore_in_title > ',
						"'",ign,"'", 'in', txt)
				break

	#ignore lines tetxt on its own is unlikely to be title
	if not ignored:
		for ign in G.ignore_title:
			if txt.lower().strip() == ign:
				ignored = True
				if print_:
					print('{:<7}'.format(''),'fails ignore_title > ',
						ign)
				break

	#ignore lines where start of line is unlikely to be title
	if not ignored:
		ign_start_status = False
		ign_end_status = False
		ign_punct_end_status = False

		for ign_start in G.ignore_title_start:
			
			if ign_start not in txt and \
				ign_start not in orig_txt: continue
			
			try:
				if txt.startswith(ign_start) or \
					orig_txt.startswith(ign_start):
					ignored = True
					ign_start_status = True
					break
			
			# catch specials like '+' which throw regex errors
			except: pass


		if not ignored:
			for ign_end in G.ignore_title_end:
				if re.search(r'\b'+ign_end+r'\b$',txt) or \
					re.search(r'\b'+ign_end+r'\b$',orig_txt):
					ignored = True
					ign_end_status = True
					break

			if not ignored:
				for ign_punct_end in G.puncts:
					if re.search(r'\b'+ign_punct_end+r'\b$',txt) or \
						re.search(r'\b'+ign_punct_end+r'\b$',orig_txt):
						ignored = True
						ign_punct_end_status = True
						break

		if ignored:
			if ign_start_status: 
				offence = ign_start
			elif ign_end_status: 
				offence = ign_end
			elif ign_punct_end_status: 
				offence = ign_punct_end

			if print_:
				print('{:<7}'.format(''),
					'looks like unlikely start/end for title > ',
						offence)

	if not ignored:
		for K,V in G.ignore_title_combos.items():
			if K in txt:
				for v in V:
					if re.search(r''+str(v),txt,flags=re.I):
						if print_:
							print('{:<7}'.format(''),
							'looks like ignore combo > ',v)
						ignored = True
						break
			if ignored: break

	return ignored


def is_price(txt):
	''' check if price '''
	txt = txt.lower()
	price = False
	clues = ['£', 'gbp', '€', 'euro', 'eur', '\\$']
	marks = ['price', 'ticket'] 
	if any(re.search(r'\d*\s*'+c+r'\s*\d*',txt,flags=re.I)
		 	for c in clues) or \
		any(m in txt.lower() for m in marks):
		price = True
	return price


def is_email(txt):
	''' check if email '''
	is_ = False
	if re.search(r'.*@.*\..*',txt): is_ = True
	return is_


def is_day(txt):
	''' check if is day of week '''
	is_ = False
	txt = txt.lower().strip()
	finds = []

	for d in G.all_days:
		if txt == d: 
			is_ = True
			break
			
		#case: Monday - Saturday or 'Mon, Wed, Thurs'
		if re.search(r'\b'+d+r'\b',txt):
			finds.append(d)
			if len(finds) > 1:
				is_ = True
				break

		if is_: break

	return is_


def is_org(txt,org):
	''' txt looks like the org name '''
	is_ = False
	txt, org = txt.lower(), org.lower()
	#also need to test if txt is just a long decsrip
	#that happens to have org_name in it
	if (txt in org or org in txt) and \
		len(org) / 2 < len(txt) < len(org) * 1.5:
		#if long txt then unlikely org name 
		is_ = True
	return is_


def is_meta(txt,metas,tags):
	''' is txt mainly metas or tags '''
	
	is_ = False
	meta_count, meta_max 	= 0, 2
	tag_count, tag_max 		= 0, 3
	txt = txt.split()

	for t in txt:
		if t in metas:
			meta_count += 1
		if meta_count >= meta_max:
			is_ = True
			break

		if t in tags:
			tag_count += 1
		if tag_count >= tag_max:
			is_ = True
			break
	return is_


def is_mth(txt):
	''' line is just a month name on it's own '''
	is_ = False
	min_len = 2
	txt = txt.lower()
	for mth in G.all_months:
		if re.search(r'\b'+mth+r'\b',txt):
			txt = re.sub(mth,'',txt)
			txt = strip_chars(txt)
			if len(txt) < min_len:
				is_ = True
				break
		if is_: break
	return is_


def is_inval_pattern(txt):
	''' txt includes invalid patterns '''
	is_ = False
	txt = txt.lower()
	invals = [
			r'\d+,\d+', #list of numbers
			r'\d+in', r'\d+cm', r'\d+mm', r'\d+\"', ##art, frame/photo size
			r'\d+\s*x\s*\d+', #art, frame/photo size
			r'tel[:|\.]\s*', #telephone no, 'telephone' in ignore_doclist
			r'\d{3,},*\s*\d{3,}', #tel numbers, '{3,'' to avoid dates
			r'phone.*\d+',
			r'fake\s\d+', #fake lines added to doclist
			r'^\d+\s*-*week', #4 weeks!
			r'\d+\s*-*per', #5-persons, 3 per child
			r'cover\s*\:*\s*\$\d', #cover $20
			r'^\d+\+', r'^\d+\sand', r'^\d+\s*min', #18+; 21 and over, #40 mins
			r'over\s\d+', #over 21s
			r'running.*\d', #running 1hr
			r'\d+\s*min', #72 min, 90mins, 60 minutes
			r'\d+\s*items', #basket, cart, results
			r'room\s\d',r'gallery',r'lower floor',r'upper floor',
			r'bar.*open',r'bar.*drinks',r'drinks.*bar',r'^drinks',
			r'doors\:*\s*.*?\d', #doors [open] 7pm - need to avoid 'the doors'
			r'evening show$', #evening show
			r'closes\s\d+', #closes 3pm
			r'\d+.*found', # 6 events found
			r'^\?', # starts with ? eg http://boo.com/events/?range=all
			r'&amp', # remnants of re.subs
			]

	for i in invals:
		if re.search(i, txt, flags=re.I):
			is_ = True
			break
	
	return is_


def is_country(txt):
	''' txt is country name pos from address '''
	is_ = False
	txt = txt.lower()
	if txt in G.countries:
		is_ = True
	return is_


def is_specials(txt):
	''' test if txt malformed from various re.subs leaving specials '''
	#eg. txt could be '21 &, 31 -, good & , art'
	is_ = False
	txt = txt.strip('...') # b/c probably valid
	permit = ['|','//','/','...'] # not unusal separators in valid titles
	
	words = re.findall(r'\w{3,}',txt) # how many substantial worda
	txt = re.findall(r'\W',txt)

	if txt:
		specs = [t for t in txt if len(t.strip()) > 0] #remove spaces
		specs = [t for t in specs if t not in permit]

		# too many above what's "normal" and too few words
		if len(specs) >= 4 and len(words) < 4:
			is_ = True
	return is_


def bad_len(txt):
	''' test len in range '''
	is_bad = True
	min_title, max_title = 3, 100
	if min_title <= len(txt) <= max_title: 
		is_bad = False
	return is_bad


def title_tests(txt,org,metas,tags):
	''' test if text qualifies as an event title '''

	class test_elem():
		def __init__(self,test,failed):
			if failed is None: failed = False
			self.test = test
			self.failed = failed
		def __repr__(self):
			return self.test

	test_elems = []

	# tests not done inside dict b/c all would be done
	# when the dict is created
	tests = {
		'bad len': bad_len,
		'image link': is_img_link,
		'is_date': possible_date,
		'is_price': is_price,
		'is_time': get_time,
		'is_email': is_email,
		'is_not_text': has_text,
		'is_meta_tag': is_meta,
		'is_day': is_day,
		'is_org': is_org,
		'is_mth': is_mth,
		'is_ctr': is_country,
		'is_inv_p': is_inval_pattern,
		'is_specials': is_specials,
		'is_descr_like': is_descr,
		'is_quote': is_quote,
		'in ignore_what': ignore_what,
	}

	# tests done here so first fail can be caught
	for test, func in tests.items():
		if test == 'is_not_text':
			elem = test_elem(test, not func(txt))
		elif test == 'is_meta_tag':
			elem = test_elem(test, func(txt,metas,tags))
		elif test == 'is_org':
			elem = test_elem(test, func(txt,org.seed))
		else:
			elem = test_elem(test, func(txt))
		if elem.failed:
			test_elems.append(elem)
			break
	return test_elems


def print_test_errors(test_elems):
	''' print test errors for title and descriptions '''
	for e in test_elems:
		if e.failed:
			print('{:<7}'.format(''),'failed: ',e.test)
	return


def looks_like_free_event(txt):
	''' check if text looks like free or paid event '''
	looks_like = False
	if any(f in txt for f in G.free_types):
		looks_like = True
	return looks_like


def get_event_time(date,anchor,doclist):
	''' get time for event being parsed '''

	print('\n')
	print('TIME for event on >> ',
			date.upper(),' << at Doclist', anchor + 1)
	print('-'*70)
	
	# check for time on same line as date
	event_time = None

	# search for time on same line
	item = doclist[anchor]
	time = get_time(item,as_input=False)
	if time:
		event_time = time
		print('{:<4}'.format(100), 'time found on same line > ', event_time)
	
	if event_time is None:
		# traverse doclist - we only traverse down for times
		# set lower, upper bounds of doclist to traverse and step
		span		= 6
		low_bound	= anchor + 1
		upp_bound	= min(len(doclist), anchor + span + 1)
		step 		= 1
	
		for i in range(low_bound, upp_bound, step):

			item = doclist[i]

			print('{:<4}'.format(200), 'test > ', item)
			
			# exit if reached another date
			if possible_date(item):
				print('{:<4}'.format(300), 
					'exit traverse - reached another date', item)
				break

			# else carry on and get time
			time = get_time(item,as_input=False)
			if time is not None:
				event_time = time					
				break

	if event_time is not None:
		print('{:<4}'.format(400), 'SET TIME >', event_time)
	else:
		print('{:<4}'.format(400), 'time not found')

	return event_time


def scrub_reg_mark(txt):
	''' remove reg_mark from line '''
	start = G.reg_marker
	end = G.reg_mark_end
	t = re.search(r''+start+r'(.*)'+r''+end,txt)
	if t:
		txt = t.group(1)
	else:
		pass
	return txt


def get_event_descr(date,anchor,doclist):
	''' get descr for event being parsed '''

	print('\n')
	print('DESCRIPTION for event on >> ',
			date.upper(),' << at Doclist', anchor + 1)
	print('-'*70)
	
	event_descr = ''

	# traverse doclist - we only traverse down for descriptions
	# set lower, upper bounds of doclist to traverse and step
	span		= 6
	low_bound	= anchor + 1
	upp_bound	= min(len(doclist), anchor + span + 1)
	step 		= 1

	for i in range(low_bound, upp_bound, step):

		item = doclist[i]
		item = scrub_reg_mark(item)

		print('{:<4}'.format(200), 'test > ', item)
		
		# exit if reached another date
		if possible_date(item):
			print('{:<4}'.format(300), 
				'exit traverse - reached another date', item)
			break

		# else carry on and get description		
		if is_descr(item):
			event_descr = item
				
			if any(d in event_descr for d in G.strip_descr):
				for d in G.strip_descr:
					event_descr = re.sub(d, '', event_descr)

			event_descr = remove_spaces(event_descr)
			event_descr = strip_chars(event_descr)			
			break
		else:
			print('{:<4}'.format(300), 'not description')


	if event_descr != '':
		print('{:<4}'.format(400), 'SET DESCR >', event_descr)
	else:
		print('{:<4}'.format(400), 'description not found')

	return event_descr


def get_event_image(date,anchor,doclist,first_up):
	''' get image for event being parsed '''

	print('\n')
	print('IMAGE for event on >> ',
			date.upper(),' << at Doclist', anchor + 1)
	print('-'*70)
	
	event_image = ''

	exit_traverse = False
	traverse = ['up', 'down']
	if not first_up: traverse = ['down', 'up']

	for trav in traverse:

		if exit_traverse: break

		print('{:<4}'.format(100), 'traversing > ', trav)

		# traverse doclist - we only traverse down for descriptions
		# set lower, upper bounds of doclist to traverse and step
		span = 6
		if trav == 'up':
			
			# limited span if trav opposite to normal 
			if not first_up: span = 1
			
			low_bound	= max(0, anchor - 1)
			upp_bound	= max(0, anchor - span - 1)
			step 		= -1
		else:

			# limited span if trav opposite to normal 
			if first_up: span = 1

			low_bound	= anchor + 1
			upp_bound	= min(len(doclist), anchor + span + 1)
			step 		= 1


		for i in range(low_bound, upp_bound, step):

			item = doclist[i]

			print('{:<4}'.format(200), 'test > ', item)
			
			# exit if reached another date
			if possible_date(item):
				print('{:<4}'.format(300), 
					'exit traverse - reached another date', item)
				exit_traverse = True
				break
		
			# check has no spaces (as it fails url link) and inval words
			if is_img_link(item):
				not_link = [' ','banner','logo']
				if not any(not_ in item for not_ in not_link):
					event_image = item[len(G.img_linker):]	
					exit_traverse = True
					break

		if event_image != '':
			print('{:<4}'.format(400), 'SET IMAGE > ',event_image)
		else:
			print('{:<4}'.format(400), 'image not found')

	return event_image


def get_event_free(date,anchor,doclist):
	''' lookaround if event is free '''

	print('\n')
	print('ADMISSION for event on >> ',
			date.upper(),' << at Doclist', anchor + 1)
	print('-'*70)
	
	event_free = False
	traverse = ['up', 'down']

	# first check line itself
	item = doclist[anchor]
	print('{:<4}'.format(100), 'test date line > ', item)
	if looks_like_free_event(item):
		event_free = True
		print('{:<4}'.format(400), 'SET ADMISSION FREE >', event_free)
		return event_free

	# otherwise traverse
	exit_traverse = False
	for trav in traverse:

		if exit_traverse: break

		print('{:<4}'.format(150), 'traversing > ', trav)

		# traverse doclist - we only traverse down for descriptions
		# set lower, upper bounds of doclist to traverse and step
		span = 1
		if trav == 'up':
			low_bound	= max(0, anchor - 1)
			upp_bound	= max(0, anchor - span - 1)
			step 		= -1
		else:
			low_bound	= anchor + 1
			upp_bound	= min(len(doclist), anchor + span + 1)
			step 		= 1


		for i in range(low_bound, upp_bound, step):

			item = doclist[i]

			print('{:<4}'.format(200), 'test > ', item)
			
			# exit if reached another date
			if possible_date(item):
				print('{:<4}'.format(300), 
					'exit traverse - reached another date', item)
				exit_traverse = True
				break
	
			# check has no spaces (as it fails url link) and inval words
			if looks_like_free_event(item):
				event_free = True	
				exit_traverse = True
				break

		if event_free:
			print('{:<4}'.format(400), 'SET ADMISSION FREE >', event_free)
		else:
			print('{:<4}'.format(400), 'free admission not found')

	return event_free


def scrub_event_title_line(date, txt, org, metas, tags):
	''' check line for title or time content '''

	event_title = ''
	bracks = ['\(', '\)', '\[', '\]']
	months = G.all_months

	# flag if date in orig text
	date_in_txt = False
	if date in txt:
		date_in_txt = True

	# prepare
	for br in bracks:
		txt = re.sub(br,'',txt)
	txt = scrub_reg_mark(txt)
	txt = strip_time(txt)
	if txt.strip() == '': 
		return txt.strip()

	# remove dow
	if any(day in txt for day in G.all_days):
		for day in G.all_days:
			if txt.strip() == day:
				txt = ''

			elif re.search(r'\d',txt):
				# only if day as in date else removes titles like
				# 'easy sunday workshop'

				# 8 Wed
				txt = re.sub(r'(\d{1,2}\s'+day+r')', '', txt) 

				# Wed 8 feb 2019 but the '8 feb 2019' to be replaced below
				# crucially \s\d+ to avoid case: 'Wednesday Jam' 
				txt = re.sub(r'('+day+r')\s\d{1,2}', '', txt) 
				
				# saturdays 
				txt = re.sub(r'\b'+day+r's,*\b','', txt)

				# saturday, 
				txt = re.sub(r'\b'+day+r',*\b','', txt)


	# remove date - nb. after removing dow
	txt = txt.replace(date,'')
	
	# remove any other dates
	# leave months with text as in: 'march sessions'
	# remove if mth at end of line as unusual for a title
	if any(mth in txt for mth in months):
		for mth in months:
			if txt.strip() == mth: 
				txt = ''
				break
			if mth in txt:
				txt = re.sub(r'(\d+\s'+mth+r',*\s*\d{0,4})', '', txt)
				txt = re.sub(r'('+mth+r'\s\d{1,2},*\s*\d{0,4})', '', txt)
				
				# possible to still have month stranded
				# case: thursday 21 march 7pm andrew maxwell
				# all the above would leave 'march andrew maxwell'
				# whereas in cases like 'march jazz sessions' - more likely
				# no date in txt; and if any date in txt then ...
				# 'jazz sessions' as title still not bad
				if date_in_txt:
					txt = re.sub(r'\b'+mth+r'\b','',txt)


	# clean up
	if txt.strip() == '':
		return txt.strip()
	txt = reset_unbalanced_parenthesis(txt)
	txt = strip_chars(txt)
	for dash in G.dashes:
		txt = txt.strip(dash)
	txt = txt.strip()

	return txt


def cleanup_title(title):
	''' clean up event title '''

	title = title.strip()
	if len(title) >= 3:
		if title[-3:] == ' at': 
			title = title[:-3]

	#remove titles of type ", blah blah"
	title = strip_chars(title)
	title = title.strip('.')
	title = re.sub(r'\(\)','',title) #remove '()'

	#remove any last digits not year eg 'Blah 21 2019' 
	#b/c mth in date removed
	finds = re.findall(r'(\d{1,2},*\s*\d{4})',title)
	if finds:
		for f in finds:
			title = title.replace(f,'')

	finds = re.findall(r'\s(\d{1,2})\s*$',title)
	if finds:
		for f in finds:
			title = title.replace(f,'')

	title = strip_chars(title)
	title = title.strip()

	#remove gumpf at start/ends eg '-'
	title = remove_spaces(title)
	for dash in G.dashes:
		title = title.strip(dash)

	return title


def parse_url_for_title(url,org,metas,tags):
	''' check if title could be in url '''

	event_title = ''	
	potentially_after = ['events/','show/','shows/','exhibition/',
						'theatre/']
	if any(p in url for p in potentially_after):
		for p in potentially_after:
			patt = re.compile(r'.*?'+p+r'(.*)')
			maybe = re.findall(patt,url)
			if maybe:
				maybe = re.sub('_',' ',maybe[0])
				maybe = re.sub('-',' ',maybe)
				test_elems = title_tests(maybe,org,metas,tags)
				if not any(e.failed for e in test_elems):
					event_title = maybe.strip()
					break
	
	return event_title


def indicative_full_title(txt):
	''' indicative of proper title already '''
	indicative = False
	inval_start = ['feat'] #ignore 'featuring: blah'
	t_marks = ['presents','present']
	t_signs = [':'] #\b doesn't work for type = txt:
	if not any(txt.startswith(inv) for inv in inval_start) and \
		(any(re.search(r'\b'+t_+r'\b',txt) for t_ in t_marks) or \
		any(' '+dash+' ' in txt for dash in G.dashes) or \
		any(t_ in txt for t_ in t_signs)):
		indicative = True
	return indicative


def test_title_elems(date, txt, org, metas, tags):
	''' apply title tests '''
	txt_test_elems = title_tests(txt, org, metas, tags)
	return txt_test_elems


def compose_event_title(maybe, maybe_test, switch, switch_test, first_up):
	''' set the event title using maybe and switch '''

	event_title = ''

	if not maybe_test: # empty list so no fails 

		if indicative_full_title(maybe):
			event_title = maybe
			print('{:<4}'.format(210), 'indicative full title in maybe')

		elif not switch_test:

			if switch.endswith('...'):
				# some sites have descr on hover on pic above title & date
				# would very likely have descr ending in '...'
				event_title = maybe
				print('{:<4}'.format(230), 
				'use maybe as looks like kind Descr.../Title')
			
			elif indicative_full_title(switch):
				event_title = switch
				print('{:<4}'.format(220), 'indicative full title in switch')

			elif maybe not in switch and \
				switch not in maybe: 
				
				# if trav_up: then order is > line_before:this_line
				# if trav_down: order is > this_line:next_line
				if first_up:
					event_title = switch + ': ' + maybe
				else:
					event_title = maybe + ': ' + switch

				print('{:<4}'.format(240),
					'looks like kind: Title1/Title2/Date')

			else:
				event_title = maybe
				print('{:<4}'.format(250), 'switch has failed - use maybe')

		else:
			event_title = maybe
			print('{:<4}'.format(260), 'looks like title in maybe only')

	return event_title


def scan_line(date, item, org, metas, tags):
	''' check date line for title '''
	
	event_title = ''

	print('{:<4}'.format(100), 'start test with > ',item)
	item = scrub_event_title_line(date, item, org, metas, tags)

	item_test_elems = \
			title_tests(item, org, metas, tags)
	if not any(e.failed for e in item_test_elems):
		event_title = item

	return event_title


def get_event_title(date,anchor,doclist,first_up,url,org):
	''' get title of event '''

	event_title, maybe = '', ''	
	metas 	= [m.lower() for m in values_list['metas']]
	tags 	= [t.lower() for t in values_list['tags']]

	print('\n')
	print('TITLE for event on >> ',
			date.upper(),' << at Doclist', anchor + 1)
	print('-'*70)

	if not isinstance(anchor,int): 
		print('{:<4}'.format(1),'SCRAP > anchor not a number', anchor + 1)
		return event_title

	# scan dateline for title
	item = doclist[anchor]
	event_title = scan_line(date, item, org, metas, tags)
	if event_title == '':
		print('{:<4}'.format(110), 'no TITLE found in date line')

	# if no luck see if what we want is just before/after headers
	if first_up: trav = 'up'
	else: trav = 'down'

	if event_title == '':

		span = 6
		if first_up:
			low_bound	= max(0, anchor - 1)
			upp_bound	= max(0, anchor - span - 1)
			step 		= -1
		else:
			low_bound	= anchor + 1
			upp_bound	= min(len(doclist), anchor + span + 1)
			step 		= 1

		print('{:<4}'.format(130),'traversing > ',trav)
		
		for i in range(low_bound, upp_bound, step):

			# get a line to parse
			maybe = doclist[i]
			
			# exit if reached a date
			if possible_date(maybe):
				print('{:<4}'.format(150),
				'exit traverse - reached a date or a mth_head')
				break
			
			maybe = scrub_event_title_line(date, maybe, org, metas, tags)

			print('{:<4}'.format(140),'test >', maybe)

			# test the line and print any errors
			maybe_test_elems = test_title_elems(
							date, maybe, org, metas, tags)

			maybe_test = [e.failed for e in maybe_test_elems]
			
			# sometimes title can fail because it's an amalgam
			# 'title : some descr like'
			# test first half and use that if it passes
			if any(maybe_test):
				
				if ':' in maybe and not is_img_link(maybe):
					maybe1 = maybe.split(':')[0]
					maybe1_test_elems = test_title_elems(
							date, maybe1, org, metas, tags)
					maybe1_test = [e.failed for e in maybe1_test_elems]
					
					if any(maybe1_test): # fails
						print_test_errors(maybe1_test_elems)
					else: # passes and we'll use this only
						maybe = maybe1
						event_title = maybe
						break
				else:
					print_test_errors(maybe_test_elems)


			else:

				if trav == 'up':
					switch_index = i - 1
				else:
					# more likely Date, Promoter/EventType, Title
					switch_index = min(len(doclist) - 1, i + 1)

				switch = doclist[switch_index]

				if possible_date(switch):
					print('{:<4}'.format(190), 
						'switch is possible date > ',switch)
					switch = ''

				switch = scrub_event_title_line(date, switch, org, metas, tags)
				print('{:<4}'.format(170),'potential switch >',switch)

				print(171,switch)

				switch_test_elems = \
						test_title_elems(date, switch, org, metas, tags)
				switch_test = [e.failed for e in switch_test_elems]	
				print(172,switch_test_elems)	
				
				# if switch fails, use maybe
				# else compoise using both maybe and switch
				if any(switch_test): 
					print_test_errors(switch_test_elems)
					print('{:<4}'.format(180),'switch fails - use maybe')
					event_title = maybe

				else:
					# switch passes 
					event_title = \
						compose_event_title(
						maybe, maybe_test, switch, switch_test, first_up)

				if event_title != '':
					break						


	# often the title is in the url for shows
	if event_title == '':
		event_title = parse_url_for_title(url,org,metas,tags)
		print('{:<4}'.format(200),'taken from url > ', event_title)

	# remove org ignores
	if event_title != '':
		org_ignore = get_org_ignores(org)
		if org_ignore is not None:
			if any(ign in event_title for ign in org_ignore):
				for ign in org_ignore:
					event_title = event_title.replace(ign, '')
				print('{:<4}'.format(250),'excl org ignores > ', event_title)

	# clean up
	if event_title != '':
		event_title = cleanup_title(event_title)
		if len(event_title.strip()) > 0:
			print('{:<4}'.format(400),'SET TITLE > ', event_title)
		else:
			print('{:<4}'.format(400),'no TITLE found')
	else:
		print('{:<4}'.format(400),'no TITLE found')
		
	return event_title


def remove_event_duplicates(e_deck):
	''' we do it here b/c when we compile doclist
		we don't know if a multi-date is for a separate event
		or a multi-title is for incongruos dates
		so we grab the dates/text anyway
		and sort it out later i.e. here
	'''

	if len(e_deck) < 2: return e_deck

	#list; not non-subscriptable dict_list
	copy_deck = e_deck[:] 
	org_default = e_deck[0].org.tme_beg
	org_url = e_deck[0].org.seed_url

	#iterate through deck removing similar with shorter title
	for i in range(len(e_deck)-1):
		first, others = copy_deck[i], copy_deck[i+1:]
		f_t, f_d, f_tme = first.title, first.date_beg, first.time_beg
		f_url, f_tf = first.url, first.time_found

		for oth in others:
			o_t, o_d, o_tme = oth.title, oth.date_beg, oth.time_beg
			o_url, o_tf = oth.url, oth.time_found

			f_t_ = remove_punctuation(f_t)
			o_t_ = remove_punctuation(o_t)

			if f_t_ in o_t_ or o_t_ in f_t_:

				if f_d == o_d:

					# keep event found on home seed url page
					if f_url == org_url:
						if oth in e_deck:
							e_deck.remove(oth)
							print('.'*6 + 
								' keep event with url same as seed >',o_t[:40])

					# keep event found on home seed url page
					elif o_url == org_url:
						if first in e_deck:
							e_deck.remove(first)
							print('.'*6 + 
								' keep event with url same as seed >',f_t[:40])

					# remove one if non time-found and the other time-found
					elif o_tf and not o_tf:
						if oth in e_deck:
							e_deck.remove(oth)
							print('.'*6 + ' remove non time found >',o_t[:40])

					elif o_tf and not f_tf:
						if first in e_deck:
							e_deck.remove(first)
							print('.'*6 + ' remove non time found >',f_t[:40])

					# else remove shorter titled if same time or one
					# has '00:00' or is org default time 
					else:
						if f_tme == o_tme or \
							(f_tme == '00:00' or o_tme == '00:00') or \
							(f_tme == org_default or o_tme == org_default):

							if len(f_t) <= len(o_t):
								if oth in e_deck:
									e_deck.remove(oth)
									print('.'*6 + 
										' removing longer title >',o_t[:40])

	return e_deck


def collate_lists(e_deck):
	''' collate titles and urls from dictionary '''

	titles, descrips = [], []
	for e in e_deck:

		#compile all titles
		title = e.title.lower()
		if 'multi' in title:
			title = title[:title.find('multi')].strip()
		titles.append(title)

		#compile descriptions
		descrip = e.descr.lower()
		if descrip:
			if descrip not in descrips: descrips.append(descrip)

	return titles, descrips


def get_url(url):
	''' extract the last text in a url '''
	if url[-1] == '/':
		url = url[:-1] #b/c if last char, regex group brings back nothing
	x = re.search(r'.*/(.*)',url)
	if x: #post last / so we can do if url in title
		url = x.group(1)

	y = re.search(r'.*(\..*)',url)
	if y: #if eg url-ish.html remove the .html
		pos = url.find(y.group(1))
		url = url[:pos]
	return url


def harmonise_title_url(e):
	''' remove punctuation and strip text to make url more like title '''
	title = strip_text(e.title.lower(),'multi')
	title = remove_punctuation(title)
	url = e.url
	url = get_url(url)
	url = remove_punctuation(url,rm_dig=True)
	#rm_dig b/c url could include an event-id not in title
	return title, url


def remove_events_on_multiple_pages(e_deck):
	'''
	we remove events recorded multiple times from different pages
	first on a general page and later on own page
	but sometimes on another event's page in a 'You might also like' segment
	we remove the own-page list b/c although these usually have time
	it's not uncommon for trav to be different from main page
	and trav in Seed is based on main page
	nb. this won't deal with multiple page entries for same event
	eg on home, meta, own-pages - only own-pages removed
	'''

	urls = defaultdict(dict)
	to_delete = []				# multiple events to delete
	not_own_page_titles = []	# list of not own titles

	metas = values_list['metas']
	metas = [m.lower() for m in metas]

	# typical page title for listings - we don't want these as 'own_title'
	listings = ['listings','all','events']

	# identify all titles on page
	for e in e_deck:

		# harmonise title & url and create dictionary entries
		title, url = harmonise_title_url(e)
		if url not in urls.keys():
			urls[url] = {}
			urls[url]['titles'] = title + ','
		else: 
			urls[url]['titles'] += title + ','

		
		# identify titles currently on their own event page
		# we don't want:
		# metas else http../theatre will count 'theatre' as a title
		# general listings page else 'listings' will be taken as own title
		# and this will stop other titles being recognised
		# further url must be > 1 word else if single word we could end up
		# with 'Blah party' being own-title for a /party listings page
		if (title in url or url in title):
			if url not in metas and \
				url not in listings and \
				' ' in url:
				urls[url]['own_title'] = title			
		else:
			#add to list of titles not this url page's own title
			if title not in not_own_page_titles:
				not_own_page_titles.append(title.strip())


	#now identify own-page events that are on 
	for e in e_deck:

		#remove punctuation
		title, url = harmonise_title_url(e)

		# if title on two pages: own_page and not own_page
		# remove from own_page
		# case: title on listings & own page (same date & diff date)
		# b/c we picked on listings page first
		# on own_page same event/same date is scrapped as duplicate
		# however if on own_page and we have reverse Trav
		# eg in sidebar for instance
		# it won't have been scraped and we end up with wrong date
		# by scrapping own-page we keep to correct Trav from listings page 
		if title in not_own_page_titles:

			if 'own_title' not in urls[url].keys(): continue
			
			if urls[url]['own_title'] != '':

				if urls[url]['own_title'] == title:
					#keep event on website/exhibitions
					#delete event on website/this-exhibition
					to_delete.append(e)
					print('.'*6 + ' rm duplicate on own-page >',
								e.title.title()[:40])

				else:
					#event title = another-exhibition but is on a url
					#that's set up for this-exhibition
					#nb. this means if nowhere else then we lose it
					#possible if it's a lecture/preview for this-exhibition
					to_delete.append(e)
					print('.'*6 + ' rm b/c page already has own title', 
							e.title.title()[:40])
					print('.'*9 + ' this page >', url)
					print('.'*9 + ' this page title >', urls[url]['own_title'])

			else:
				pass

		elif url in not_own_page_titles:
			#url is actually a title but the title taken from url
			#does not match that from not_own_page_title
			#here url = website/this-exhibition-name
			#but title picked up is this-exhibition-name-by-artist
			#whereas on website/exhibitions title picked up = this-exhibition
			#so the titles don't match but url matches title on listings page
			to_delete.append(e)
			print('.'*6 + ' rm b/c title picked up elsewhere >',
					e.title.title()[:40])

	#delete unwanted
	for to_ in to_delete: 
		e_deck.remove(to_)

	return e_deck


def scrub_events_1(e_deck):
	''' delete invalid and existing events '''

	#existing events
	existing = Event.objects.filter(evt_end__gte=G.today)

	#some more deletes
	to_delete = [] #reset
	inval_title = ['cancelled','postponed','moved']
	for e in e_deck:

		exists, done = False, False

		date_beg = e.date_beg
		date_end = e.date_end
		ven_ref = e.ven_ref
		tme_beg = e.time_beg
		descr = e.descr.lower()
		title = strip_text(e.title.lower(),'multi')
		
		#if invalid
		if any(i in e.title.lower() for i in inval_title):
			if e not in to_delete: 
				to_delete.append(e)
				print('.'*6 + ' rm invalid >',e.title[:40])
				continue

		#case: date_beg > today+360 and date_end was forced to +360
		if date_beg > date_end:
			if e not in to_delete: 
				to_delete.append(e)
				print('.'*6 + ' rm date_beg > date_end >',e.title[:40])
				continue

		#case: date_beg > today+360 and date_end was forced to +360
		if date_beg > G.today.date()+datetime.timedelta(days=360):
			if e not in to_delete: 
				to_delete.append(e)
				print('.'*6 + ' rm date_beg > date+360 >',e.title[:40])
				continue

		#if already an existing event: using end_date as dates with
		#'until' where start_dte is set to today throws using start_date
		#also use time in case same evt same dte repeated diff times eg films

		#get existing events for venue and compare to event nam
		ven_existing = existing.filter(evt_end=date_end,tme_beg=tme_beg,
									ven_ref=ven_ref)

		ven_existing = [evt_tag_title(e.event) for e in ven_existing]

		nam = [title]
		if ':' in title: 
			nam.extend(title.split(':'))
		nam = [evt_tag_title(n) for n in nam]
		nam = set(nam)

		for n in nam:
			if n in ven_existing:
				exists = True
				break

		# or check if some words in title exist in an existing event 
		# to avoid set(nam) | set(ven..) using individual chars in str
		# split - so can compare whole words
		if not exists:
			for n in nam:
				n = n.split()
				for v in ven_existing:
					v = v.split()
					if len(set(n) & set(v)) > 3:
						exists = True
						break

		if exists: 
			to_delete.append(e)
			print('.'*6 + ' rm existing >',e.title.title()[:40])
			continue

	#delete unwanted
	for to_ in to_delete: 
		e_deck.remove(to_)

	return e_deck


def scrub_events_2(e_deck,doc_dict,org,metas,tags):
	''' scrub event descriptions '''

	#some descrips are actually for the next event down
	#case: Title1/Descr1/Date1 Title2/Descr2/Date2
	#b/c Descr is Trav Down, Descr2 is picked for Date1
	#Here we'll identify where the Trav Down has gone through a Title2
	#before recahing the Descr set for Event1. We'll annul this Descr

	#first, create a long text of all titles to check against
	#we do this b/c a simple is this doclist line in titles list won't work
	#as we may have an entry Event_Title1:Event_Title2 eg Artist Name:Exh Title
	#and here a doclist line that matches Evemt_Title1 won't be found
	#by using a long string instead of all the titles, we'll be able to match

	#collate titles and urls
	titles, descrips = collate_lists(e_deck)

	long_title = ''
	for t in titles: long_title += t

	ind = 0

	for e in e_deck:

		ind += 1
		step = 1

		proto = False
		title = strip_text(e.title,'multi')
		descr = e.descr
		descr_ = descr.strip('.?!')
		index = e.index #where date is in doclist

		# get correct doclist for this event
		url = e.url
		doclist = doc_dict[url]['doclist']

		print('\n')
		print(ind, title)
		print('-'*40)

		print(100,'descr > ',descr)

		# prep - blank any descr in title
		if descr != '':

			if title == descr:
				descr = ''
				print(102,'rm descr b/c same as title')

			elif descr in title:
				
				title = title.replace(descr,'')
				title = strip_chars(title,ignore_pos_links=False)
				
				if len(title) <= 2: #unlikely to be a real title 
					e.title = 'x'
					e.descr = ''
					print(103,'ABORT: scrap event as title too short >',title)
					continue

				else:
					print(105,'rm descr from title >',title)
					
				# replace new title in doclist and long_title
				long_title = long_title.replace(e.title,title)
				i = doclist.index(e.title)
				if i != -1: doclist[i] = title

			
		# rest of function only applies to Trav Up
		if e.trav == 'down':
			e.title = title
			e.descr = descr
			print(191,'final title >', e.title)
			print(192,'final descr >', e.descr)
			print(199,'SKIP b/c Trav down')
			continue


		if descr == '':
			if ':' in title:
				title_ = title.split(':')
				descr = title_[-1].strip()
				print(210,'no descr but title has : may incl descr')
				print(211,'pos descr from title >',descr)
				
				try:
					#only valid if line exists in doclist
					#else title already came with the colon
					doclist.index(descr)
					proto = True
					if is_descr(descr):
						e.descr = descr
						title = strip_chars(title_[0].strip())
						e.title = title
						print(212,'passes descr test >',descr)
						print(213,'amended title >',title)
						continue

					else:
						print(214,
							'fails descr test - leave descr blank')
					
				except:
					print(215,'descr not found in doclist - leave descr blank')
					
			else:
				try: #in case index-3 is out of range
					if doclist[index-3].lower() == title:
						#so likely of the type Tit/Desc/Dte nb Dte=index-1
						descr = doclist[index-2].lower()
						#b/c now testing up instead of down
						step = -1
						print(216,'may be Title/Descr/Date - go trav up')
				except:
					pass


		if descr != '':

			try:
				descr_index = doclist.index(descr)
				print(227,'docline test range:', index, descr_index+1)
			except:
				e.descr = ''
				print(228,'pos descr not in doclist - keep title, blank descr')
				continue

			
			if not is_descr(descr):
				descr = ''
				print(229,'descr fails - set to blank')

			else:

				if index > descr_index and step == 1:
					print(230,'cannot test as range inverted')
					continue

				elif step == -1:
					#move everything back one
					index += -1
					descr_index += -1

				elif index == descr_index:
					#descr may have been another title
					#rather tha the descr line below it in Tit/Des/Dte
					#extend range so for loop works
					descr_index += 1 

				#now go through doclist lines between date and descr
				for i in range(index, descr_index+1, step):

					print('-'*10)
					print(330,'test [',i,']:',doclist[i])

					if G.img_linker in str(doclist[i]).lower():
						print(340,'Pass > img link')
						continue
					
					if doclist[i] in long_title:
						# blank descr as we've crashed through another title
						# case: T1 \n Dte2 \n T2 \n Desc1 \n Dte2 \n Desc2
						# Desc1 which belongs to T2 is picked up for T1
						
						print(440,'oops, found a title')

						if descr in title:
							title = re.sub(descr,'',title,flags=re.I)
							title = strip_chars(title)
							if len(title.strip()) <= 2: title = 'x' 
							print(442,'rm descr from title >',title[:40])

						descr = ''
						print(445,'blank descr and exit loop')
						break

					elif step == -1:
						
						# here potential Title/Descr/Date case
						new_descr = descr
						print(800,'a reverse loop: switch test')
						print(801,'potential new descr > ', new_descr)
						
						if is_descr(new_descr):
							e.descr = new_descr
							print(810,'passes')
						else:
							print(815,'fails')
						
						#only checking the suggested descr
						break

					else:

						# stop if we reach the description
						if doclist[i] == descr:
							print(910,'reached descr; left as is')
							break

						else:
							# test the line; if line is_descr use that and exit
							# i.e. abandon whatever orig or changed descr
							if is_descr(doclist[i]):
								descr = doclist[i]
								print(920,'use this test descr:',descr)
								break
							
							else:
								print(930,'new pos descr fails')

		else:
			print(990,'no descr picked up')

		e.title = title
		e.descr = descr
		print(991,'final title >', title)
		print(992,'final descr >',descr)

	return e_deck


def scrub_events_3(e_deck):
	''' scrub other descriptions from event '''

	# with Trav=up <title1>\n<date1>\n<descr1>\n<title2> ...
	# can leave title2 to become <descr1:title2> if len descr1 is short
	# test if descr1 in <descr1:title2> is a descr for something else
	# remove if it is
	
	# collate titles and urls
	titles, descrips = collate_lists(e_deck)

	for e in e_deck:

		descr = e.descr.lower()
		title = strip_text(e.title.lower(),'multi')

		print('\n')
		print(title[:40])
		print('-'*40)

		# any other description
		for d in descrips:
			if d in title:
				# using 'in' and not re.search as descr of type
				# "blah | blah | i" will match the i in a title 
				print('.'*6 + ' another descr is in title >',d)
				t = strip_chars(re.sub(d,'',title))
				if len(t) < 2:
					title = 'x'
				else:
					title = t
				e.title = title.strip()
				
				print('.'*6 + ' rm the descr from title >',title)
				break

	return e_deck


def scrub_events_4(e_deck):
	''' remove invalid events eg cancelled '''

	#copy descr to like events in case missed
	descr_dict = {}
	for e in e_deck:
		title = e.title 
		if title not in descr_dict.keys():
			if e.descr != '':
				descr_dict[title] = e.descr
	
	for e in e_deck:
		title = e.title 
		if title in descr_dict.keys() and e.descr == '':
			e.descr = descr_dict[title]

	return e_deck

def refine_tagging(e, meta_prob, metas, tags):
	''' adjustments to tagging esp if tags don't fit meta '''

	def clean_tags(tags):
		tags = strip_chars(tags)
		while ';;' in tags:
			tags = re.sub(';;',';',tags)
		while '; ;' in tags:
			tags = re.sub('; ;',';',tags)
		while ';-' in tags:
			tags = re.sub(';-',';',tags)
		tags = tags.strip(';')
		return tags

	
	# metas with valid 'tour' tags NB music not in there
	tours = ['outdoor','art','sights','other']

	# tags we do not want that may have been smart tagged
	invalid = ['live','event','club','night','short','star','out']

	# remove these tags if this meta_tag 
	scrub_tags = {
		'spoken':('talk','conversation','lecture','discussion','word'),
		'music':('fan','musicians','musician','vocal','energy','play',
			'performance','icon','legend','time','musical','tour','dance'),
		'comedy':('theatre','comedian','comic'),
		'workshop':('course',),
		'kids':('children',),
		'clubs':('music','art','dance'),
		'cinema':('film','screening'),
		'theatre':('star','fan'),
	}

	meta = e.meta_tag.lower()
	tags = e.tags

	if not tags: tags = ''

	if meta not in tours:
		tags = re.sub(r'\btour\b','',tags)

	if meta != 'art':
		tags = re.sub('exhibition','',tags)

	if meta != 'music':
		tags = re.sub('house','',tags)
		tags = re.sub('rock','',tags)

	if meta not in ['science',]:
		tags = re.sub('space','',tags)
		tags = re.sub('stars','',tags)

	if meta in tags:
		tags = re.sub(meta,'',tags)

	# specific meta_tags
	for scrub, tees in scrub_tags.items():
		if meta.lower() == scrub:
			for t in tees:
				#and for simple plurals
				tags = re.sub(r'\b'+t+r's*\b','',tags,flags=re.I)
			break

	# remove invalid tags
	# eg 'live' b/c 'music' was re.subbed in 'live music'
	for i in invalid:
		tags = re.sub(r'\b'+i+r'\b','',tags,flags=re.I)

	# if art+exhibition stuff
	if meta == 'art':

		if 'exhibitions' in tags:
			tags = re.sub('exhibitions','',tags)

		if e.date_beg == e.date_end:
			if 'exhibition' in tags:
				tags = re.sub('exhibition','',tags)
		
		if e.date_beg != e.date_end:
			if 'exhibition' not in tags and 'Exhibition' not in tags:
				tags += ';exhibition'

		# use default Org admission
		if 'exhibition' in tags:
			if not e.free:
				e.free = e.org.free

	e.tags = clean_tags(tags)
	return e

def descr_tagging(e, meta_prob, metas, tags):
	''' set tags based on description '''
	
	if e.descr == '': return e

	max_tags = 6
	gotten = ''

	try:
		gotten = e.tags.lower()
	except:
		pass

	gotten = re.sub(r';{2,}',';',gotten)
	gotten = gotten.strip(';')

	#we get tags from title and description
	sources = [e.title, e.descr]


	for src in sources:
		for t in tags:
			t = t.lower().strip()
			if t == e.meta_tag.lower(): continue
			if t != '' and t not in gotten and len(t) > 2:
				if len(re.findall(r';',gotten)) >= max_tags: 
					break
				if re.search(r'\b'+t+r'\b',src.lower()):
					gotten += ';'+t

	gotten = gotten.strip(';')
	e.tags = gotten

	#adjust metas based on description and update tags
	for key, val in meta_prob.items():
		
		#old: to del
		#if any(re.search(r'\b'+v+r'\s*\b',e['descr'],flags=re.I) 
		#			for v in val):
		
		#using \W to catch paren case: (15) and not blah 15 blah
		if any(re.search(r'\W'+v+r'\W',e.descr,flags=re.I) 
					for v in val):
			old_meta = e.meta_tag

			if old_meta.lower() != key.lower():

				e.meta_tag = key

				#scrub from tags if appropriate
				curr_tags = e.tags.lower()
				if re.search(r'\b'+key+r'\s*\b',curr_tags,flags=re.I):
					curr_tags = re.sub(r'\b'+key+r'\s*\b','',curr_tags,
									flags=re.I)
					curr_tags = re.sub(';;',';',curr_tags)
					curr_tags = curr_tags.strip(';')
					e.tags = curr_tags

	return e

def title_tagging(e, meta_prob, metas, tags):
	''' set tags based on title '''
	
	title = e.title
	titled = title.split()

	for meta in meta_prob.keys():
		if any(re.search(r'\b'+m+r's*\b',title,flags=re.I) 
				for m in meta_prob[meta]):
			meta = Meta_Tag.objects.get(meta_tag__iexact=meta)
			e.meta_tag = meta.meta_tag
			break

	e_tags = e.tags
	if e_tags is None: e_tags = ''
	for t in titled:
		if t in tags and \
			t not in e_tags.lower() and \
			t != e.meta_tag.lower():
			if e_tags != '' and e_tags is not None:
				e_tags += '; ' + t
			else:
				e_tags = t

	e_tags = strip_chars(e_tags,ignore_pos_links=False)
	e.tags = e_tags

	return e

def url_tagging(e, meta_prob, metas, tags):
	''' set tags based on url '''
	
	meta_done = False
	club_time = 22 #set to 10pm
	url = e.url

	#if still default then try url tagging
	if any(re.search(r'\b'+m+r's*\b', url, flags=re.I) for m in metas):
		for m in metas:
			if m != 'event':
				if re.search(r'.*/'+m+r'\s*', url, flags=re.I):
					e.meta_tag = m
					break
	return e

def datetime_tagging(e, meta_prob, metas, tags):
	''' meta based on datetime '''

	#esp for art: if single day then likely spoken
	if e.meta_tag == 'art':
		tags = e.tags
		if e.date_beg  == e.date_end:
			e.meta_tag = 'spoken'
			tags = tags.replace('spoken','')
			tags = tags.replace('exhibition','')
			print(' '*9 + ' 1-day Art event > use Spoken')
			if 'art' not in tags:
				tags += ';art;'

		else:
			if 'exhibition' not in tags:
				tags += ';exhibition;'

		e.tags = tags #reset

	#clubs based on time
	club_time = 22 #set to 10pm
	tme = e.time_beg.split(":")[0]
	if int(tme) >= club_time:
		e.meta_tag = \
			Meta_Tag.objects.get(meta_tag='Clubs').meta_tag
	
	return e

def evt_tag_title(txt):
	''' create title for Tagged Events '''
	txt = re.sub(r'\W',' ', txt) #remove puncts,non-words; format in Tagged_E
	txt = re.sub('  ',' ', txt) #convert dbl spaces to single
	txt = strip_common(txt)
	txt = strip_varnish(txt)
	txt = strip_chars(txt)
	txt = txt.strip()
	return txt

def smart_tagging(e_deck, org):
	''' set tags based on event attributes '''
	
	Prior_Tags = Tagged_Events.objects.all()
	Prior_Titles = values_list['prior']

	metas = Meta_Tag.objects.filter(primary=True)
	metas = list(metas.values_list('meta_tag',flat=True))
	metas = [m.lower() for m in metas]

	Tags = Tag.objects.all().distinct()
	tags = list(Tags.values_list('tag',flat=True))

	#we won't go through everything
	max_sample = min(1000000,len(tags))
	tags = list(random.sample(tags,max_sample))

	for e in e_deck:

		url = e.url.lower()
		org = Seed.objects.get(seed=org)

		print('-'*40)
		print('.'*6, e.title)

		#first set default meta tag
		e.tags = org.gen_tags
		e.meta_tag = org.meta_tag.meta_tag

		#next override above with saved tags if applicable
		e_x = evt_tag_title(e.title)
		if e_x in Prior_Titles:
			
			e_ = Prior_Tags.get(event=e_x)
			#overwrite tags with any prior
			e.meta_tag = e_.meta
			e.tags = e_.tags
			print(' '*9,'prior meta/tags (Full) >',e_.meta)
			if e.img in ['',None]:
				e.img = e_.img

		else:
			#test if some words in a Prior
			#long enough to catch proper words but not too long to miss names
			#weak assumption: for improper caught no X same words in diff evts
			min_words, min_chars = 3, 4 #eg 3 similar words of min 4 chars each
			az = re.sub(r'\d','',e_x)
			az = az.strip()
			az = az.split(' ')
			az_ = [a for a in az if len(a) >= min_chars]
			if len(az_) >= min_words: #at least two words
									
				Pr = Prior_Tags.filter(functools.reduce(operator.or_,(
						Q(event__iregex=r'\y'+a+r'\y') for a in az_)))

				for e_ in Pr:
					e_split = e_.event.split()
					mutual = set(e_split) & set(az_)

					if len(mutual) >= min_words:
						#overwrite tags with any prior
						e.meta_tag = e_.meta
						e.tags = e_.tags
						print(' '*9,'prior meta/tags (Part) > ',e_.meta)
						if e.img in ['', None]:
							e.img = e_.img
						break

		#finally adjust tags based on attributes; order matters
		funcs = \
			[title_tagging, descr_tagging, datetime_tagging, 
				url_tagging, refine_tagging]

		for func in funcs:

			org = e.org
			orig_meta = e.meta_tag
			orig_tags = e.tags
			
			func_name = func.__name__.split('_')[0]
			
			#skip descr_tagging if no description
			if func_name == 'descr' and e.descr == '': 
				continue

			#if still default meta then try url tagging; else skip
			if func_name == 'url':
				if orig_meta != org.meta_tag.meta_tag:
					continue

			#get any new values if appropriate 
			e = func(e, G.meta_prob, metas, tags)
			new_meta = e.meta_tag
			new_tags = e.tags
			if orig_tags == None and new_tags == '': new_tags = None
		
			#print
			if new_meta != orig_meta: print(' '*9,func_name,'meta > ',new_meta)
			if new_tags != orig_tags: print(' '*9,func_name,'tags > ',new_tags)

		e_tags = e.tags
		e_tags = strip_chars(e_tags)
		e.tags = e_tags.strip()

	return e_deck

def smart_time(e_deck, org):
	''' set event time based on context '''

	valid_metas = ['art','music','theatre','clubs','comedy']

	#existing events
	existing = Event.objects.filter(evt_end__gte=G.today)

	for e in e_deck:

		time = e.time_beg
		meta = e.meta_tag.lower()
		e.time_found = False

		#if existing but diff dates, use existing time if no e|time
		#case: same event eg club night; yoga class etc 
		try:
			e_ = existing.get(event__iexact=e.title, ven_ref=e.ven_ref)
			if e.tme_beg=='00:00' and e_.tme_beg != '00:00':
				e.time_beg = e_.tme_beg
		except: pass

		#only where no times found
		if time == None or time == '00:00':

			if meta in valid_metas:
				seed = Seed.objects.get(seed=org)
				e.time_beg = seed.tme_beg
				print('.'*6 + ' using default time',seed.tme_beg,
						'for ',e.title[:40])

		else:
			e.time_found = True
			print('.'*6 + ' time found:',time,'for ',e.title[:40])

		#set date_end to date_beg if time end is early morning
		#eg late night gigs/clubs		
		if e.time_end != '00:00':
			if e.time_end < '06:00':
				e.date_end = e.date_beg
				print('.'*6 + ' set date_end to date_beg as ends early a.m')

	return e_deck


def restack_images(e_deck):
	''' match images to scrape using matched strings '''

	ext = ['jpg','jpeg','svg','tiff','png','gif','bmp']
	images, queries = {}, {}
	metas = values_list['metas']
	common_ = ['tour','special guests','special guest','guests','guest',]
	common_.extend(G.conjunctions) 
	common_.extend(G.descr_like)
	common_.extend(metas) 

	#collate images and individual words
	for e in e_deck:
		img = e.img
		if img and img.strip() != '':
			if img not in images.keys():	
				img_ = img.lower()
				m = re.search(r'(.*/)',img_)
				if m:
					img_ = img_[m.span()[1]:]
					for s in G.ignore_starts: #holds non alpha_nums
						img_ = img_.replace(s,' ')
					img_ = re.findall(r'([a-zA-Z]+)',img_)
					if img_:
						img_ = [i for i in img_ if len(i) > 1 and 
								i not in ext and i not in common_]
						images[img] = img_
	
	print('.'*6, 'images found')
	for k in images:
		k = k[re.search(r'(.*/)',k).span()[1]:]
		print('.'*2, k)

	#match image to query
	for e in e_deck:

		found = False
		
		#use if more than x number of words are common
		min_mutual = 2
		
		#collect individual non-common words from title
		title = e.title.lower()
		for c in common_:
			title = re.sub(r'\b'+c+r'\b','',title)
		title_ = title.split()
		title_ = [t for t in title_ if len(t) > 1]

		#get acronym of title
		acronym = ''
		acronym_ = [t[0] for t in title_]
		for a in acronym_: acronym += a
		if len(acronym) < 3: acronym = ''

		#set conditions
		if len(title_) <= 2: min_mutual = 1
		orig, new = e.img, None
		e.img = ''

		#assign appropriate images to events
		for k, val in images.items():

			#if more than min words from img|val in title
			mutual = set(title_) & set(val)
			if len(mutual) >= min_mutual:
				found = True
			elif acronym in val or any(v in acronym for v in val):
				#if acronym of title in img|val
				found = True
	
			if found:
				e.img = k
				new = k
				break

		#print
		o, n = '--', '--'
		if orig != new:
			
			if orig: #ie != None
				o = re.search(r'(.*/)',orig)
				if o: o = orig[o.span()[1]:]
			
			if new:
				n = re.search(r'(.*/)',new)
				if n: n = new[n.span()[1]:]

			print('-'*40)
			print('{:<6}'.format('e'), e.title)
			print('{:<6}'.format('orig'), o)
			print('{:<6}'.format('new'), n)

		else:
			if orig:
				o = re.search(r'(.*/)',orig)
				if o: o = orig[o.span()[1]:]
			print('-'*40)
			print('{:<6}'.format('e'), e.title)
			print('{:<6}'.format('img'), o)

	return e_deck

def set_closed_days(e_deck, org):
	''' set closed days for venue - mainly theatres '''

	long_days = G.long_days

	for e in e_deck:

		every = False
		everys = []
		title = e.title.lower()
		ev = e.every
		meta = e.meta_tag.lower()

		if ev or meta in ['theatre','workshop','classes','meetups',
							'social','kids']:

			if ev:
				#compile days - normally long
				ev = ev.lower()
				for d in long_days:
					if d in ev:
						everys.append(d[:2])
						every = True

			#record not open days
			if every:
				for d in long_days:
					if d[:2] not in everys:
						e.closed += d[:2]+','
					
			else:

				date_beg = e.date_beg
				date_end = e.date_end
				
				if (date_end - date_beg).days > 6:
				
					if meta == 'theatre':
						ven_ref = e.ven_ref
						seed = Seed.objects.get(seed=org)

						closed = seed.closed_days
						if closed:
							closed = closed.lower()
							to_close = ''
							if 'mo' in closed: to_close += 'Mo,'
							if 'tu' in closed: to_close += 'Tu,'
							if 'we' in closed: to_close += 'We,'
							if 'th' in closed: to_close += 'Th,'
							if 'fr' in closed: to_close += 'Fr,'
							if 'sa' in closed: to_close += 'Sa,'
							if 'su' in closed: to_close += 'Su,'
							e.closed = to_close
						
						else: # set closed to a default Sun and Mon
							e.closed = 'Mo,Su'

				
					# for metas like classes, these often happen on a set day
					# if start/end weekday is the same then close other days

					# these have closed/open defined in model
					excl = ['theatre','art']
		
					if meta not in excl:
					
						date_beg_day = date_beg.weekday()
						date_end_day = date_end.weekday()

						if date_beg_day == date_end_day:
							to_close = ''
							for i in range(len(long_days)):
								if i != date_beg_day:
									to_close += long_days[i][:2]+','
							e.closed = to_close

	return e_deck


class event:
	def __init__(self, title):
		self.title = title
		self.tags = ''
		self.meta_tag = 'Event'
		self.closed = ''

def class_sort(class_list,attr_getter):
	''' sort class items by attribute '''
	return sorted(class_list,key=operator.attrgetter(attr_getter))


def get_events(org,url,ven_ref,doclist,first_up,e_deck,dates,failed_dates,failed_times):
	''' compile events '''

	tomorrow = (G.today + datetime.timedelta(days=1)).date()
	furthest_date = (G.today + datetime.timedelta(days=360)).date()
	times, dates_done = [], []
	max_events = 100 #max to collate for any one venue
	descr = ''
	anchor, title_anchor = 0, None
	furth_date_found = G.today.date()
	early_thresh = 21 #new dates must be no earlier than prev ones

	i = 0
	if dates and len(e_deck) < max_events:
		for _date in dates.keys():

			i += 1

			#######################################
			print('\n')
			print(str(i),'... processing',_date)
			print('...... url:',url)
			print('\n')
			#######################################

			date = dates[_date]['date']
			orig_date = dates[_date]['orig_date']
			anchor = dates[_date]['index']
			time_beg, time_end = "00:00", "00:00"
			
			##standardise dates - NB we don't want dateline here
			cleaned_date = get_full_dates(date)
			##################################
			print('{:<6}'.format('raw'),date)
			print('{:<6}'.format('clean'),cleaned_date)
			print(url)
			##################################

			#if we can't then move on
			if None in cleaned_date:
				##################################
				print('>>> SCRAP: date clean fail')
				##################################				
				continue

			start_date = convert_text_date(cleaned_date[0])
			end_date = convert_text_date(cleaned_date[1])

			#abort if convert function failed
			if start_date == False or end_date == False:
				##################################
				print('>>> SCRAP: date conversion fail')
				##################################	
				continue

			#some webpages have repeated events at page bottom
			#these can have diff Trav leading to false +ves for events
			#so we'll track where new dates are earlier than prev dates
			#to allow for pages where evnts are slightly jumbled up
			#we'll have a threshold for how much earlier
			#also: we consider only start = end to avoid cases of 
			#events ... then a long-running one eg exh 2017-2019 etc
			#also: if suspected then just skip and move on to next 
			#also: skips exh where start dates could be all over the place
			if start_date == end_date:
				
				if furth_date_found == G.today: #first one
					furth_date_found = start_date

				else:
					days_diff = (start_date - furth_date_found).days

					if days_diff >= 0: #normal
						furth_date_found = start_date
					
					else:
						if abs(days_diff) < early_thresh:
							#meets threshold; allow
							pass
						else:
							#fails threshold;

							#one more test: only skip if dates
							if start_date in dates_done:
								#assume everything later is old/repeat
								##################################
								print('>>> SKIP: suspect repeat or old dates')
								##################################	
								continue


			#abort if end date < tomorrow - ignore if Tests eg Regression Tests
			if org.seed != 'Tests':
				if end_date < tomorrow: 
					##################################
					print('>>> SCRAP: end date < tomorrow')
					##################################	
					continue

			#abort if end_date > start_date
			if start_date > end_date: 
				failed_dates.append((date,':::',url))
				##################################
				print('>>> SCRAP: start date > end date')
				##################################	
				continue

			#only go up to a year
			if end_date > furthest_date: 
				##################################
				print('>>> SCRAP: end date > +360d')
				##################################	
				continue

			# nb index is 1-base but we need anchor zero-index doclist
			anchor = dates[_date]['index'] - 1

			# we need an event title else move on	
			title = get_event_title(date,anchor,
							doclist,first_up,url,org)

			if not title or title.strip() == '' or len(title.strip()) < 2: 
				continue

			# get description	
			descr = get_event_descr(date,anchor,doclist)

			# get event time(s)	
			time_beg, time_end = '00:00', '00:00'
			time = get_event_time(date, anchor, doclist)
			if time:
				if ',' in time:
					time = time.split(',')
					time_beg = time[0].strip()
					time_end = time[1].strip()
				else:
					time_beg = time.strip()

			# get image	
			img_link = get_event_image(date,anchor,doclist,first_up)

			# get if free admission
			is_free = False
			is_free = get_event_free(date,anchor,doclist)


			# get if every X-day 
			every = None
			date_txt = doclist[anchor-1]
			reg_marker, reg_mark_end = G.reg_marker, G.reg_mark_end
			if reg_marker in date_txt:
				a = date_txt.find(reg_mark_end)
				every = date_txt[len(reg_marker):a]

			#######################################
			print('...... create event and add to deck')
			#######################################

			#populate e_deck
			e = event(title)
			e.org = org
			e.index = dates[_date]['index']
			e.descr = descr
			e.url = url
			e.ven_ref = ven_ref
			e.date = date
			e.date_beg = start_date
			e.date_end = end_date
			e.every = every
			e.time_beg = time_beg
			e.time_end = time_end
			e.free = is_free
			e.img = img_link
			if first_up:
				e.trav = 'up'	
			else: e.trav = 'down'

			e_deck.append(e)

			#record date done
			dates_done.append(start_date)

			len_t, dots = len(title), ''
			if len_t > 25: dots = '...'
			print('\n')
			print('>>> ADD ',title.upper()[:25]+dots,'on',start_date,
					'to events deck')
			print('-'*20)
			print(e.__dict__)
			print('\n\n')

	return e_deck,failed_dates,failed_times


def get_webpages(org,seed_url,js_site,brow,real_org):
	''' compile href urls in seed site and store text in pages'''

	if 'http' not in seed_url and 'www.' in seed_url:
		seed_url = 'http://'+seed_url

	_title = ''	
	make_list, done_list = [seed_url], []
	failed_req, failed_con, unicode_errors = [], [], []
	doc_dict = defaultdict(dict) #store page texts

	tries, try_limit = 1, 10 #loops to gather urls: index, max to do
	if js_site: 
		try_limit = 6 #too many creates already opened session errors
	if org == 'Tests': 
		try_limit = 1 #avoid running eg href=#mobile
	
	q_seen, q_stop = 0, 100 #urls in queue, max queue length
	ad_infinitum, finite_limit = 0, 20

	start = datetime.datetime.now()
	start_str = start.strftime("%H:%M")
	so_far, time_limit = 0, 10

	#get the site url - we'll check if in page url
	#to keep scrapes within website. We want the bit after www
	#because some events sites eg theatres have event decsriptions
	#on ticket pages eg https://tickets.site_url/blah which we'll miss
	#if looking for https://www.site_url/blah
	base_url = base_venue_url(seed_url)

	#revert back if more than one seed shares base
	#using base here would mean picking up seed events
	#multiple times when other seeds with same base are run
	S = Seed.objects.filter(seed_url__istartswith=base_url)
	if len(S) > 1: m = seed_url

	m_ = re.findall(r".*www\.(.*)", base_url)
	if m_: site_url = m_[0] #www found
	else: site_url = base_url #no www so we are fine

	#for art galleries, normally all exhibitions are on an 'exhibitions' page
	#with a separate page for each exhibition also, no need to trawl these
	#so limit try_limit if exhibitions in seed_url
	if 'exhibitions' in seed_url: try_limit = 1

	#if testing, limit to first page
	glob = globals().items()
	for g in glob:
		if g[0] == '__name__' and g[1] == '__main__':
			try_limit = 1

	#loop through urls list while list is non-empty and until queue limit
	#list wll be extended with new urls found until q_stop
	while len(make_list) > 0 and tries <= try_limit and so_far < time_limit:
		this_url = make_list[0]
		
		# skip if we've done this
		if this_url in done_list or \
			this_url + '/' in done_list or \
			this_url.rstrip('/') in done_list:
			make_list = make_list[1:]
			continue

		q_seen += 1

		#variables for status update stats
		queue = len(make_list)
		now = datetime.datetime.now()
		so_far = (now - start).seconds
		mean = so_far/tries
		so_far = round(so_far/60,1)

		to_end = min((try_limit-tries),queue) #how many more to go
		to_end = round((mean*to_end)/60,1) #est mins to finish
		end = now + datetime.timedelta(minutes=to_end)
		end_str = end.strftime("%H:%M")

		duration = so_far + to_end
		dur_hr, dur_min = int(duration // 60), round(duration % 60)
		dur_str = str(dur_hr)+' h  '+str(dur_min)+' min'

		q_fin = round((mean*queue)/60,1) #estimated minutes to end of queue
		potential = tries + queue
		try_pct = int(round((tries/min(potential,try_limit))*100))

		#abort if in_queue=1 repeatedly
		#possible continuous event calendar request for next day ad infinitum
		#so we track how many of these ad infinitum request we are getting
		if queue == 1: ad_infinitum += 1

		#######################################################################
		print('\n:: {:<} | {}%   ::queue|max: {} | {}'.format(
				tries,try_pct,queue,q_seen))
		print(':: {:<8}{:<11}{:<11}{:<11}{:<10}{:<10}'.format(
				'start','so far','left','to-q','est end','est duration'))
		print(':: {:<8}{:<11}{:<11}{:<11}{:<10}{:<10}'.format(
				start_str,str(so_far)+' min',str(to_end)+' min',
				str(q_fin)+' min',end_str,dur_str))
		print('-'*75)
		#######################################################################

		#get page text; nb. output is a bytes object	
		_text = read_url(this_url,js_site,brow)

		if isinstance(_text,bytes):
			_text = _text.decode('utf-8',errors='ignore')

		if _text=='' or _text=='failed_request':
			failed_req.append(this_url)
			done_list.append(this_url), make_list.remove(this_url)

		elif _text=='failed_connect':
			failed_con.append(this_url)
			done_list.append(this_url), make_list.remove(this_url)

		elif _text=='timed out' or _text=='socket timeout':
			failed_con.append(this_url)
			done_list.append(this_url), make_list.remove(this_url)
			continue

		elif _text=='unicode error':
			failed_con.append(this_url)
			done_list.append(this_url), make_list.remove(this_url)
		
		else:
			if tries == 1 and org != 'Tests':
				#org != Tests so scrape.html not overwritten 
				done_list.append(this_url) #add to list
				#save the first url as we may need this for testing issues
				testscrape = base_dir+\
					'/scraper/templates/scraper/scrape.html'
				
				#encode to write to file and then decode to continue
				_text = _text.encode()
				with open(testscrape, mode='w+b') as \
					 test_scrape: test_scrape.write(_text)
				_text = _text.decode()

			#treat as line break
			repl_line = ['<p>','<br>']
			for r in repl_line:
				_text = re.sub(r,'\n',_text)

			#next replace pure format tags with '' to avoid line breaks 
			#and tags that can end up as orphans
			repl_null = ['<strong>','</strong>','<em>','</em>',
				'<b>','</b>','<i>','</i>','<sup>','</sup>'
				'<p','<p>','</p>','<span','<span>','</span>',
				]
			
			for r in repl_null:
				_text = re.sub(r,' ',_text)

			#again with .replace as some r's e.g. 'p' not always subbed above
			for r in repl_null:
				try: _text = _text.replace(r,' ',_text)
				except: pass

			#replace strays with '\n'
			_text = re.sub('>','>\n',_text) #stray

			souped = BeautifulSoup(_text,'lxml')

			#collect urls now and extract text later to speed download time
			
			#change test environment url to org - allows url_tagging
			if org == 'Testing':
				this_url = Seed.objects.get(seed=real_org).seed_url
				make_list = []
				make_list.append(this_url)

			doc_dict[this_url]['souped'] = souped #to get urls below
			
			###############################################
			print("...... searching webpage for urls")
			###############################################
			
			tag_num = 1
			print('search >',seed_url)

			if print_urls == 'y':
				print('{:<4}'.format(tag_num))

			for tag in souped.find_all('a',href=True):

				tag_num += 1

				if print_urls == 'y':
					print('\n')
					print('{:<4}'.format(tag_num))
					print(tag)
					

				if 'http' not in tag['href']:
					tag['href'] = \
						urllib.parse.urljoin(seed_url, tag['href'])

				#stay within site
				full_len = len('http://www.') + len(seed_url) + 6 #6=buffer
				start_href = tag['href'][:full_len]

				#adjustments so site_url conforms to start_href
				if 'https:' in start_href and 'http:' in site_url:
					site_url = site_url.replace('http','https')

				if site_url[-1] == '/': site_url = site_url[:-1]

				if print_urls == 'y':
					print('site >',site_url)
					print('href >',start_href)
				
				if site_url[site_url.find('://')+3:] in start_href and \
					len(re.findall('www',start_href)) <= 1: 

					#ignore where seed is home/something and tag_href = home
					#we don't want the home as may have same event diff Trav 
					seed_path = urllib.parse.urlparse(seed_url).path
					#path may exclude cases where seed has '?=....'
					#but we wish to keep it all
					pos = seed_url.find(seed_path)
					seed_path = seed_url[pos:]

					seed_path = seed_path.strip('/')

					if len(seed_path) > 0: #there's a path
						if seed_path not in tag['href'].lower():
							if print_urls == 'y':
								print('ABORT > off topic')
								print('-'*40)
								print('seed path',seed_path)
								print('tag_href',tag['href'].lower())
							continue

					#ignore image/shopping/old/document links
					if tag['href'][:4] != 'http':
						if print_urls == 'y': print('ABORT > bad url')
						continue

					elif tag['href'].count('http') > 1:
						if print_urls == 'y': print('ABORT > a redirect url')
						continue

					elif any(is_not_valid_url(tag['href'],test) for \
						test in G.webpage_url_tests.keys()):
						if print_urls == 'y': print('ABORT > not valid')
						continue

					else:
						#add to url list only if conditions met
						if tag['href'] not in done_list and \
							tag['href'] not in make_list and \
							tries < q_stop and \
							ad_infinitum < finite_limit:
							make_list.append(tag['href'])
							if print_urls == 'y': print('ADD')
						else:
							if print_urls == 'y': print('ABORT > already done')

				else:
					if print_urls == 'y': print('ABORT > external href')
			
			done_list.append(this_url)
			make_list.remove(this_url)
			tries += 1

	return doc_dict, failed_req, failed_con, unicode_errors


def scrape_now(org,seed_url,**kwargs):
	''' scrape meta job and saves found events to database 
		this job is run from the admin page
		for testing - use the scraperx project
	'''

	min_para_len = 3 #min char length of sentence line to consider
	max_para_len = 199
	first_up, js_site = True, False
	doc_dict, e_deck = {}, []
	fails,failed_dates,failed_times = [],[],[]
	today = G.today.strftime("%Y_%m_%d_%H_%M_%S")
	doclist = []

	metas = values_list['metas']
	metas = [m.lower() for m in metas]
	tags = values_list['tags']
	tags = [t.lower() for t in tags]

	org_index, num_org, num_e = 1, 1, 0
	scrape_start = datetime.datetime.now()
	if 'num_org' in kwargs.keys():
		num_org = kwargs['num_org'] #nb. in admin.py
	if 'org_index' in kwargs.keys():
		org_index = kwargs['org_index'] #nb. in admin.py
	if 'scrape_start' in kwargs.keys():
		scrape_start = kwargs['scrape_start'] #nb. in admin.py
	if 'num_e' in kwargs.keys():
		num_e = kwargs['num_e'] #nb. in admin.py

	organiser = None
	if org == 'Testing':
		if kwargs['use_alt'] == 'y':
			organiser = Seed.objects.get(seed_url=kwargs['test_org'])
			first_up = organiser.title_up
	elif org == 'Tests':
		organiser = Seed.objects.get(seed_url='Tests')
		first_up = kwargs['first_up']

	else:
		organiser = Seed.objects.filter(seed_url=seed_url)[0]
		first_up = organiser.title_up

	#for sites requiring browser to render content
	js_site = organiser.js_site
	brow = organiser.browser
	ven_ref = organiser.ven_ref #for scrape.py saves

	############################################################
	a = datetime.datetime.now()
	print('\n')
	print('Org:',org_index,'/',num_org)
	print("="*75,'\n','Starting get_webpages: ', a,'\n')
	############################################################

	#get all href links on seed home page and souped tags
	doc_dict,failed_requests,failed_connects,unicode_errors = \
			get_webpages(org,seed_url,js_site,brow,organiser)

	############################################################
	b = datetime.datetime.now()
	print('\n',"="*75,'\n','Starting doclist: ', b,'\n')
	############################################################

	url_num = 1
	key_num = len(doc_dict.keys())
	for url in doc_dict.keys():
		############################################################
		c = datetime.datetime.now()
		print("="*75)
		print(str(url_num)+'/'+str(key_num)+': get soup for ', url,'\n')
		############################################################
		
		#copy over 'souped' as we may need to re-run get_doclist
		#if simple 'Obj = souped' then when souped is changed ed decomposed
		#it happens also to Obj; so copy.copy to avoid this 
		reserve_souped = copy.copy(doc_dict[url]['souped'])
		doclist = get_doclist(url_num, url, reserve_souped, seed_url,
								test_org=organiser)

		doc_dict[url]['doclist'] = doclist
		url_num += 1
		############################################################
		d = datetime.datetime.now()
		print("="*75)
		print('duration this url:', round((d-c).total_seconds(),1),'secs','\n')
		print('\n\n')
		print('{:<12}'.format('Seeds done'),org_index-1,'/',num_org,
				' | ','Events >>',num_e)
		print("="*75)
		print('{:<12}'.format('Job Start'),scrape_start.strftime('%H:%M'))
		
		job_dur = (d - scrape_start).total_seconds()/60
		job_so_far = int(job_dur)
		est_dur, est_end = 0, d
		dur_ = 'mins'
		org_dur = 60  #default in secs in case new venue
		if organiser.duration:
			org_dur = organiser.duration
		
		if num_org == org_index: #last one or only one in list
			est_dur = int(org_dur) + job_so_far*60
			est_end = scrape_start + datetime.timedelta(seconds=est_dur)
			dur_ = 'secs'
		
		else:
			if org_index == 1: #first one of many; org.dur is in secs
				est_dur = int(org_dur * num_org / 60) + 1
			else:
				# org_index(-1) b/c curr index main job hasn't started 
				est_dur = int(num_org/(org_index-1) * job_so_far) + 1
				
			est_end = scrape_start + datetime.timedelta(minutes=est_dur)

		print(	'{:<20}'.format(''),
				'So Far', job_so_far, 'mins', '|',
				'Est', est_dur, dur_, '|',
				'Left', (est_dur - job_so_far), dur_)
		print('{:<12}'.format('Est End'), est_end.strftime('%H:%M'))
		print("="*75)
		print('\n\n')
		############################################################

	#save dictionary of webpages
	#if doc_dict:
	#	#b/c B-Soup is non-JSON serializable
	#	del doc_dict[url]['souped']
	#	f_name = base_dir+'/dumped/scraped_webpages_'+today+'.json'
	#	with open(f_name, mode='w', encoding='utf-8') as save_file:
	#		json.dump(doc_dict, save_file)
	
	############################################################
	e = datetime.datetime.now()
	print('-'*75,'\n','Finished get_webpages: ', e)
	print('Duration get_webpages: ',(e-a))
	print('Number of webpages: ',len(doc_dict),'\n',"-"*75,'\n')
	############################################################

	#read url
	i = 0
	num = len(doc_dict.keys())
	
	for url in doc_dict.keys():

		i += 1
		print("="*75,'\n',i,'/',num,': getting events for ',url)

		t_now = time.time()	
		doclist = doc_dict[url]['doclist']

		##############################################
		print('\n\n')
		print('...... getting dates')
		##############################################
		dates = get_dates(doclist,url,ven_ref,date_patterns)

		##############################################
		len_dates = len(dates)
		if len_dates > 0:
			print('...... found',len_dates,'dates')
		print('\n')
		##############################################
			
		e_deck,failed_dates,failed_times = get_events(
			organiser,url,ven_ref,doclist,first_up,e_deck,
			dates,failed_dates,failed_times)

		##################################################################
		print('...... processed in:',round((time.time()-t_now),1),'secs')
		print('...... events found ',len(e_deck))
		##################################################################

	print('\n')
	print('Final events dictionary actions')
	print('-'*40)

	#sort by date
	print('\n')
	print('.. sort by date begin')
	e_deck = class_sort(e_deck,'date_beg')	

	#use tags from previous instances of event
	#note: assumes Event titles are unique
	print('\n')
	print('.. smart tagging')
	e_deck = smart_tagging(e_deck, organiser)

	#if time_beg == None or time_beg == "00:00":
	print('\n')
	print('.. smart time')
	e_deck = smart_time(e_deck, organiser)

	
	print('\n')
	print('.. scrub events')
	#remove duplicated events usually from same page
	#nb done before rm those with titles in other titles
	e_deck = remove_event_duplicates(e_deck)

	#remove events on multiple_pages
	e_deck = remove_events_on_multiple_pages(e_deck)

	e_deck = scrub_events_1(e_deck)

	e_deck = scrub_events_2(e_deck,doc_dict,org,metas,tags)

	e_deck = scrub_events_3(e_deck)

	e_deck = scrub_events_4(e_deck)

	#fix closed days - nb post tagging so meta_tag fixed
	e_deck = set_closed_days(e_deck, organiser)

	#restack images":
	print('\n')
	print('.. restack images')
	e_deck = restack_images(e_deck)
	
	print('\n')

	############################################################
	c = datetime.datetime.now()
	print("="*75)
	print('Finished get_events: ', c)
	print('Duration get_events: ',(c-a),'\n\n')
	############################################################

	#store each event
	for e in e_deck:

		ind = -1
		title = e.title
		use_default_opening = False

		###################################################################
		print('...... saving: ',title,'\n','-'*70,'\n',e.__dict__,'\n')
		###################################################################

		if e.meta_tag.lower() == 'art' and 'exhibition' in e.tags.lower() and \
			e.date_beg < e.date_end:
			use_default_opening = True

		mo,tu,we,th,fr,sa,su = True,True,True,True,True,True,True
		closed = e.closed.lower()
		if 'mo' in closed: mo = False #i.e to set scraped.mon = False
		if 'tu' in closed: tu = False
		if 'we' in closed: we = False
		if 'th' in closed: th = False
		if 'fr' in closed: fr = False
		if 'sa' in closed: sa = False
		if 'su' in closed: su = False

		try:
			s = Scraped (
					org = organiser,
					evt_nam = title,
					evt_url = e.url,
					evt_dte = e.date_beg,
					evt_end = e.date_end,
					descr = e.descr,
					img = e.img,
					tme_beg = e.time_beg,
					tme_end = e.time_end,
					tme_found = e.time_found,
					free = e.free,
					dflt_opening = use_default_opening,
					ven_ref = ven_ref,
					meta_tag = e.meta_tag,
					tags =  e.tags,
					mon = mo, tue = tu, wed = we, thu = th,
					fri = fr, sat = sa, sun = su,
				)	

			s.save()

		except:
			######################################################
			print('...... failed saving: ',e.url)
			######################################################
			fails.append(e.url)

	#get number of events found for organiser/promoter
	num_events = len(e_deck)

	#save errors down in files for later review
	if fails:
		f_name = base_dir+'/dumped/fail_saves_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in fails:
				save_file.writelines(f)
				save_file.writelines('\n')

	if failed_dates:
		f_name = base_dir+'/dumped/fail_dates_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in failed_dates:
				save_file.writelines(f)
				save_file.writelines('\n')

	if failed_times:
		f_name = base_dir+'/dumped/fail_times_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in failed_times:
				save_file.writelines(f)
				save_file.writelines('\n')

	if failed_requests:
		f_name = base_dir+'/dumped/fail_requests_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in failed_requests:
				save_file.writelines(f)
				save_file.writelines('\n')

	if failed_connects:
		f_name = base_dir+'/dumped/fail_connects_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in failed_connects:
				save_file.writelines(f)
				save_file.writelines('\n')

	if unicode_errors:
		f_name = base_dir+'/dumped/unicode_errors_'+today	
		with open(f_name, mode='w', encoding='utf-8') as save_file:
			for f in unicode_errors:
				save_file.writelines(f)
				save_file.writelines('\n')

	print("="*32,'  SUMMARY  ',"="*32)
	print('{:<25}'.format('Start get_webpages'), a.strftime('%H:%M:%S'))
	print('{:<25}'.format('End get_webpages'), b.strftime('%H:%M:%S'))
	print('{:<25}'.format('Duration get_webpages'),
									round((b-a).total_seconds(),2),'secs')
	print('{:<25}'.format('Number of webpages'),len(doc_dict))
	print('{:<25}'.format('Stop get_events'), c.strftime('%H:%M:%S'))
	print('{:<25}'.format('Duration get_events'),
									round((c-b).total_seconds(),2),'secs')
	print('{:<25}'.format('Process duration'),
									round((c-a).total_seconds(),2),'secs')
	print('{:<25}'.format('Number of events'),len(e_deck))
	print('{:<25}'.format('Failed uploads'),len(fails))
	print('{:<25}'.format('Uploaded events'),len(e_deck)-len(fails))
	print("="*30,'  SUMMARY END  ',"="*30)

	#if fails using urllib, reset js_site and re-scrape
	try: 
		secs = re.findall(r'\d+:\d+:(\d{2}).\d+',str(c-a))[0]
		if secs:
			secs = int(secs)
			if secs < 2 and len(e_deck) == 0:
				if not organiser.js_site:
					print('\n')
					print("No Events + short Return: set js_site")
					organiser.js_site = True
					organiser.save()
					print('...... try scraping again\n')
					scrape_now(org,seed_url,
						test_org=organiser,use_alt=kwargs['use_alt'])
	except:
		print('Re-scrape failed')
		pass

	return num_events

	