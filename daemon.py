"""
	Daemon class that manages all the stuff a daemon manages
"""

import os
import sys
import atexit
import pwd, grp
import resource
import signal

class Daemon(object):

	def __init__(self,appname="pyDaemon",background=True,chrootdir=None,workdir="/",umask=0,pidfile=None,uid=None,gid=None,signals=None,stdin=None,stdout=None,stderr=None):
		self.appname = appname
		self.background = background
		self.chrootdir = chrootdir
		self.workdir = workdir
		self.umask = umask
		self.pidfile = pidfile
		self.signal_map = signals
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr

		if uid is None:
			uid = os.getuid()
		self.uid = uid

		if gid is None:
			gid = os.getgid()
		self.gid = gid

		self._is_open = False

	@property
	def is_open(self):
		return self._is_open


	def __enter__(self):
		self.open()
		return self

	def open(self):

		if self.is_open:
			return

		if self.chrootdir is not None:
			os.chdir(self.chrootdir)
			os.chroot(self.chrootdir)

		if self.workdir is not None:
			os.chdir(self.workdir)
		
		self.set_umask()
		self.change_process_owner()	

		self.map_signals()
		
		if self.background is True:
			self.bg()
			self.close_files()
			self.redirect(sys.stdin, self.stdin)
			self.redirect(sys.stdout, self.stdout)
			self.redirect(sys.stderr, self.stderr)

		if self.pidfile is not None:
			self.write_pidfile(str(os.getpid()))



		self._is_open = True

		self.register_atexit(self.close)

	def __exit__(self, etype, evalue, traceback):
		self.close()

	def close(self):
		if not self.is_open:
			return

		if self.pidfile is not None:
			self.remove_pidfile()
		self._is_open = False

	def bg(self):
		try:
			pid = os.fork()
			if pid > 0:
				os._exit(0)
		except OSError as exc:
			raise Exception("Unable to fork: {exc}".format(exc=exc))
			exit(1)

		os.setsid()

		try:
			pid = os.fork()
			if pid > 0:
				os._exit(0)
		except OSError as exc:
			raise Exception("Unable to fork again: {exc}".format(exc=exc))
			exit(1)


	def set_umask(self):
		try:
			os.umask(self.umask)
		except Exception as e:
			raise Exception('Unable to set umask: ({exc})'.format(exc=e))

	def change_process_owner(self):
		try:
			os.setgid(self.gid)
			os.setuid(self.uid)
		except Exception as e:
			raise Exception("Unable to change process owner: ({exc})".format(exc=e))

	def write_pidfile(self,pid):
		try:
			pidfp = os.open(self.pidfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
			os.write(pidfp, pid.encode())
			os.close(pidfp)
		except Exception as e:
			raise Exception("Unable to create pidfile: {exc}".format(exc=e))

	def remove_pidfile(self):
		try:
			os.remove(self.pidfile)
		except Exception as e:
			raise Exception("Unable to remove pidfile: {exc}".format(exc=e))

	def close_files(self):
		C_MAXFD = 1024

		maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
		if (maxfd == resource.RLIM_INFINITY):
			maxfd = C_MAXFD

		for fd in range(0, maxfd):
			try:
				os.close(fd)
			except OSError: #Ignore files that weren't open
				pass

	def map_signals(self):
		for (signal_num, handler) in self.signal_map.items():
			if handler is None or handler == "":
				handler = signal.SIG_IGN
			try:
				signal.signal(signal_num, handler)
			except RuntimeError as e:
				print("Error: Cannot handle signal")

	def redirect(self,srcStream, dstStream):

		if dstStream is None:
			if hasattr(os, "devnull"):
				null_to = os.devnull
			else:
				null_to = "/dev/null"

			targetStream = os.open(null_to, os.O_RDWR)
		else:
			targetStream = dstStream.fileno()

		os.dup2(targetStream, srcStream.fileno())
			

	def register_atexit(self, function):
		atexit.register(function)

	@classmethod
	def run(self):
		raise NotImplementedError

def get_uid_from_name(name):
	pwd_entry = pwd.getpwnam(name)
	return pwd_entry.pw_uid

def get_gid_from_name(name):
	grp_entry = grp.getgrnam(name)
	return grp_entry.gr_gid

def get_name_from_pid(pid):
	pwd_entry = pwd.getpwuid(uid)
	return pwd_entry.pw_name
