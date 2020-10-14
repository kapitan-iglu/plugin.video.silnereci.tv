# -*- coding: utf-8 -*-
import urllib2,urllib,re,os
import xbmcplugin,xbmcgui,xbmcaddon
import simplejson as json
try:
	from HTMLParser import HTMLParser
except ImportError:
	from html.parser import HTMLParser

__baseurl__ = 'https://www.silnereci.sk'
__addon__ = xbmcaddon.Addon('plugin.video.silnereci.tv')
__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__scriptname__ = __addon__.getAddonInfo('name')
icon =  os.path.join( __cwd__, 'icon.png' )
nexticon = os.path.join( __cwd__, 'nextpage.png' )
useragent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

def log(msg, level=xbmc.LOGDEBUG):
	if type(msg).__name__=='unicode':
		msg = msg.encode('utf-8')
	xbmc.log("[%s] %s"%(__scriptname__,msg.__str__()), level)

def logDbg(msg):
	log(msg,level=xbmc.LOGDEBUG)

def logErr(msg):
	log(msg,level=xbmc.LOGERROR)

def notifyErr(msg, timeout = 7000):
	xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__scriptname__, msg.encode('utf-8'), timeout, __addon__.getAddonInfo('icon')))
	logErr(msg)

def composePluginUrl(url, mode):
	return sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)

def addLink(name,url,mode,iconimage,date,related):
	logDbg("addLink(): '"+name+"' url='"+url + "' img='"+iconimage+"'date='"+date+"'")
	u=sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)
	ok=True
	liz=xbmcgui.ListItem(name+' ('+date+')', iconImage="DefaultVideo.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name} )
	liz.setProperty("IsPlayable", "true")
	if len(related):
		menuitems = []
		for related_name, related_url in related.items():
			logDbg('\tMenuItem: '+related_name+': '+related_url)
			related_url = composePluginUrl(related_url,1)
			menuitems.append((u'Prejsť na: '+related_name+'', 'XBMC.Container.Update('+related_url+')'))
		liz.addContextMenuItems(menuitems)
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
	return ok

def addDir(name,url,mode,iconimage):
	logDbg("addDir(): '"+name+"' url='"+url+"' img='"+str(iconimage)+"'")
	u=sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)
	ok=True
	liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name} )
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
	return ok

def getDataFromUrl(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', useragent)
	response = urllib2.urlopen(req)
	data = response.read()
	response.close()
	return data

def getHtmlFromUrl(url):
	return getDataFromUrl(url).decode("utf-8")

def getJsonDataFromUrl(url):
    return json.loads(getDataFromUrl(url))

def listCategories():
	logDbg("listCategories()")
	data = getHtmlFromUrl(__baseurl__+'/tv/')
	pattern = re.compile('<h4><a href="(.+?)"[^>]*?>(.+?)</a></h4>', re.DOTALL)
	it = re.finditer(pattern,data)
	for item in it:
		link,title = item.groups()
		addDir(title.strip(),__baseurl__+link,1,None)
#	addDir('Komici','https://silnereci.sk/komici/',1,None)

def listEpisodes(url):
	logDbg("listEpisodes()")
	logDbg("\turl="+url)
	data = getHtmlFromUrl(url)
	pattern = re.compile('<article class="([^"]+).+?<a href="([^"]+)"\s+title="([^"]+)">.+?src="([^"]+)"(.+?)<span class="updated[^>]+>(.+?)</span>', re.DOTALL)
	it = re.finditer(pattern,data)
	for item in it:
		tags,link,title,img,related,date = item.groups()
		h = HTMLParser()
		title=h.unescape(title)
		if 'rcp-no-access' in tags:
			continue
		beg_idx=related.find('<span class="entry-category"')
		related_items = {}
		if beg_idx >= 0:
			end_idx=related.find('<h2')
			pattern = re.compile('<a href="([^"]+?)"[^>]+>([^<]+?)</a>', re.DOTALL)
			it = re.finditer(pattern,related[beg_idx:end_idx])
			for item in it:
				related_link,related_title = item.groups()
				base_url = related_link.strip('/').rsplit('/',1)[-1]
				if base_url in url:
					continue
				related_items[related_title]=related_link
		addLink(title,link,2,img,date,related_items)
	match = re.compile(r'<a class="next page-numbers" href="(.+?)">(.+?)</a>', re.DOTALL).search(data)
	if match:
		addDir(match.group(2),match.group(1),1,nexticon)

def playEpisode(url):
	logDbg("playEpisode()")
	logDbg("\turl="+url)
	url=getVideoUrl(url)
	if url:
		liz = xbmcgui.ListItem(path=url, iconImage="DefaultVideo.png")
#		liz.setInfo( type="Video", infoLabels={ "Title": 'titulok'} )
		liz.setProperty('IsPlayable', "true")
		xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=liz)
	return

def getVideoUrl(url):
	logDbg("getVideoUrl()")
	httpdata = getHtmlFromUrl(url)
	match = re.compile(r'data-action="video"\s+data-id="([0-9]+)"', re.DOTALL).search(httpdata)
	if not match:
		logDbg("\tdata-id not found")
		notifyErr(u"Platený obsah?")
		return None
	ytid=getYTid(match.group(1))
	if ytid:
		return 'plugin://plugin.video.youtube/play/?video_id='+ytid
	return None

def getYTid(data_id):
	logDbg("getYTID("+data_id+")")
	values = {'action' : 'vlog_format_content',	'format' : 'video',	'id' : data_id }
	data = urllib.urlencode(values)
	req = urllib2.Request('https://silnereci.sk/wp-admin/admin-ajax.php', data)
	req.add_header('User-Agent', useragent)
	response = urllib2.urlopen(req)
	httpdata = response.read()
	response.close()
	match = re.compile(r'www\.youtube\.com/embed/([^\?]+)', re.DOTALL).search(httpdata)
	if not match:
		logDbg("\tYouTube ID not found")
		return None
	logDbg("\tYouTube video ID: "+match.group(1))
	return match.group(1)

def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]
	return param

params=get_params()
url=None
mode=None

try:
	url=urllib.unquote_plus(params["url"])
except:
	pass
try:
	mode=int(params["mode"])
except:
	pass

logDbg("Mode: "+str(mode))
logDbg("URL: "+str(url))

if mode==None or url==None or len(url)<1:
	listCategories()

elif mode==1:
	listEpisodes(url)

elif mode==2:
	playEpisode(url)
	sys.exit(0)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
