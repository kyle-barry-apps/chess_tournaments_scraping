# Imports for gspread adding and formatting in google sheet
import gspread
from gspread_formatting import *
import gspread_dataframe as gd
from oauth2client.service_account import ServiceAccountCredentials

# Imports for getting data from uschess website
import requests
from bs4 import BeautifulSoup
from datetime import date
from datetime import timedelta
import pandas as pd

# Get today's date to use in URL for events past this day
today = date.today().strftime('%m%d%Y')

# Establish basic part of link to build hyperlinks to events
BASE_LINK = 'https://new.uschess.org/'

# URL for US chess events
URL = f'https://new.uschess.org/upcoming-tournaments?combine=&field_event_address_administrative_area=All&field_online_event_value=All&field_event_dates_occurrences%5Bmin%5D={today[0]}%2F{today[1]}%2F{today[2]}&field_event_dates_occurrences%5Bmax%5D=&field_banner_line_value%5BHeritage+Event%5D=Heritage+Event&field_banner_line_value%5BAmerican+Classic%5D=American+Classic&field_banner_line_value%5BGrand+Prix%5D=Grand+Prix&field_banner_line_value%5BEnhanced+Grand+Prix%5D=Enhanced+Grand+Prix&field_banner_line_value%5BJunior+Grand+Prix%5D=Junior+Grand+Prix&field_banner_line_value%5BNational+Championship+Event%5D=National+Championship+Event&field_banner_line_value%5BState+Championship+Event%5D=State+Championship+Event&field_banner_line_value%5BRegionals%5D=Regionals&field_geofield_proximity%5Bvalue%5D=&field_geofield_proximity%5Bsource_configuration%5D%5Borigin_address%5D=&page='

def get_data(url):
    '''Connects to US chess tournaments listing and collects data to be
    parsed'''

    page_count = 0
    events_dict_list = []

    while page_count < 5:

        page = requests.get(url+str(page_count))
        soup = BeautifulSoup(page.content, 'lxml')

        events = soup.find_all(class_='event-details')

        # Parsing through data in soup object to create something usable in a dataframe
        for event in events:
            event_dict = {}
            event_dict['name']= event.find(class_='title3').text

            if event.find(class_='date-recur-date'):
                event_dict['date'] = event.find(class_='date-recur-date').text.strip()
            elif event.find(class_='date-recur-interpretaton'):
                event_dict['date'] = event.find(class_='date-recur-interpretaton').text.strip()
            else:
                event_dict['date'] = 'empty'

            # Passing the date into a parser function to get a start and end date
            # and clean it up

            dates = parse_date(event_dict['date'])
            event_dict['start_date'] = dates[0]
            event_dict['end_date'] = dates[1]

            # Getting the rest of the data from the soup object
            location = event.find(class_='address').text
            city,state = location.split(',')
            event_dict['city'] = city.strip().title()
            event_dict['state'] = state.strip().title()
            event_dict['event_type'] = event.find(class_='banner-line h4').text
            event_dict['organizer'] = event.find(class_='organizer-name').text
            event_dict['link'] = BASE_LINK + event.find('a')['href']
            events_dict_list.append(event_dict)

        page_count += 1

    # Creating a pandas dataframe of the event data and cleaning it up
    df = pd.DataFrame(events_dict_list)
    cols = ['name', 'start_date', 'end_date', 'city', 'state', 'organizer','link']
    df = df[cols]
    df = df.iloc[2:,:]
    df.rename(columns={'name': 'Event Name', 'start_date': 'Start Date',
        'end_date': 'End Date', 'city': 'City', 'state': 'State', 'organizer':
        'Organizer', 'link': 'Link'}, inplace=True)
    df['Event Name'] = df['Event Name'].str.replace('annual', 'Annual')
    return df

def parse_date(date):
    '''Parsing the date given in the soup object to create a start and end date
    column in the dataframe'''

    if len(date.split('-'))==2:
        start_date = date.split('-')[0].strip()
        end_date = date.split('-')[1].strip()
    else:
        start_date = date
        end_date = 'n/a'

    dates = (start_date, end_date)

    return dates


def format_sheet():
    """Connect to google sheet and format it"""

    df = get_data(URL)

    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("US Chess Tournaments").sheet1

    gd.set_with_dataframe(sheet, df)

    df_len = len(df) + 1

    fmt = cellFormat(
    horizontalAlignment='CENTER',
    textFormat=textFormat(bold=True, fontSize=11)
    )

    fmt2 = cellFormat(
        backgroundColor=color(1, 0.9, 0.9),
        textFormat=textFormat(bold=False, foregroundColor=color(1, 0, 1)),
        horizontalAlignment='LEFT'
        )

    fmt3 = cellFormat(
        textFormat=textFormat(bold=True)
        )
    format_cell_ranges(sheet, [('A1:G1', fmt), (f'A2:G{str(df_len)}', fmt2),
        (f'A2:G{str(df_len)}', fmt3)])

    set_frozen(sheet, rows=1)
    set_column_widths(sheet, [('A', 400), ('B', 200), ('C', 200), ('D', 150),
        ('E', 150), ('F', 300), ('G', 900)])


format_sheet()
