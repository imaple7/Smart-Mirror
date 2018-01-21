# -*- coding: utf-8 -*-

# smartmirror.py
# requirements
# requests, feedparser, traceback, Pillow

from Tkinter import *
from lunar import Lunar
import locale
import threading
import time
import requests
import json
import traceback
import feedparser

from PIL import Image, ImageTk
from contextlib import contextmanager

LOCALE_LOCK = threading.Lock()

ui_locale = '' # e.g. 'fr_FR' fro French, '' as default
time_format = 12 # 12 or 24
date_format = "%b %d, %Y" # check python doc for strftime() for options
news_country_code = 'cn'
weather_api_token = 'c483933cdf16e6c34b2f17a6574ef1db' # create account at https://darksky.net/dev/
weather_lang = 'en' # see https://darksky.net/dev/docs/forecast for full list of language parameters values
weather_unit = 'ca' # see https://darksky.net/dev/docs/forecast for full list of unit parameters values
latitude = None # Set this if IP location lookup does not work for you (must be a string)
longitude = None # Set this if IP location lookup does not work for you (must be a string)
xlarge_text_size = 94
large_text_size = 48
medium_text_size = 28
small_text_size = 18
future_weather_text_size = 14

@contextmanager
def setlocale(name): #thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)

# maps open weather icons to
# icon reading is not impacted by the 'lang' parameter
icon_lookup = {
    'clear-day': "assets/Sun.png",  # clear sky day
    'wind': "assets/Wind.png",   #wind
    'cloudy': "assets/Cloud.png",  # cloudy day
    'partly-cloudy-day': "assets/PartlySunny.png",  # partly cloudy day
    'rain': "assets/Rain.png",  # rain day
    'snow': "assets/Snow.png",  # snow day
    'snow-thin': "assets/Snow.png",  # sleet day
    'fog': "assets/Haze.png",  # fog day
    'clear-night': "assets/Moon.png",  # clear sky night
    'partly-cloudy-night': "assets/PartlyMoon.png",  # scattered clouds night
    'thunderstorm': "assets/Storm.png",  # thunderstorm
    'tornado': "assests/Tornado.png",    # tornado
    'hail': "assests/Hail.png"  # hail
}


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black")
        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize day of week
        self.day_of_week1 = ''
        self.dayOWLbl = Label(self, text=self.day_of_week1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dayOWLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dateLbl.pack(side=TOP, anchor=E)
        # initialize chinese calendar
        self.chineseDate1 = ''
        self.chineseDateLb1 = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.chineseDateLb1.pack(side=TOP, anchor=E)
        self.chineseJieqi1 = ''
        self.chineseJieqiLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.chineseJieqiLbl.pack(side=TOP, anchor=E)

        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p') #hour in 12h format
            else:
                time2 = time.strftime('%H:%M') #hour in 24h format

            day_of_week2 = time.strftime('%A')
            date2 = time.strftime(date_format)
            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if day_of_week2 != self.day_of_week1:
                self.day_of_week1 = day_of_week2
                self.dayOWLbl.config(text=day_of_week2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)

            #Chinese calendar
            ln = Lunar()
            chineseDate2 = ln.ln_date_str() + " 【" + ln.gz_year() + "】 " + ln.sx_year() + "年 " + ln.gz_day() + "日 " + ln.gz_hour() + "时"
            chineseJieqi2 = "节气：" + ln.ln_jie()
            if chineseDate2 != self.chineseDate1:
                self.chineseDate1 = chineseDate2
                self.chineseDateLb1.config(text=chineseDate2)
            if chineseJieqi2 != self.chineseJieqi1:
                self.chineseJieqi1 = chineseJieqi2
                self.chineseJieqiLbl.config(text=chineseJieqi2)

            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
            self.timeLbl.after(200, self.tick)

class Weather(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.temperature = ''
        self.forecast = ''
        self.location = ''
        self.currently = ''
        self.icon = ''

        self.degreeFrm = Frame(self, bg="black")
        self.degreeFrm.pack(side=TOP, anchor=W)
        self.temperatureLbl = Label(self.degreeFrm, font=('Helvetica', xlarge_text_size), fg="white", bg="black")
        self.temperatureLbl.pack(side=LEFT, anchor=N)
        self.iconLbl = Label(self.degreeFrm, bg="black")
        self.iconLbl.pack(side=LEFT, anchor=N, padx=20)
        self.currentlyLbl = Label(self, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.currentlyLbl.pack(side=TOP, anchor=W)
        self.forecastLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.forecastLbl.pack(side=TOP, anchor=W)
        self.locationLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.locationLbl.pack(side=TOP, anchor=W)

        self.futureContainer = Frame(self, bg="black")
        self.futureContainer.pack(side=TOP)


        self.get_weather()

    def get_ip(self):
        try:
            ip_url = "http://jsonip.com/"
            req = requests.get(ip_url)
            ip_json = json.loads(req.text)
            return ip_json['ip']
        except Exception as e:
            traceback.print_exc()
            return "Error: %s. Cannot get ip." % e

    def get_weather(self):
        try:

            if latitude is None and longitude is None:
                # get location
                location_req_url = "http://freegeoip.net/json/%s" % self.get_ip()
                r = requests.get(location_req_url)
                location_obj = json.loads(r.text)

                lat = location_obj['latitude']
                lon = location_obj['longitude']

                location2 = "%s, %s" % (location_obj['city'], location_obj['region_code'])

                # get weather
                weather_req_url = "https://api.darksky.net/forecast/%s/%s,%s?lang=%s&units=%s" % (weather_api_token, lat,lon,weather_lang,weather_unit)
            else:
                location2 = ""
                # get weather
                weather_req_url = "https://api.darksky.net/forecast/%s/%s,%s?lang=%s&units=%s" % (weather_api_token, latitude, longitude, weather_lang, weather_unit)

            r = requests.get(weather_req_url)
            weather_obj = json.loads(r.text)
            self.get_futureForecast(weather_obj)

            degree_sign= u'\N{DEGREE SIGN}'
            temperature2 = "%s%s" % (str(int(weather_obj['currently']['temperature'])), degree_sign)
            currently2 = weather_obj['currently']['summary']
            forecast2 = weather_obj["hourly"]["summary"]
            icon_id = weather_obj['currently']['icon']
            icon2 = None

            if icon_id in icon_lookup:
                icon2 = icon_lookup[icon_id]

            if icon2 is not None:
                if self.icon != icon2:
                    self.icon = icon2
                    image = Image.open(icon2)
                    image = image.resize((100, 100), Image.ANTIALIAS)
                    image = image.convert('RGB')
                    photo = ImageTk.PhotoImage(image)

                    self.iconLbl.config(image=photo)
                    self.iconLbl.image = photo
            else:
                # remove image
                self.iconLbl.config(image='')

            if self.currently != currently2:
                self.currently = currently2
                self.currentlyLbl.config(text=currently2)
            if self.forecast != forecast2:
                self.forecast = forecast2
                self.forecastLbl.config(text=forecast2)
            if self.temperature != temperature2:
                self.temperature = temperature2
                self.temperatureLbl.config(text=temperature2)
            if self.location != location2:
                if location2 == ", ":
                    self.location = "Cannot Pinpoint Location"
                    self.locationLbl.config(text="Cannot Pinpoint Location")
                else:
                    self.location = location2
                    self.locationLbl.config(text=location2)

        except Exception as e:
            traceback.print_exc()
            print "Error: %s. Cannot get weather." % e

        # DarkSky API allows 1,000 calls per day for free,
        # Set as refresh every 5 mins. => 288 calls per day
        self.after(300000, self.get_weather)

    def get_futureForecast(self, json_object):
        try:
            # remove all children
            for widget in self.futureContainer.winfo_children():
                widget.destroy()

            next_week_forecast = json_object["daily"]

            for day_forecast in next_week_forecast["data"][1:7]:
                dayForecast = DayForecast(self.futureContainer, day_forecast["time"], day_forecast["temperatureHigh"], day_forecast["temperatureLow"], day_forecast["icon"])
                dayForecast.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print "Error: %s. Cannot get forecast." % e

class DayForecast(Frame):
    def __init__(self, parent, day_time="", day_high_temp = 0.0, day_low_temp = 0.0, day_icon=""):
        Frame.__init__(self, parent, bg='black')
        future_icon_2 = None

        degree_sign = u'\N{DEGREE SIGN}'
        temp_high = "%s%s" % (str(int(day_high_temp)), degree_sign)
        temp_low = "%s%s" % (str(int(day_low_temp)), degree_sign)
        day_print = ""

        # convert UNIX timestamp to Weekday
	day_time_string = time.strftime("%A", time.localtime(day_time))
	day_high_temp_string = "High:" + temp_high
	day_low_temp_string = "Low:" + temp_low

	if day_time_string == "Wednesday":
            day_time_string += "\t"
	else:
	    day_time_string += "\t\t"
        day_print += day_time_string + day_high_temp_string + "\t" + day_low_temp_string + "\t"

        if day_icon in icon_lookup:
            future_icon_2 = icon_lookup[day_icon]

        if future_icon_2 is not None:
            image = Image.open(future_icon_2)
            image = image.resize((25, 25), Image.ANTIALIAS)
            image = image.convert('RGB')
            photo = ImageTk.PhotoImage(image)

        self.eventName = day_time
        self.eventNameLbl = Label(self, text=day_print, font=('Helvetica', future_weather_text_size), fg="white",bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N, padx=20)

class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'News' # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if news_country_code == None:
                headlines_url = "https://news.google.com/news?ned=us&output=rss"
            else:
                headlines_url = "https://news.google.com/news?ned=%s&output=rss" % news_country_code

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[1:6]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print "Error: %s. Cannot get news." % e

        self.after(300000, self.get_headlines)

class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg='black')

        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)

class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events'
        self.calendarLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=E)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=E)
        self.get_events()

    def get_events(self):
        #TODO: implement this method
        # reference https://developers.google.com/google-apps/calendar/quickstart/python

        # remove all children
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        calendar_event = CalendarEvent(self.calendarEventContainer)
        calendar_event.pack(side=TOP, anchor=E)
        pass

