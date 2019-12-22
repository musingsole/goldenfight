from urllib.parse import parse_qs
from bs4 import BeautifulSoup
from LambdaPage import LambdaPage
from HTTPS.murd_ddb import murd_ddb
from datetime import datetime, timedelta


memory = murd_ddb("GoldenFight")


###############################################################################
# Utilities

def get_page(PageName):
    with open("Pages/{}.html".format(PageName), "r") as f:
        page = f.read()

    return str(page)


###############################################################################
# Account Management Endpoints

def get_login_page(event=None, message=None):
    """ Generate WebApp Login Page

        The login page is the default landing location of the page. It
        allows a user to enter the system with a valid username and
        password. This page also provides access to account creation
        and account recovery.
    """
    print("Retreiving login page")
    raw_page = get_page("Login")

    message = message + "<br>" if message is not None else ""
    formatted_page = raw_page.replace("{message}", message)

    page = BeautifulSoup(formatted_page, 'html.parser')

    return str(page)


def goldenfight_console(message=""):
    print("Building GoldenFight Console")

    print("Gathering GoldenFight Status")
    status = memory.remember(tree="goldenfight_status", Limit=1, ScanIndexForward=False)[0]
    recent_status = status['TRUNK'] > (datetime.utcnow() - timedelta(hours=3)).strftime(TIME_FORMAT)
    print("Recent status: {}".format(recent_status))

    raw_page = get_page("GoldenFight")
    formatted_page = raw_page.replace("{message}", message)

    page = BeautifulSoup(formatted_page, 'html.parser')

    return str(page)


def login_submit(event):
    print("Handling Login Submission")
    # Check password
    try:
        print("Decoding credentials")
        body = parse_qs(event['body'])
        if type(body) is bytes:
            body = body.decode()
        password = body['password'][0]
    except Exception as e:
        print("Password decoding generated exception: {}".format(e))
        password = None

    if password != "GoldenFight":
        print("Password {} invalid".format(password))
        return 200, get_login_page(message="Incorrect Password")
    else:
        return 200, goldenfight_console()


def device_submit(event):
    print("Handling Device Submission")
    # Check password
    try:
        print("Decoding credentials")
        body = parse_qs(event['body'])
        if type(body) is bytes:
            body = body.decode()
        password = body['password'][0]
    except Exception as e:
        print("Password decoding generated exception: {}".format(e))
        password = None

    if password != "GoldenFightDeviceSubmit":
        print("Invalid password: {}".format(password))
        return 403
    else:
        print("Success")
        return 200


###############################################################################

def init_lambda_page():
    page = LambdaPage()

    page.add_endpoint('get', '/webapp', get_login_page, 'text/html')
    page.add_endpoint('post', '/webapp', login_submit, 'text/html')
    page.add_endpoint('post', '/webapp/device_submit', device_submit, 'application/json')

    return page


def lambda_handler(event, context):
    print("Received Event: {}".format(event))
    return init_lambda_page().handle_request(event)


if __name__ == "__main__":
    init_lambda_page().start_local()
