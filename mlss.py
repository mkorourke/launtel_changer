#!/usr/bin/env python3
"""
Purpose: Script for Launtel Speed Info and Change
"""
import argparse
import getpass
import logging
import sys
import signal
import os
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import parse_qs
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from mechanize import Browser
from mechanize import Link
from rich import box
from rich.table import Table
from rich.console import Console

_USERNAME = ''
_PASSWORD = ''

_BASE_URL = 'https://residential.launtel.net.au'
_LOGIN_URL = f'{_BASE_URL}/login'
_SIGNOUT_URL = f'{_BASE_URL}/logout_user'
_MODIFY_SERVICE_URL = f'{_BASE_URL}/service'
_ISP = "Launtel"
_LOGIN_SUCCESSFUL = False
_COMPLETE = False

_COMMIT = False
_LATEST = False
_SHAPER = False
_PSID_VALID = False
_PSID = ''

_SERVICE_DICT = {}
_SPEEDS_DICT = {}
_USERID = ''
_AVCID = ''
_C_PSID = ''
_UNPAUSE = ''
_SERVICE_ID = ''
_UPGRADE_OPTIONS = ''
_DISCOUNT_CODE = ''
_LOCID = ''
_COAT = ''


def signal_handler(sig, frame):
    """
    Capture Ctrl+C and logout if login was successful
    """
    logging.debug('Signal captured: sig: %s frame: %s', sig, frame)
    print('\nYou pressed Ctrl-C, Quiting.')
    if _LOGIN_SUCCESSFUL:
        logout()
    else:
        sys.exit(0)


def get_credentials(prompt):
    """
    Generic funtion to prompt for credentials
    """
    if sys.stdin.isatty():
        print(prompt)
        if _USERNAME == '':
            username = input('Username: ')
        else:
            username = _USERNAME
            print(f'Username: {username}')
        if _PASSWORD == '':
            password = getpass.getpass('Password: ')
        else:
            password = _PASSWORD
    else:
        if _USERNAME == '':
            username = sys.stdin.readline().rstrip()
        else:
            username = _USERNAME
            print(f'Username: {username}')
        if _PASSWORD == '':
            password = sys.stdin.readline().rstrip()
        else:
            password = _PASSWORD
    return [username, password]


def get_browser():
    """
    Create _browser and set desired defaults
    """
    browser = Browser()
    browser.set_handle_robots(False)   # ignore robots
    browser.set_handle_refresh(False)  # can sometimes hang without this
    browser.addheaders = [('User-agent', 'Firefox')]
    return browser


def logout():
    """
    Logout of Launtel
    """
    if _SHAPER is True:
        logging.info(
            '%s shaper change complete status is %s, signing out.',
            _ISP, _COMPLETE)
    else:
        logging.info(
            '%s speed change complete status is %s, signing out.',
            _ISP, _COMPLETE)
    _br.follow_link(Link(
        base_url=_BASE_URL,
        url=_SIGNOUT_URL,
        text='Sign Out',
        tag='a',
        attrs=[
            ('href',
             _SIGNOUT_URL)]))
    logging.debug('url:%s', _br.geturl())
    sys.exit()


def login():
    """
    Login to Launtel
    """
    _br.open(_LOGIN_URL)
    _br.select_form(id='login-form')
    _br.form['username'] = _USERNAME
    _br.form['password'] = _PASSWORD
    _login_soup = BeautifulSoup(_br.submit().read(), features='lxml')
    _login_status = _login_soup.find(
        'div', attrs={
            'class': 'alert-content'}).text.strip()
    if _login_status == 'Sorry incorrect login details':
        logging.error('Login Failure.')
        logging.debug('%s alert content : %s', _ISP, _login_status)
        sys.exit()
    logging.debug('Login Successful.')
    return True


def check_latest(_latest_psid_btn):
    """
    Check latest pricing options exist
    """
    if _latest_psid_btn is not None:
        logging.debug('%s available', _latest_psid_btn.text)
        return True
    logging.debug('No latest psid options')
    return False


