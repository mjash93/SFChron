import numpy as np
import pandas as pd

import requests
import requests_cache
import lxml.html as lx

import nltk
import re

def get_articles(url):
	"""
		function designed to scrape all article url's from the article list. 

		Input: 
			url -- article list url
		Output:
			links -- list of article url's
	"""
	response = requests.get(url)
	try:
		response.raise_for_status()
	except:
		print("URL {} couldn't be downloaded.".format(url))

	html = lx.fromstring(response.text)
	html.make_links_absolute(url)
	links = html.xpath('//a/@href')

	links = [x for x in links if 'article' in x]
	links = set(links) # remove any duplicate links
	return list(links) # return the links as a list, after cutting duplicates

def get_mod_date(html):
	"""
		I found that the two paths below work very well to find the dates. I used two instead of 1 for the ease
		of accessing the data inside the elements (use of content or datetime)
	"""
	time = html.xpath("//article//header//time")
	date_mod = html.xpath("//*[@*='article:modified_time']")

	if len(date_mod) != 0:
		return date_mod[0].get('content').strip()
	elif len(time) == 2:
		return time[1].get('datetime').strip()
	else:
		return None

def get_date(html):
	date_pub = html.xpath("//*[@*='article:published_time']")

	if len(date_pub) != 0: 
		return date_pub[0].get('content').strip()
	else:
		return None

def get_text(html):
	textstring = ''
	text = html.xpath("//main//section[contains(@class,'body')]/p |//div[@class='article-body']/p |//div[@class='text-block']/p | //div[@class='article-text']/p")
	text = [x.text for x in text]
	# remove None values in the string (shows up occasionally)
	for y in text:
		try:
			textstring = textstring + ' ' + y.strip()
		except AttributeError:
			pass
	return textstring

def get_title(html):
	title = html.xpath("//title")
	return title[0].text.strip()

def get_author(html):
	author = html.xpath("//article//header//span[starts-with(@class, 'header-')] |//p[@class='byline']/a |//div[@class='author']/a |//p[@class='byline']/a")
	try:
		author =  [x.text.strip() for x in author if len(x.text.strip()) > 0][0]
		return author
	except IndexError:
		return None

def get_data(url):
	"""
		get_data retrieves a set of information from a given article and returns
		it in a dict with the following keys.
		Input:
			url -- article url
		Output:
			my_info -- dict with relevant info as values
	"""
	response = requests.get(url)
	try:
		response.raise_for_status()
	except:
		print("URL {} couldn't be downloaded.".format(url))

	html = lx.fromstring(response.text)

	my_info ={
	'url': url, 'title': get_title(html), 'author': get_author(html),
	'date': get_date(html), 'date_updated': get_mod_date(html), 'text': get_text(html),
	}

	return my_info

def scrape_chronicle(base_url, category=None):
	"""
		function meant to take as input the url of SF Chronicle's main page as well as a parameter that 
		determines which article list to scrape. The function then scrapes all articles and relevant article
		info from the page and puts it into a pandas dataframe.

		Input:
			url -- SF Chronicle URL
			category -- the category to scrape, default None (assumes that the user inputs 
							url of category)
		Output:
			df -- dataframe with all articles for a given category
	"""
	if category is None:
		if base_url[-1] == '/': category = base_url.rsplit('/', 2)[-2]
		else: category = base_url.rsplit('/', 1)[-1]

	links = get_articles(base_url)
	df = pd.DataFrame(columns=['url','title','author','category','date','date_updated','text'])

	for url in links:
		article_info = get_data(url)
		article_info['category'] = category
		df_temp = pd.DataFrame([article_info])
		df = df.merge(df_temp, how='outer')


	df['date'] = df['date'].str.replace('T.*', '')
	df['date_updated'] = df['date_updated'].str.replace('T.*', '')
	df['author'] = df['author'].str.replace('By','')
	df['author'] = df['author'].str.replace(',.*','')
	df['category'] = df['category'].str.replace('us-world', 'world')

	df['date'] = pd.to_datetime(df['date'])
	df['date_updated'] = pd.to_datetime(df['date_updated'])

	df = df.rename({'date_updated': 'date updated'}, axis=1)

	return df

def freq_dist(doc, stopwords, ng=1):
	"""
		returns frequency distribution for a document, based off Nick's code from lecture
	"""
	words = [w.lower() for w in re.findall(r"(?:\w|['&])+", doc) if w.lower() not in stopwords]
	words = nltk.ngrams(words, ng)
	return nltk.FreqDist(words)

def comp_rel_freq(df, textstring, category):
	"""
		computes the relative frequency of a dataframe to better analyze the importance
		of certain words. 
	"""
	series = df.sum(axis=0)
	df = series.to_frame().reset_index()
	df = df.rename({'index': 'n-gram',0:'count'}, axis=1)
	df['category'] = category
	df['relative'] = 2 * df['count'] / len(textstring) *100 #(approx due to whitespace)
	return df

#from lxml import etree
#print(etree.tostring(time[1], pretty_print=True))

