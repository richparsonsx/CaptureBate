'''
Connecting to site
'''
from config import *
from time import sleep

import re, requests
from MyAdapter import MyAdapter

def Connection():
	#Connecting to server
	count = 0
	while True:
		try:
#			logging.info('Connecting to ' + URL)
			client = requests.session()
			client.mount('https://', MyAdapter())
			# Retrieve the CSRF token first
			r1 = client.get(URL)
			csrftoken = r1.cookies['csrftoken']
			break
		except Exception, e:
			logging.error('Some error during connecting to '+URL)
			logging.error(e)
			logging.error('Trying again after 20 seconds')
			count+=1
			if count > 10:
				logging.info('Connection Error 1 - get crsftoken.  Sleep 180 seconds')
				logging.info(e)
				sleep(180)
				count = 0
			sleep(20)

	#csrftoken = r1.cookies['csrftoken']
	# Set login data and perform submit
	login_data = dict(username=USER, password=PASS, csrfmiddlewaretoken=csrftoken, next='/')
	count = 0
	while True:
		try:
			r = client.post(URL, data=login_data, headers=dict(Referer=URL))
			#logging.debug('Page Source for ' + URL + '\n' + r.text)
			page_source = 'Page Source for ' + URL + '\n' + r.text
			# if DEBUGGING is enabled Page source goes to debug.log file
			if DEBUGGING == True:
				Store_Debug(page_source, "connection.log")
			return client

		except Exception, e:
			logging.error('Some error during posting to '+URL)
			logging.error(e)
			if count > 10:
				logging.info('Connection Error 2 - data post.  Sleep 180 second. (' + URL + ')')
				logging.info(e)
				sleep(180)
				count = 0
				#return None
			sleep(20)
			count+=1