def submit_service_modification():
    """
    Prepare the service modification URL and submit modification confirmation if Commit is True
    """
    _confirm_service_url = (f'/confirm_service?userid={_USERID}'
                            f'&psid={_PSID}&'
                            f'unpause={_UNPAUSE}&'
                            f'service_id={_SERVICE_ID}&'
                            f'upgrade_options={_UPGRADE_OPTIONS}&'
                            f'discount_code={_DISCOUNT_CODE}&'
                            f'avcid={_AVCID}&'
                            f'locid={_LOCID}&'
                            f'coat={_COAT}')
    _confirm_service_link = Link(
        base_url=_BASE_URL,
        url=_confirm_service_url,
        text='Looks great - update it!',
        tag='a',
        attrs=[
            ('href',
             _confirm_service_url)])
    _br.follow_link(_confirm_service_link)
    logging.debug('url:%s', _br.geturl())
    if _COMMIT is True:
        _br.select_form(name='confirm_service')
        _confirm_soup = BeautifulSoup(_br.submit().read(), features='lxml')
        logging.debug('url:%s', _br.geturl())
        _confirm_status = _confirm_soup.find(
            'dl', attrs={'class': 'service-dl'}).text.strip()
        if 'Change in progress' in _confirm_status:
            logging.info('%s status is "Change in progress".', _ISP)
        else:
            logging.error(
                '%s status is not "Change in progress", please check portal.',
                _ISP)
            logout()


def check_psid():
    """
    Return True if the PSID is valid
    """
    _psid_valid = False
    for _key in _SPEEDS_DICT:
        if _PSID == _key:
            if _PSID == _C_PSID and _LATEST is False:
                logging.error("Requested psid is not valid.")
            else:
                logging.debug('Requested psid is valid.')
                _psid_valid = True
    return _psid_valid


def get_shaper_control(_br):
    """
    Get shaper control info
    """
    _soup = BeautifulSoup(_br.follow_link(
        text='Show Advanced Info'), features='lxml')
    logging.debug('url:%s', _br.geturl())
    _queue_type = None
    _shaperdown_control = None
    _shaperup_control = None
    _shaperdown_cont = 'override'  # always override to keep this simple
    _shaperup_cont = 'override'
    if _soup.find('input', attrs={'name': 'queue_type', 'value': 'shape'}).get('checked') is not None:
        _queue_type = 'shape'
    elif _soup.find('input', attrs={'name': 'queue_type', 'value': 'police'}).get('checked') is not None:
        _queue_type = 'police'

    if _soup.find('input', attrs={'name': 'shaperup_control', 'id': 'shaperup_control_none'}).get('checked') is not None:
        _shaperup_control = 'none'
    elif _soup.find('input', attrs={'name': 'shaperup_control', 'id': 'shaperup_control_default'}).get('checked') is not None:
        _shaperup_control = 'default'
    elif _soup.find('input', attrs={'name': 'shaperup_control', 'id': 'shaperup_control_override'}).get('checked') is not None:
        _shaperup_control = 'override'

    if _soup.find('input', attrs={'name': 'shaperdown_control', 'id': 'shaperdown_control_none'}).get('checked') is not None:
        _shaperdown_control = 'none'
    elif _soup.find('input', attrs={'name': 'shaperdown_control', 'id': 'shaperdown_control_default'}).get('checked') is not None:
        _shaperdown_control = 'default'
    elif _soup.find('input', attrs={'name': 'shaperdown_control', 'id': 'shaperdown_control_override'}).get('checked') is not None:
        _shaperdown_control = 'override'

    _shaperdown_max = _soup.find(
        'input', attrs={'id': 'shaperdown_speed'}).get('max')
    _shaperdown_min = _soup.find(
        'input', attrs={'id': 'shaperdown_speed'}).get('min')
    _shaperdown_speed = _soup.find(
        'input', attrs={'id': 'shaperdown_speed'}).get('value')

    _shaperup_max = _soup.find(
        'input', attrs={'id': 'shaperup_speed'}).get('max')
    _shaperup_min = _soup.find(
        'input', attrs={'id': 'shaperup_speed'}).get('min')
    _shaperup_speed = _soup.find(
        'input', attrs={'id': 'shaperup_speed'}).get('value')

    _shaper_control = [{"key": "queue_type", "value": _queue_type},
                       {"key": "shaperdown_cont", "value": _shaperdown_cont},
                       {"key": "shaperdown_control", "value": _shaperdown_control},
                       {"key": "shaperdown_speed", "value": _shaperdown_speed},
                       {"key": "shaperup_cont", "value": _shaperup_cont},
                       {"key": "shaperup_control", "value": _shaperdown_control},
                       {"key": "shaperup_speed", "value": _shaperup_speed}]

    _shaper_control_url = _soup.find(
        'form', attrs={'name': 'form-shaping'}).get('action')

    _shaper_dict = {}
    _shaper_dict = {
        'queue_type': _queue_type,
        'shaperdown_cont': _shaperdown_cont,
        'shaperdown_control': _shaperdown_control,
        'shaperdown_speed': _shaperdown_speed,
        'shaperup_cont': _shaperup_cont,
        'shaperup_control': _shaperup_control,
        'shaperup_speed': _shaperup_speed,
        'shaperdown_max': _shaperdown_max,
        'shaperdown_min': _shaperdown_min,
        'shaperup_max': _shaperup_max,
        'shaperup_min': _shaperup_min,
        'shaper_control_url': _shaper_control_url,
    }

    return _shaper_dict