class CalendarEvent(Frame):
    def __init__(self, parent, event_name="Event 1"):
        Frame.__init__(self, parent, bg='black')
        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=TOP, anchor=E)

class CenterText(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.sentence = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.sentence.pack(side=TOP, anchor=W)
        self.reference = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.reference.pack(side=RIGHT, anchor=W)

        self.get_quotation()

    def get_quotation(self):
        try:
            # Get json
            quotation_url = "https://sslapi.hitokoto.cn/?encode=json"

            r = requests.get(quotation_url)
            quotation_obj = json.loads(r.text)

            sentence = quotation_obj["hitokoto"]
            reference = quotation_obj["from"]

            self.sentence.config(text=sentence)
            self.reference.config(text=reference)

        except Exception as e:
            traceback.print_exc()
            print "Error: %s. Cannot get quotation." % e

        self.after(300000, self.get_quotation)

class FullscreenWindow:

    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background = 'black')
        self.bottomFrame = Frame(self.tk, background = 'black')
        self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        self.bottomFrame.pack(side = BOTTOM, fill=BOTH, expand = YES)
        self.centerFrame = Frame(self.tk, background = 'black')
        self.centerFrame.pack(side = TOP, fill=BOTH, expand = YES)
        self.centerFrame.place(relx=0.5, rely=0.6, anchor=CENTER)
        self.state = False
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)
        # clock
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=RIGHT, anchor=N, padx=100, pady=60)
        # weather
        self.weather = Weather(self.topFrame)
        self.weather.pack(side=LEFT, anchor=N, padx=100, pady=60)
        # news
        self.news = News(self.bottomFrame)
        self.news.pack(side=LEFT, anchor=S, padx=100, pady=60)
        #center text - Hitokoto
        self.centerText = CenterText(self.centerFrame)
        self.centerText.pack(side=LEFT, anchor=S, padx=10, pady=10)

        # calender - removing for now
        # self.calender = Calendar(self.bottomFrame)
        # self.calender.pack(side = RIGHT, anchor=S, padx=100, pady=60)

    def toggle_fullscreen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_fullscreen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"

if __name__ == '__main__':
    w = FullscreenWindow()
    w.tk.mainloop()
