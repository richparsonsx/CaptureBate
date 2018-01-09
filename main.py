import config
from config import *
from time import sleep
import connection, time, datetime
from ModelsManager import ModelsManager

if __name__ == '__main__':
	init_logging()
	# Create directories
	Remove_folder(SCRIPTS_FOLDER)
	Preconditions(SCRIPTS_FOLDER)
	Preconditions(VIDEO_FOLDER)
	Preconditions(TEMP_FOLDER)
	mm = ModelsManager()
	while True:
		reload(config)
		from config import *
		try:
			if mm._tUpdate:
				if len(mm._wanted) > 0:
					mm.stopProcess()
					mm = ModelsManager()
					logging.info('')
				
				logging.info('************************ Starting application: version %s ************************' %VERSION)
				logging.info('***********************************************************************************')
				mm._tSpan = RELOAD_TIME
				mm.get_some()
			else:
				if len(mm._wanted) > 0:
					sleep(DELAY)
				ts = time.time()
				st = datetime.datetime.fromtimestamp(ts).strftime('%Y.%m.%d_%H.%M.%S')
				print(st + '  Running mm.update()')
				mm._tSpan = RELOAD_TIME
				mm.update()
		except Exception, e:
			if mm._tUpdate:
				if len(mm._wanted) > 0:
					mm.stopProcess()
					mm = ModelsManager()
					logging.info('')
				
				logging.info('************************ Starting application: version %s ************************' %VERSION)
				logging.info('***********************************************************************************')
				mm._tSpan = RELOAD_TIME
				mm.get_some()
			else:
				if len(mm._wanted) > 0:
					sleep(DELAY)
				ts = time.time()
				st = datetime.datetime.fromtimestamp(ts).strftime('%Y.%m.%d_%H.%M.%S')
				print(st + '  Running exception mm.update()')
				print(e)
				mm._tSpan = RELOAD_TIME
				mm.update()