def get_speeds_table(_title):
    """
    Create a new speeds table
    """
    table = Table(
        show_header=True,
        header_style='bold magenta',
        title=_title,
        box=box.SQUARE,
        show_lines=True)
    table.add_column('PSID')
    table.add_column('SPEED')
    table.add_column('SPEND')
    return table


def print_speeds_table():
    """
    Get the speeds table
    """
    if _LATEST is True:
        _speeds_title = f'Latest {_ISP} Speeds'
    else:
        _speeds_title = f'{_ISP} Speeds'
    _speeds_table = get_speeds_table(_speeds_title)
    for _key, values in _SPEEDS_DICT.items():
        speed_psid = _key
        speed_name = values['name']
        speed_daily_spend = values['spend']
        if _key == _C_PSID and _LATEST is False:
            speed_psid = f'[bright_green]{speed_psid}[/bright_green]'
            speed_name = f'[bright_green]{speed_name}[/bright_green]'
            speed_daily_spend = f'[bright_green]{speed_daily_spend}[/bright_green]'
        elif _key == _C_PSID:
            speed_psid = f'[bright_yellow]{speed_psid}[/bright_yellow]'
            speed_name = f'[bright_yellow]{speed_name}[/bright_yellow]'
            speed_daily_spend = f'[bright_yellow]{speed_daily_spend}[/bright_yellow]'
        _speeds_table.add_row(*(speed_psid, speed_name, speed_daily_spend))

    _console = Console()
    _console.print(_speeds_table)


def get_speeds_dict(soup):
    """
    Get a dict of speeds
    """
    _speeds = soup.find_all(
        'span', attrs={'data-value': True})
    _speeds_dict = {}

    for speed in _speeds:
        speed_name = speed.find(
            'div', attrs={
                'class': 'col-sm-4'}).text.strip()
        speed_psid = speed.get('data-value')
        speed_daily_spend = speed.get('data-plancharge')
        _speeds_dict[speed_psid] = {
            'name': speed_name,
            'spend': speed_daily_spend}

    return _speeds_dict


def get_service_dict(soup):
    """
    Get a dict of the service
    """
    # Find all the values utilised within Launtels service modification
    # and necessary for next services of validations and script steps
    _userid = soup.find(
        'input', attrs={'name': 'userid'}).get('value')
    _c_psid = soup.find(
        'input', attrs={'name': 'psid'}).get('value')
    _unpause = soup.find(
        'input', attrs={'name': 'unpause'}).get('value')
    _service_id = soup.find(
        'input', attrs={
            'name': 'service_id'}).get('value')
    _upgrade_options = soup.find(
        'span', attrs={'class': 'rollover list-group-item'}).get('value')
    _discount_code = ''  # /check_discount/0/{_AVCID}/
    _avcid = soup.find(
        'input', attrs={'name': 'avcid'}).get('value')
    _locid = soup.find(
        'input', attrs={'name': 'locid'}).get('value')
    _coat = soup.find('input', attrs={'name': 'coat'}).get('value')

    _service_dict = {}
    _service_dict[_avcid] = {
        'userid': _userid,
        'psid': _c_psid,
        'unpause': _unpause,
        'service_id': _service_id,
        'upgrade_options': _upgrade_options,
        'discount_code': _discount_code,
        'locid': _locid,
        'coat': _coat}

    return _service_dict


