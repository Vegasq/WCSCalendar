from __future__ import print_function

import sys
import json
import logging
import urllib
import httplib2
try:
    from HTMLParser import HTMLParser
except:
    from html.parser import HTMLParser

from cliff.app import App
from cliff.commandmanager import CommandManager
from cliff.command import Command

from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery


class Handler(object):
    def __init__(self):
        self.day = None
        self.number = None
        self.month = None
        self.time = None
        self.title = None

    @property
    def dict(self):
        return {
            'summary': self.title,
            'location': '',
            'description': self.title,
            'start': {
                'dateTime': self.time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': self.time,
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 30},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

    def set_day_name(self, data):
        if not self.day:
            self.day = data

    def set_day_number(self, data):
        if not self.number:
            self.number = data

    def set_month_name(self, data):
        if not self.month:
            self.month = data

    def set_time(self, data):
        if not self.time:
            self.time = data

    def set_title(self, data):
        if not self.title:
            self.title = data

    def __str__(self):
        return "%s-%s-%s, %s, %s" % (self.month, self.number, self.day,
                                     self.time, self.title)

    def __unicode__(self):
        return self.__str__()

    def get_setter(self, class_name):
        setter_name = "set_" + class_name.replace('-', '_')
        if getattr(self, setter_name, False):
            return getattr(self, setter_name)


class Schedule(HTMLParser):
    wcs_schedule_url = "http://wcs.battle.net/sc2/en/schedule"

    @classmethod
    def get(cls):
        f = urllib.urlopen(cls.wcs_schedule_url)
        html = f.read()

        parser = Schedule()
        parser.feed(html)
        parser.close()

        return parser

    def __init__(self):
        HTMLParser.__init__(self)

        self.current_handler = None
        self.done_handlers = []

        self.call_me = None

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for name, value in attrs:
                if name == 'class' and value == 'full-schedule-item':
                    # Define new entry
                    if self.current_handler:
                        self.done_handlers.append(self.current_handler)
                    self.current_handler = Handler()

                if name == 'class' and value in ('day-name', 'day-number',
                                                 'month-name', 'title'):
                    self.call_me = self.current_handler.get_setter(value)

        if tag == 'time':
            for name, value in attrs:
                if name == 'datetime':
                    self.current_handler.set_time(value)

    def handle_endtag(self, tag):
        self.call_me = None

    def handle_data(self, data):
        if self.call_me:
            self.call_me(data)

    def __iter__(self):
        return iter(self.done_handlers)


class GoogleCalendar(object):
    calendar_name = ''
    credentials_json = ''
    calendar_owner = ''
    calendar_id = ''

    timezone = 'Atlantic/Reykjavik'
    scopes = ['https://www.googleapis.com/auth/calendar']

    @staticmethod
    def get_creator(calendar_name, calendar_owner, credentials_json):
        gc = GoogleCalendar()
        gc.calendar_name = calendar_name
        gc.credentials_json = credentials_json
        gc.calendar_owner = calendar_owner
        return gc

    @staticmethod
    def get_updater(config):
        with open(config, 'r') as fl:
            cfg = json.loads(fl.read())

        gc = GoogleCalendar()
        gc.calendar_id = cfg['calendar_id']
        gc.credentials_json = cfg['credentials_json']
        return gc

    def __init__(self):
        self._service = None

    @property
    def service(self):
        if not self._service:
            creds =  ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_json, self.scopes)
            http = creds.authorize(httplib2.Http())

            self._service = discovery.build('calendar', 'v3', http=http)
        return self._service

    def set_rights(self):
        """Make user owner of calendar, by default owner is service account
        and we cant see or change it."""
        rule = {
            'scope': {
                'type': 'user',
                'value': self.calendar_owner,
            },
            'role': 'owner'
        }

        created_rule = self.service.acl().insert(
            calendarId=self.calendar_id,
            body=rule).execute()

    def create_calendar(self):
        """Create empty calendar in Google"""
        calendar = {
            'summary': self.calendar_name,
            'description': self.calendar_name,
            'timeZone': self.timezone
        }

        created_calendar = self.service.calendars().insert(
            body=calendar).execute()

        self.calendar_id = created_calendar['id']

    def _get_events(self):
        all_events = []
        page_token = None
        while True:
            events = self.service.events().list(
                calendarId=self.calendar_id,
                pageToken=page_token).execute()
            for event in events['items']:
                all_events.append(event)
            page_token = events.get('nextPageToken')
            if not page_token:
                break
        return all_events

    def create_events(self):
        """Parse WCS site and create events in Google Calendar"""
        events = self._get_events()

        for i in Schedule.get():
            if (
                i.title in [ev['description'] for ev in events] and
                i.time in [ev['start']['dateTime'].replace('Z', '+00:00')
                           for ev in events]
            ):
                logging.info('Event "%s" already created' % i.title)
                continue
            event = self.service.events().insert(calendarId=self.calendar_id,
                                                 body=i.dict).execute()
            logging.info('Event %s created: %s' % (i.title,
                                                    event.get('htmlLink')))

    def dump_config(self):
        """Save config with new calendar id"""
        with open ('config.json', 'w') as fl:
            fl.write(json.dumps({
                'calendar_id': self.calendar_id,
                'credentials_json': self.credentials_json
            }))
        logging.info("Config saved as config.json")
        logging.info("Check your email for new calendar")
        logging.info("To fill this calendar with WCS events call wcsc update -h")


class CreateNewCalendar(Command):
    """Create fresh new calendar"""

    def get_parser(self, prog_name):
        parser = super(CreateNewCalendar, self).get_parser(prog_name)
        parser.add_argument('calendar_name')
        parser.add_argument('owner_email')
        parser.add_argument('service_credentials_json')
        return parser

    def take_action(self, parsed_args):
        gc = GoogleCalendar.get_creator(parsed_args.calendar_name,
                                        parsed_args.owner_email,
                                        parsed_args.service_credentials_json)
        gc.create_calendar()
        gc.set_rights()
        gc.dump_config()


class UpdateCalendar(Command):
    """Update exist calendar with newest events"""

    def get_parser(self, prog_name):
        parser = super(UpdateCalendar, self).get_parser(prog_name)
        parser.add_argument('config')
        return parser

    def take_action(self, parsed_args):
        gc = GoogleCalendar.get_updater(parsed_args.config)
        gc.create_events()


class WCSCalendarApp(App):
    def __init__(self):
        command = CommandManager('wcscalendar')

        super(WCSCalendarApp, self).__init__(
              description='WCS Calendar',
              version='0.1',
              command_manager=command,
              deferred_help=True,
        )

        commands = {
            'update': UpdateCalendar,
            'create': CreateNewCalendar
        }

        for k in commands:
            command.add_command(k, commands[k])

    def initialize_app(self, argv):
        self.LOG.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = WCSCalendarApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
