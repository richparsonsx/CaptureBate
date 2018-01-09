from config import *

#from bs4 import BeautifulSoup
import re
import time, datetime, requests, json
import os, signal
import subprocess, psutil
import connection

class Model:

	def __init__(self, id):
		self._id = id
		self._online = False
		self._private = False
		self._r4 = None
		self._client = None
		self._gender = 'female'
		self._script_process = None
		self._pid = -1			# Recording script pid, note that the actual rtmpdump pid will be self._pid + 0
		self._flv = None		# The file we're rtmpdump-ing the recording to
		self._error = False		# self._error == True is something is wrong w/ this model's page
		
	def init(self):
		self._client = connection.Connection()
		self._online = self.is_online()
		self._private = self.is_private()
		
		if self._error:
			logging.debug('[Model.init] ' + self._id + ' does not exist on site')
			return

		status_string = ''
		if DEBUGGING:
			status_string = '\t[Model.init]\t'
		status_string = status_string + "online:" + str(self._online) + " | private:" + str(self._private) + " -> model initialized"
		
		if self._online and not self._private:
			self.write_log(status_string + " and starting recording | gender: " + self._gender, REC_START)
			self._start_recording()
		#else:
		#	self.write_log(status_string)

	def write_log(self, message, status = '  '):
		model_string = self._id
		id_length = len(model_string)
		for x in range(id_length, MAX_LEN):
			model_string = ' ' + model_string
		logging.info(status + ' ' + model_string + '  ' + message)

	def get_id(self):
		return self._id
		
	def set_client(self, client):
		self._client = client

	def is_recording(self):
		return self._pid != -1
	
	def is_online(self):
		try:
			chkOnline = False
			self._r4 = json.loads(requests.get('https://chaturbate.com/api/chatvideocontext/' + self._id + '/').text)
			for key, value in self._r4.iteritems():
				if key == 'room_status' and value == 'offline':
					logging.debug('[Model.is_online] ' + self._id + ' is offline.')
					return False
				elif key == 'code' and value == 'access-denied':
					logging.debug('[Model.is_online] ' + self._id + ' is online not available')
					return False
				elif key == 'room_status' and value == 'away':
					logging.debug('[Model.is_online] ' + self._id + ' is away.')
					return False
				elif key == 'room_status' and value == 'public':
					chkOnline = True
				elif key == 'broadcaster_gender':
					self._gender = value
			if chkOnline:
				return True
		except Exception, e:
			return False
			
	def is_private(self):
		if self._online:
			try:
				for key, value in self._r4.iteritems():
					if key == 'room_status' and value == 'private':
						logging.debug('[Model.is_private] ' + self._id + ' is online but in private show')
						return True
					elif key == 'room_status' and value == 'unauthorized':
						logging.debug('[Model.is_private] ' + self._id + ' is online but in password show')
						return True
					elif key == 'room_status' and value == 'hidden':
						logging.debug('[Model.is_private] ' + self._id + ' is online but in hidden show')
						return True
				logging.debug('[Model.is_private] ' + self._id + ' is online and not private')
				return False
			except Exception, e:
				logging.error('Some error during connection to https://chaturbate.com/api/chatvideocontext/' + self._id + '/')
				logging.error(e)
				return True
		else:
			logging.debug('[Model.is_private] ' + self._id + ' is not online')
			return False

	def _is_still_recording(self):
		try:
			p = psutil.Process(self._pid)
			stat = os.stat(TEMP_FOLDER + '/' + self._flv)
			tstamp = time.time()
			tdiff = tstamp - stat.st_mtime
			if p.status() == psutil.STATUS_ZOMBIE:
				self._script_process.communicate()
				# self.write_log(str(self._pid + 0) + ' active but zombie.', REC_START)
				return False
			elif tdiff > 40:
				self.write_log(str(self._pid + 0) + ' tdiff ('+ str(tdiff) + ') is greater than 40.  Active but file has not changed.')
				#self._script_process.communicate()
				#self.write_log(str(self._pid + 0) + ' active but file has not changed.', REC_START)
				#os.kill(self._pid + 0, signal.SIGTERM)
				return False
			else:
				os.kill(self._pid + 0, 0) 
				return True
		except Exception, e:
			self.write_log(str(self._pid + 0) + ' not active, so livestreamer must have died unplanned.', REC_START)
			#self._script_process.communicate()
			self.write_log(str(self._pid + 0) + ' debug ', REC_START)
			logging.debug(e)
			return False

	def _update_status(self, new_online, new_private):
		self._online = new_online
		self._private = new_private

	def update(self):
		if self._error:
			return
			
		self._client = connection.Connection()
		if (not self._client == None):
			new_online = self.is_online()
			new_private = self.is_private() 
			status_update = "online:" + str(self._online) + "->" + str(new_online) + " | private:" + str(self._private) + "->" + str(new_private)
			logging.debug('[Model.update]' + status_update)
			
			if self._online:
				# model was online
				if (not self._private):
					# model was online and not in a private room
					if new_online:
						# model stayed online
						stillRec = self._is_still_recording()
						if new_private:
							# model went into a private room, so stop recording
							self.write_log('went private, so stopping recording', REC_STOP)
							self._stop_recording()
						elif not stillRec:
							# Recording died, so clean up recording script and restart recording
							#self.write_log('recording died, so stopping recording.', REC_START)
							self._stop_recording()
							self.write_log('recording died, so restarting recording.', REC_START)
							self._start_recording()
					else:
						# new_online == False, so model went offline
						self.write_log('went offline, so stopping recording', REC_STOP)
						self._stop_recording()
				elif (not new_private) and new_online:
					# model was in a private room and model went public and stayed online
					self.write_log('left private room, so starting recording', REC_START)
					self._start_recording()
			elif new_online and (not new_private):
				# model was offline
				self.write_log('went online, so starting recording', REC_START)
				self._start_recording()
			self._update_status(new_online, new_private)
		else:
			self.write_log('unable to connect to connection.', REC_START)
			
	def _start_recording(self):
		logging.debug('[Model._start_recording] Starting recording for ' + self._id)
		model_url = "https://chaturbate.com/" + self._id + "/"
		script_name = SCRIPTS_FOLDER+'/'+self._id+'.sh'
		ts = time.time()
		st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M')
		self._flv = self._id + '_' + st + '.mp4'
		rtmpdump_string = RTMPDUMP + ' --quiet --yes-run-as-root --retry-streams 3 --retry-open 3 --hls-segment-threads 4 --hls-segment-attempts 4 --hls-segment-timeout 20 --hls-timeout 20 --hls-live-edge 4 -o "' + TEMP_FOLDER + '/' + self._flv + '" "' + model_url + '" best'
		
		flinks = open(script_name, 'w')
		flinks.write('#!/usr/local/bin/zsh\n')
		flinks.write(rtmpdump_string)
		logging.debug('[Model._start_recording] rtmpdump_string: ' + rtmpdump_string)
		flinks.write('\n')
		flinks.close()
		
		os.chmod(SCRIPTS_FOLDER + '/' + self._id + '.sh', 0777)
		logging.debug('[Get_links] ' + self._id +'.sh is created')
		self._script_process = subprocess.Popen(script_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		self._pid = self._script_process.pid
		logging.info('    [Model._start_recording]  Recording for ' + self._id + ' started with pid: ' + str(self._pid + 0))
		time.sleep(10)

	def _stop_recording(self):
		# Terminating self._pid + 0, since that is the actual rtmp process spawned by the recording script
		try: 
			if self._pid > 0:
				#if (not self._is_still_recording()):
				logging.info('     [Model._stop_recording]  Checking if still recording: ' + self._id + ' with pid ' + str(self._pid + 0))
				#stillRec = self._is_still_recording()
				#if not stillRec:
				#	#self._script_process.communicate()
				#	logging.info('     [Model._stop_recording]  Stopping recording: ' + self._id + ' with pid ' + str(self._pid + 0))
				#	time.sleep(5)
				os.kill(self._pid + 0, signal.SIGTERM) # or signal.SIGKILL
				#else:
				#	logging.info('     [Model._stop_recording]  Already stopped recording: ' + self._id + ' with pid ' + str(self._pid + 0))
		#	else:
		#		return
		except Exception, e:
			logging.info('     [Model._stop_recording]  kill ' + str(self._pid + 0) + ' failed')
			logging.debug(e)
#			return

		if (os.path.isfile(TEMP_FOLDER + '/' + self._flv)):
			# Check if the recording is at least MINIMAL_RECORDING_SIZE_IN_MB big
			if (os.path.getsize(TEMP_FOLDER + '/' + self._flv) >> 20) < MINIMAL_RECORDING_SIZE_IN_MB:
				# Deleting the recording, since it is too small
				logging.info('     [Model._stop_recording]  Deleting temp recording ' + self._flv + ' since it is too small')
				os.remove(TEMP_FOLDER + '/' + self._flv)
			else:
				# recording is at least the minimal recording size, so move it to the saved folder
				# Make the recording read- and writeable to the world
				logging.debug('   [Model._stop_recording] Making recording ' + self._flv + ' world read- and writeable')
				os.chmod(TEMP_FOLDER + '/' + self._flv, 0666)

				# Moving the recording
				logging.info('     [Model._stop_recording]  Moving recording ' + self._flv + ' to ' + OUTPUT_FOLDER + '/' + self._gender)
				os.rename(TEMP_FOLDER + '/' + self._flv, OUTPUT_FOLDER + '/' + self._gender + '/' + self._flv)
		# Clean up
		self._flv = None
		self._script_process = None
		self._pid = -1
		logging.debug('   [Model._stop_recording] Stopped recording: ' + self._id + ' with pid ' + str(self._pid))

	def destroy(self):
		logging.debug('   [Model.destroy] Starting cleanup of ' + self._id)
		if self._pid != -1:
			logging.info('             [Model.destroy]  Recording for ' + self._id + ' is being destroyed.  PID: ' + str(self._pid + 0))
			self._stop_recording()
		self._online = False
		self._private = False
		logging.debug('   [Model.destroy] Completed cleanup of ' + self._id)