def print_active_service_status():
    """
    Check active service status
    """
    _services_soup = BeautifulSoup(
        _br.follow_link(
            text='Services').read(),
        features='lxml')
    logging.debug('url:%s', _br.geturl())
    _services_status = _services_soup.find(
        'dl', attrs={'class': 'service-dl'}).text.strip()

    if 'Active' in _services_status:
        logging.debug('%s service status is Active.', _ISP)
    else:
        logging.debug('%s service status is not Active.', _ISP)


def print_cookies():
    """
    Print _browser session_id cookie
    """
    _cookies = _br._ua_handlers['_cookies'].cookiejar  # pylint: disable=protected-access
    for cookie in _cookies:
        if cookie.name == "session_id":
            _session_id = cookie.value
            logging.debug('%s=%s', cookie.name, _session_id)


signal.signal(signal.SIGINT, signal_handler)

parser = argparse.ArgumentParser(
    description='Launtel Speed Info and Change CLI')
# add arguments to the parser
parser.add_argument('-p', '--psid', help='Launtel Speed PSID')
parser.add_argument(
    '-c',
    '--commit',
    action='store_true',
    help=f'Commit to {_ISP}.')
parser.add_argument(
    '-l',
    '--latest',
    action='store_true',
    help='Use latest psid options.')
parser.add_argument(
    '-s',
    '--shaper',
    action='store_true',
    help='Shaper control.')
parser.add_argument(
    '-d',
    '--debug',
    action='store_true',
    help='Debug logging to stderr.')

# parse the arguments
args = parser.parse_args()

if args.debug is True:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logging.debug('Debug is True.')
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger = logging.getLogger(__name__)

# get the arguments value for psid
if args.psid is not None:
    _PSID = args.psid

# get the arguments value for commit
if args.commit is True:
    logging.debug('Commit is True.')
    _COMMIT = True
else:
    logging.debug('Commit is False.')

# get the arguments value for commit
if args.latest is True:
    logging.debug('Use latest psid options is True.')
    _LATEST = True
else:
    logging.debug('Use latest psid options is False.')

# get the arguments value for commit
if args.shaper is True:
    logging.debug('Shaper control is True.')
    _SHAPER = True
else:
    logging.debug('Shaper control is False.')

# Load variables from .env file
load_dotenv()
# Check and utilise ENV variables for user credentials
_USERNAME = os.getenv("LAUNTEL_USERNAME")
_PASSWORD = os.getenv("LAUNTEL_PASSWORD")

# if ENV not set, interactivly prompt for user credentials
if _USERNAME == '' or _PASSWORD == '':
    logging.debug('%s username or password not set.', _ISP)
    _isp_credentials = get_credentials(f'Enter your {_ISP} credentials:')
    _USERNAME = _isp_credentials[0]
    _PASSWORD = _isp_credentials[1]

if _USERNAME == '' or _PASSWORD == '':
    logging.error('Quiting, %s username or password not set.', _ISP)
    sys.exit()

_br = get_browser()
_LOGIN_SUCCESSFUL = login()
if args.debug is True:
    print_cookies()
    print_active_service_status()
# Make sure we are at the correct starting point
_br.follow_link(text='Services')
logging.debug('url:%s', _br.geturl())
parsed_url = urlparse(_br.find_link(text='Show Advanced Info').url)
_USERID = parse_qs(parsed_url.query)['userid'][0]
_AVCID = parse_qs(parsed_url.query)['avcid'][0]

