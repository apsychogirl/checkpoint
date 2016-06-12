from . import app
import api_response
from cp_mgmt_api import APIClient


# CheckpPoint library
api = APIClient()

# function for replacing - with _ in lists and dicts
def underscore(data):
    if isinstance(data, list):
        for element in data:
            for key, value in element.iteritems():
                element[key.replace('-', '_')] = element.pop(key)
    if isinstance(data, dict):
        for key, value in data.iteritems():
            data[key.replace('-', '_')] = data.pop(key)
    return data


class APIObject:

    #
    # initialize class
    #
    def __init__(self, name):
        self.name = app.config['ID_COLE'] + name
        self.uid = None
        self.kind = None

    def add(self, **kwargs):
        payload = {'name': self.name}
        for element in kwargs:
            payload[element.replace('_', '-')] = kwargs[element]
        return api.api_call('add-' + self.kind, payload)

    def add_to_group(self, action, group_name):
        payload = {
            'name': app.config['ID_COLE'] + group_name,
            'members': {
                'add': self.name
                }
            }
        return api.api_call(action, payload)

    def show(self, details_level='standard'):
        payload = {'name': self.name, 'details-level': details_level}
        call = api.api_call('show-' + self.kind, payload).data
        return underscore(call)

    def show_members(self):
        call = self.show('full')
        underscore(call['members'])
        return self.order(call['members'])

    def order(self, list, field='name'):
        return sorted(list, key = lambda element: (element[field]))

    def edit(self):
        pass

    def delete(self):
        payload = {'name': self.name}
        return api.api_call('delete-' + self.kind, payload)

    def delete_from_group(self, action, group_name):
        payload = {
            'name': app.config['ID_COLE'] + group_name,
            'members': {
                'remove': self.name
                }
            }
        return api.api_call(action, payload)

    def where_used(self):
        payload = {'name': self.name}
        call = api.api_call('where-used', payload).data
        return call['used-directly']['total']


class Group(APIObject):

    #
    # initialize class
    #
    def __init__(self, name):
        APIObject.__init__(self, name)
        self.kind = 'group'


class ApplicationGroup(APIObject):

    #
    # initialize class
    #
    def __init__(self, name):
        APIObject.__init__(self, name)
        self.kind = 'application-site-group'


class Host(APIObject):

    #
    # initialize class
    #
    def __init__(self, name):
        APIObject.__init__(self, name)
        self.kind = 'host'


class ApplicationSite(APIObject):

    #
    # initialize class
    #
    def __init__(self, name):
        APIObject.__init__(self, name)
        self.kind = 'application-site'

