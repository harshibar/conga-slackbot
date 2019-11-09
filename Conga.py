import threading
import time
import requests
import json
import config
import datetime
from datetime import datetime, timedelta
import pytz

# a class for *each* conga line
class Conga(object):
    def __init__(self, conductor, destination, departureTime, minLeft):
        self.DepartureTime = departureTime.strftime("%I:%M%p on %b %d %Y")
        self.TimeRemaining = minLeft
        self.DisplayDestination = destination
        self.MapDestination = destination.lower()
        self.Passengers = set([conductor])
        self.Lock = threading.Lock()

    def AddPassenger(self, passenger):
        self.Lock.acquire()
        if passenger in self.Passengers:
            self.Lock.release()
            return "%s is already on the conga line to %s 😎" % (passenger, self.DisplayDestination)
        self.Passengers.add(passenger)
        self.Lock.release()
        return None

    # human readable list of passengers
    def PassengerString(self):
        self.Lock.acquire()
        res = ""
        numPassengers = len(self.Passengers)
        i = 0
        for passenger in self.Passengers:
            res += passenger
            if i != numPassengers - 1:
                res += ", "
            if i == numPassengers - 2:
                res += "and "
            i += 1
        self.Lock.release()
        return res

# a group of conga lines
class Party(object):
    def __init__(self):
        self.Lock = threading.Lock()
        self.Congas = {}

    def AddConga(self, conga):
        if conga.MapDestination in self.Congas:
            return "There's already a conga line to %s 🤩" % conga.MapDestination
        else:
            self.Congas[conga.MapDestination] = conga
            return None

    def DeleteConga(self, destination):
        res = self.Congas.pop(destination, None)
        if res is None:
            return res
        return "The conga line to %s doesn't exist so it can't be removed 😱" % destination

    # show all active conga lines
    def ActiveCongaCommand(self):
        self.Lock.acquire()
        res = "There are conga lines to:\n"
        i = 0
        numCongas = len(self.Congas)
        if numCongas == 0:
            self.Lock.release()
            return "There are currently no active conga lines. Try starting one! 😏"
        for dest in self.Congas:
            conga = self.Congas[dest]
            if numCongas == 1:
                self.Lock.release()
                return f"There is currently a conga line to {conga.DisplayDestination} at {conga.DepartureTime} (with {conga.PassengerString()} on it)"
            else:
                res += f"{conga.DisplayDestination} at {conga.DepartureTime} (with {conga.PassengerString()} on it)"
            if i != numCongas - 1:
                res += ", \n"
            i += 1
        self.Lock.release()
        return res

    def HelpCommand(self):
        return "Usage: /conga start <destination> <minutes> || /conga join <destination> || /conga active"

    def JoinCongaCommand(self, passenger, destination):
        self.Lock.acquire()
        destination = destination.lower()
        res = ""
        # make sure conga line exists
        if destination in self.Congas:
            conga = self.Congas[destination]
            err = conga.AddPassenger(passenger)
            self.Lock.release()
            if err is not None:
                return err
            elif res == "":
                res = "%s jumped on the conga line to %s 🚂" % (passenger, conga.DisplayDestination)
                return res
            else:
                return res
        else:
            self.Lock.release()
            return "That conga line doesn't exist, please try again or find a new conga line to join 😫"

    # this doesn't work right now lol
    def LeaveCongaCommand(self, passenger, destination):
        self.Lock.acquire()
        destination = destination.lower()
        res = ""
        if destination in self.Congas:
            passengerCongas = self.GetPassengerCongas(passenger)
            if passengerCongas is not None and destination in passengerCongas:
                res = self.DitchConga(passenger, destination)
        else:
            self.Lock.release()
            return "That conga line doesn't exist, please try again or find a new conga line to join 😫"


    def DitchConga(self, passenger, destination):
        res = "%s ditched their conga line to %s." % (passenger, destination)
        passengerCongas = self.GetPassengerCongas(passenger)
        oldConga = passengerCongas[destination]
        oldConga.Lock.acquire()
        oldConga.Passengers.remove(passenger)
        oldConga.Lock.release()
        if len(oldConga.Passengers) == 0:
            self.DeleteConga(destination)
        return res

    # show all conga lines a passenger is part of (returns dict)
    def GetPassengerCongas(self, passenger):
        congas = {}
        for dest in self.Congas:
            conga = self.Congas[dest]
            if passenger in conga.Passengers:
                congas[dest] = conga
        return congas if congas else None

    def StartCongaCommand(self, conductor, destination, time):
        self.Lock.acquire()
        res = ""

        # convert time to time remaining
        cst = pytz.timezone('America/Chicago')
        currentTime = datetime.now(cst)
        diff = time - currentTime
        timeRemaining = round(diff.total_seconds()/60)

        newConga = Conga(conductor, destination, time, timeRemaining)
        err = self.AddConga(newConga)
        if err is not None:
            self.Lock.release()
            return err
        else:
            if res != "":
                res += "\n"
            res += f"{conductor} has started a conga line to {newConga.DisplayDestination} that leaves at {newConga.DepartureTime}! 🎊"
            if newConga.TimeRemaining == 1:
                res = "%s has started a conga line to %s that leaves in %d minute! 🏃🏽‍" % (conductor, newConga.DisplayDestination, newConga.TimeRemaining)
        self.Lock.release()
        worker = CongaWorker(self, newConga)
        worker.start()
        return res