if _SHAPER is True:
    _SHAPER_DICT = get_shaper_control(_br)
    print(f'Queue Type: {_SHAPER_DICT["queue_type"]}')
    print(f'Down Control: {_SHAPER_DICT["shaperdown_control"]}')
    print(
        f'Down Speed: Max: {_SHAPER_DICT["shaperdown_max"]} Min: {_SHAPER_DICT["shaperdown_min"]} Value: {_SHAPER_DICT["shaperdown_speed"]}')
    print(f'Up Control: {_SHAPER_DICT["shaperup_control"]}')
    print(
        f'Up Speed: Max: {_SHAPER_DICT["shaperup_max"]} Min: {_SHAPER_DICT["shaperup_min"]} Value: {_SHAPER_DICT["shaperup_speed"]}')
    _SHAPER_CONTROL_URL = _BASE_URL + _SHAPER_DICT["shaper_control_url"]
    print(_SHAPER_CONTROL_URL)
    if _COMMIT is False:
        _COMPLETE = False
        logout()
    if _COMMIT is True:
        # Define _SHAPER_CONTROL_DATA as a dictionary directly
        _SHAPER_CONTROL_DICT = {
            "queue_type": _SHAPER_DICT["queue_type"],
            "shaperdown_cont": _SHAPER_DICT["shaperdown_cont"],
            "shaperdown_control": _SHAPER_DICT["shaperdown_control"],
            "shaperdown_speed": _SHAPER_DICT["shaperdown_max"],
            "shaperup_cont": _SHAPER_DICT["shaperup_cont"],
            "shaperup_control": _SHAPER_DICT["shaperup_control"],
            "shaperup_speed": _SHAPER_DICT["shaperup_max"]
        }
        # URL-encode the form data and Post
        _br.open(_SHAPER_CONTROL_URL, urlencode(_SHAPER_CONTROL_DICT))
        _COMPLETE = True  # If we get to here Complete is considered True
        logout()


_MODIFY_SERVICE_URL = f'{_MODIFY_SERVICE_URL}?avcid={_AVCID}&userid={_USERID}'
_soup = BeautifulSoup(
    _br.follow_link(Link(
        base_url=_BASE_URL,
        url=_MODIFY_SERVICE_URL,
        text='Modify Service',
        tag='a',
        attrs=[
            ('href',
             _MODIFY_SERVICE_URL)])).read(),
    features='lxml')
logging.debug('url:%s', _br.geturl())
_br.select_form(name='manage_service')

# Check if new pricing or plan options exist
if _LATEST is True and check_latest(
    _soup.find(
        "button", {
            "onclick": "showLatest()"})) is True:
    _LATEST_PSID_URL = f'{_MODIFY_SERVICE_URL}&latest=1'
    _soup = BeautifulSoup(
        _br.follow_link(Link(
            base_url=_BASE_URL,
            url=_LATEST_PSID_URL,
            text='Show Latest Pricing Options',
            tag='a',
            attrs=[
                ('href',
                 _LATEST_PSID_URL)])).read(),
        features='lxml')
    logging.debug('url:%s', _br.geturl())
    _br.select_form(name='manage_service')

# Get a dict with all the service information
_SERVICE_DICT = get_service_dict(_soup)
# Set the remaining required variables
_C_PSID = _SERVICE_DICT[_AVCID]['psid']
_UNPAUSE = _SERVICE_DICT[_AVCID]['unpause']
_SERVICE_ID = _SERVICE_DICT[_AVCID]['service_id']
_UPGRADE_OPTIONS = _SERVICE_DICT[_AVCID]['upgrade_options']
_DISCOUNT_CODE = _SERVICE_DICT[_AVCID]['discount_code']
_LOCID = _SERVICE_DICT[_AVCID]['locid']
_COAT = _SERVICE_DICT[_AVCID]['coat']
# Get speeds and print
_SPEEDS_DICT = get_speeds_dict(_soup)
print_speeds_table()

# check and cater for non-interactive eg. cron based entry of PSID
if _PSID != '':
    _PSID_VALID = check_psid()
    # if non-interactive PSID is false, logout
    if _PSID_VALID is False:
        logout()

# check and cater for interactive entry of PSID, re-prompt if PSID is invalid
while _PSID_VALID is False:
    _PSID = input('Please enter psid: ')
    _PSID_VALID = check_psid()

if _PSID_VALID is True:
    submit_service_modification()
else:
    logging.error("Requested psid is not valid.")
    logout()

_COMPLETE = True  # If we get to here Complete is considered True
logout()
