from . import app
from models import *
from forms import *
import requests
import json
from flask import session


def register(user, password):
    payload = {'user': user, 'password': password}
    call = apiCall('login', payload, '')
    if 'sid' in call:
        return call['sid']
    return None


def apiCall(command, json_payload, sid):
    url = 'https://' + app.config['SERVER'] + ':' + app.config['PORT'] + \
        '/web_api/' + command
    if 'sid' in session:
        request_headers = {
            'Content-Type': 'application/json',
            'X-chkp-sid': session['sid']
            }
    else:
        request_headers = {'Content-Type': 'application/json'}
    r = requests.post(
        url,
        data=json.dumps(json_payload),
        headers=request_headers,
        verify=app.config['VERIFY']
        )
    if r.status_code != 200:
        print '\nMESSAGE =>', r.json(), '\n'
    return r.json()


def instantiateObject(className):
    object_to_instantiate = globals()[className]
    return object_to_instantiate()


def instantiateForm(className, request):
    form_to_instantiate = globals()[className+'Form']
    return form_to_instantiate(request)


def orderList(list):
    return sorted(list, key = lambda element: (element['name']))


def redirect_url(default='home'):
    return request.args.get('next') or request.referrer or url_for(default)
