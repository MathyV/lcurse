from PyQt5 import Qt
from bs4 import BeautifulSoup
import cookielib, urllib2
import zipfile
import defines
import os

class CheckDlg(Qt.QDialog):
	checkFinished = Qt.pyqtSignal(Qt.QVariant, bool, Qt.QVariant)
	def __init__(self, parent, addons):
		super(CheckDlg, self).__init__(parent)
		layout = Qt.QVBoxLayout(self)
		if len(addons) == 1:
			layout.addWidget(Qt.QLabel(self.tr("Verifying if the addon needs an update...")))
		else:
			layout.addWidget(Qt.QLabel(self.tr("Verifying which addon needs an update...")))
		self.progress = Qt.QProgressBar(self)
		self.progress.setRange(0, len(addons) - 1)
		layout.addWidget(self.progress)
		self.addons = addons

	def exec_(self):
		self.threads = []
		for addon in self.addons:
			idx = len(self.threads)
			self.threads.append(CheckWorker(addon))
			self.threads[idx].checkFinished.connect(self.onCheckFinished)
			self.threads[idx].start()
		super(CheckDlg, self).exec_()

	@Qt.pyqtSlot(int, Qt.QVariant)
	def onCheckFinished(self, addon, needsUpdate, updateData):
		value = self.progress.value() + 1
		self.progress.setValue(value)
		self.checkFinished.emit(addon, needsUpdate, updateData)
		if value == self.progress.maximum():
			self.close()

class CheckWorker(Qt.QThread):
	checkFinished = Qt.pyqtSignal(Qt.QVariant, bool, Qt.QVariant)
	def __init__(self, addon):
		super(CheckWorker, self).__init__()
		self.addon = addon
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
		# default User-Agent ('Python-urllib/2.6') will *not* work
		self.opener.addheaders = [('User-Agent', 'Mozilla/5.0'),]

	def needsUpdate(self):
		try:
			response = self.opener.open(str(self.addon[2]) + "/download")
			html = response.read()
			with open("/tmp/response.txt", "w") as f:
				f.write(html)
			soup = BeautifulSoup(html)
			lis = soup.select('#breadcrumbs-wrapper ul li span')
			if len(lis) > 0:
				version = lis[len(lis) - 1].string
				if str(self.addon[3]) != version:
					downloadLink = soup.select(".download-link")[0].get('data-href')
					return (True, (version, downloadLink))
			return (False, ("", ""))
		except urllib2.HTTPError as e:
			print(e)
		return (False, None)

	def run(self):
		result = self.needsUpdate()
		self.checkFinished.emit(self.addon, result[0], result[1]) 

class UpdateDlg(Qt.QDialog):
	updateFinished = Qt.pyqtSignal(Qt.QVariant, bool)
	def __init__(self, parent, addons):
		super(UpdateDlg, self).__init__(parent)
		layout = Qt.QVBoxLayout(self)
		if len(addons) == 1:
			layout.addWidget(Qt.QLabel(self.tr("Updating the addon...")))
		else:
			layout.addWidget(Qt.QLabel(self.tr("Updating the addons...")))
		self.progress = Qt.QProgressBar(self)
		self.progress.setRange(0, len(addons) - 1)
		layout.addWidget(self.progress)
		self.addons = addons

	def exec_(self):
		self.threads = []
		for addon in self.addons:
			idx = len(self.threads)
			self.threads.append(UpdateWorker(addon))
			self.threads[idx].updateFinished.connect(self.onUpdateFinished)
			self.threads[idx].start()
		super(UpdateDlg, self).exec_()

	@Qt.pyqtSlot(int, Qt.QVariant)
	def onUpdateFinished(self, addon, result):
		value = self.progress.value() + 1
		self.progress.setValue(value)
		self.updateFinished.emit(addon, result)
		if value == self.progress.maximum():
			self.close()

class UpdateWorker(Qt.QThread):
	updateFinished = Qt.pyqtSignal(Qt.QVariant, bool)
	def __init__(self, addon):
		super(UpdateWorker, self).__init__()
		self.addon = addon
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
		# default User-Agent ('Python-urllib/2.6') will *not* work
		self.opener.addheaders = [('User-Agent', 'Mozilla/5.0'),]

	def doUpdate(self):
		try:
			settings = Qt.QSettings()
			print("updating addon %s to version %s ..." % (self.addon[1], self.addon[4][0]))
			response = self.opener.open(self.addon[4][1])
			filename = "/tmp/%s" % (self.addon[4][1].split('/')[-1])
			dest = "%s/Interface/AddOns/" % (settings.value(defines.WOW_FOLDER_KEY, defines.WOW_FOLDER_DEFAULT))
			with open(filename, 'wb') as zipped:
				zipped.write(response.read())
			with zipfile.ZipFile(filename, "r") as z:
				z.extractall(dest)
			os.remove(filename)
			return True
		except Exception as e:
			print(e)
		return False

	def run(self):
		result = self.doUpdate()
		self.updateFinished.emit(self.addon, result) 