# validate user inputted date/time
def validate(date_text):
    try:
        datetime.strptime(date_text, '%I:%M%p')
        return True
    except ValueError:
        return False
        raise ValueError("Incorrect data format, should be HH:MM[AM/PM] ⌛️")

# set the time of conga line
# if the time in HH:MM is after the present time, keep the datetime as current date
# otherwise, set to the following day
def GetTime(message):
    time = message[-1]
    if validate(time):
        cst = pytz.timezone('America/Chicago') # <- put your local timezone here
        now = datetime.now(cst)
        today_date = now.strftime("%Y-%m-%d")
        a = datetime.strptime(f'{today_date} {time}', "%Y-%m-%d %I:%M%p")
        a = cst.localize(a)
        if a < now:
            tomorrow = now + timedelta(days=1)
            tomorrow_date = tomorrow.strftime("%Y-%m-%d")
            a = datetime.strptime(f'{tomorrow_date} {time}', "%Y-%m-%d %I:%M%p")
            a = cst.localize(a)

        return a, None

    else:
        return None, "Incorrect data format, should be HH:MM[AM/PM] ⌛️"

# a hard worker
class CongaWorker(threading.Thread):
    def __init__(self, party, conga):
        threading.Thread.__init__(self)
        self.Party = party
        self.Conga = conga
        # Implement a separate counter (in seconds) to refresh the party more "instantaneously"
        self.TimeRemaining = conga.TimeRemaining * 60

    def run(self):
        while self.TimeRemaining >= 0:
            time.sleep(1)
            self.TimeRemaining -= 1
            if len(self.Conga.Passengers) == 0 or self.Conga.MapDestination not in self.Party.Congas:
                return
            message = ""
            if self.TimeRemaining == 60:
                message = "Reminder, the next conga line to %s leaves in one minute ⏰" % self.Conga.DisplayDestination
            elif self.TimeRemaining == 0:
                message = "The conga line to %s has left with %s on it! 🎉" % (self.Conga.DisplayDestination, self.Conga.PassengerString())
                self.Party.DeleteConga(self.Conga.MapDestination)
            if message != "":
                PostMessage(message)

# Main method to handle user requests
def Handler(party, user, message):
    message = message.split(' ')
    # /conga join starbucks
    command = message[0]  # help, active, join, start, or leave
    message = message[1:]  # additional information beyond the command
    notFound = "Your conga line/destination could not be found, please try again ☹️"
    if command == "help":
        return party.HelpCommand()
    elif command == "active" and len(message) == 0:
        return party.ActiveCongaCommand()
    elif command == "join" and len(message) >= 1:
        return party.JoinCongaCommand(user, ' '.join(message))
    elif command == "leave" and len(message) >= 1:
        # this is buggy atm
        return party.LeaveCongaCommand(user, ' '.join(message))
    elif command == "start" and len(message) >= 2:
        time, err = GetTime(message) # a datetime object
        destination = message[:-1]
        destination = ' '.join(destination)
        if err is not None:
            return err
        elif len(destination) == 0:
            return notFound
        else:
            return party.StartCongaCommand(user, destination, time)
    else:
        return "Your command could not be found or was malformed, please view the help message (/conga help) for more details 😬"


def PostMessage(message):
    webhook_url = config.webhook
    slack_data = {'text': message, 'response_type': 'in_channel'}
    response = requests.post(webhook_url, data=json.dumps(slack_data), headers={'Content-Type': 'application/json'})