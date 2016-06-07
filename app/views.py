# -*- coding: utf-8 -*-

from flask import request, render_template, redirect, url_for, flash, session
from functools import wraps
import webbrowser

from . import app
from models import User
from helpers import *
from cp_mgmt_api import APIClient


# start using CheckpPoint library
api = APIClient()


@app.route('/')
def home():
    '''
    home
    ------------------------------------------------------------------
    performs a login call to the server and stores username in session

    return: renders home page if success or login page if error

    '''
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    login
    ------------------------------------------------------------------
    performs a login call to the server and stores username in session

    return: renders home page if success or login page if error

    '''
    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate():
        login = api.login(
            app.config['SERVER'],
            form.username.data,
            form.password.data
            )
        # check login
        if 'sid' in login.data:
            # store username in session for header and login_required
            session['username'] = form.username.data
            flash('Usuari registrat')
            return render_template('home.html')
        else:
            flash(u"Error d'inici de sessió, torneu a intentar-ho.")

    return render_template('login.html', request=request, form=form)


def login_required(f):
    '''
    login requred
    ---------------------------------------------------------------
    wraps the functions that need the user to be logged in to run

    arguments:
        f: the wrapped function itself

    return: renders home page if success or login page if error

    '''
    @wraps(f)
    def wrap(*args, **kwargs):
        # if we have a session username
        if 'username' in session:
            # and there is an status-code when we ask to the server
            call = api.api_call('show-login-message')
            if hasattr(call, 'status_code'):
                # and this status_code is 200
                if call.status_code == 200:
                    # then go on
                    return f(*args, **kwargs)
            # either there isn't an status_code but is not 200 or there is not
            # any status_code at all, probably expired, let's clear the session
            session.clear()
            return render_template('session-expired.html')
        # We don't have a session username, so let's get one
        flash(u'Necessiteu estar registrats per accedir a aquesta opció')
        return redirect(url_for('login'))
    return wrap


@app.route('/logout')
def logout():
    '''
    logout
    -----------------------------------------------------------
    performs a logout call to the server and clears the session

    return: redirect to home

    '''
    api.api_call('logout')
    session.clear()
    flash('Usuari desconnectat')
    return redirect(url_for('home'))


@app.route('/block-access')
@login_required
def blockAccess():
    '''
    block access
    --------------------------------------------------------------------------
    shows the group and the application-site-group for blocking hosts and URLs

    return: renders the block access page

    '''
    # call for group
    payload = {'name': app.config['ID_COLE'] + 'GRUP_LlistaNegraEquips'}
    group = api.api_call('show-group', payload).data
    # call for application group
    payload = {'name': app.config['ID_COLE'] + app.config['LLISTA_NEGRA']}
    app_list = api.api_call('show-application-site-group', payload).data

    return render_template(
        'block-access.html',
        group=group,
        app_list=app_list,
        url_back='blockAccess'
        )


@app.route('/show-group-members/<group_id>/<url_back>')
@login_required
def showGroupMembers(group_id, url_back):
    '''
    show groups members
    --------------------------------------------------------------------------
    shows the hosts of each group, allows the user to add a new host or net to
    the group, either selecting it from the list or creating a new one

    arguments:
        group_id: the id number of the group

    return: renders the show group members page

    '''
    form_new_host = HostForm(request.form)
    form_select_host = HostSelectForm(request.form)

    # call for group members
    hosts = []
    payload = {'uid': group_id, 'details-level': 'full'}
    call = api.api_call('show-group', payload).data
    for element in call['members']:
        # select the hosts
        if element['type'] == 'host':
            object = {
                'uid': element['uid'],
                'name': element['name'][10:],
                'ipv4_address': element['ipv4-address']
                }
            hosts.append(object)

    # call for host choices
    options = [('', 'seleccionar')]
    call = api.api_call('show-hosts').data
    for element in call['objects']:
        already_in_group = False
        for host in hosts:
            if element['name'][10:] == host['name']:
                already_in_group = True
        if not already_in_group:
            options.append((element['name'], element['name'][10:]))
    form_select_host.name.choices = options

    # order lists by name
    hosts = orderList(hosts)

    return render_template(
        'show-group-members.html',
        request=request,
        hosts=hosts,
        form_new_host=form_new_host,
        form_select_host=form_select_host,
        group_id=group_id,
        url_back=url_back
        )


@app.route('/show-app-group-content/<app_list>/<url_back>')
@login_required
def showAppGroupContent(app_list, url_back):
    '''
    show application-site group content
    -----------------------------------------------------------------------
    shows application group content when selecting a source in the dropdown
    menu while adding a new rule

    argument:
        group_id: the group that's been selected

    return: renders the show application group content page just below the
        select

    '''
    form_new_app = ApplicationSiteForm(request.form)
    form_select_app = ApplicationSelectForm(request.form)

    # call for application group members
    apps = []
    payload = {'uid': app_list, 'details-level': 'full'}
    call = api.api_call('show-application-site-group', payload).data
    for element in call['members']:
        objects = {
            'uid': element['uid'],
            'name': element['name'][10:],
            'url_list': element['url-list'][0]
            }
        apps.append(objects)

    # call for app choices
    options = [('', 'seleccionar')]
    payload = {'name': app.config['ID_COLE'] + app.config['LLISTA_GENERAL']}
    call = api.api_call('show-application-site-group', payload).data
    for element in call['members']:
        if element['name'][:5] == app.config['ID_COLE']:
            already_in_group = False
            for appl in apps:
                if element['name'][10:] == appl['name']:
                    already_in_group = True
            if not already_in_group:
                options.append((element['name'], element['name'][10:]))
    form_select_app.name.choices = options

    # order lists by name
    apps = orderList(apps)

    return render_template(
        'show-app-group-content.html',
        form_select_app=form_select_app,
        form_new_app=form_new_app,
        apps=apps,
        app_list=app_list,
        url_back=url_back
        )


@app.route('/add-existing-host/<group_id>/<url_back>', methods=['POST'])
@login_required
def addExistingHost(group_id, url_back):
    '''
    add existing host
    ----------------------------------------------------------------
    adds an existing host to a group

    arguments:
        host_id: the id of the host to be added to the group
        group_id: the id of the group where the host has to be added

    return: when POST adds the host to the group, if NO renders the
        show groups page

    '''
    form = HostSelectForm(request.form)
    # call for adding the host to the group
    payload = {
        'uid': group_id,
        'members': {
            'add': form.name.data
            }
        }
    api.api_call('set-group', payload)
    api.api_call('publish')
    flash('Equip afegit')
    return redirect(url_for(url_back))


@app.route('/add-host/<group_id>/<url_back>', methods=['POST'])
@login_required
def addHost(group_id, url_back):
    '''
    add host
    ---------------------------------------------------------------------------
    adds a new host inside a group

    arguments:
        group_id: the id number of the group where the host has to be added

    return: if YES creates the host and adds it to the group, if NO renders the
        show groups page

    '''
    form = HostForm(request.form)

    if form.validate():
        # call for creating the host
        payload = {
            'name': app.config['ID_COLE'] + 'HOST_' + form.name.data,
            'ipv4-address': form.ipv4_address.data
            }
        api.api_call('add-host', payload)
        # call for adding the host to the group
        payload = {
            'uid': group_id,
            'members': {
                'add': app.config['ID_COLE'] + 'HOST_' + form.name.data
                }
            }
        api.api_call('set-group', payload)
        api.api_call('publish')
        flash('Equip afegit')
        return redirect(url_for(url_back))

    return render_template('new-host.html', form=form)


@app.route('/delete-host/<group_id>/<object_uid>/<url_back>', methods=['GET', 'POST'])
@login_required
def deleteHost(group_id, object_uid, url_back):
    '''
    delete host
    ---------------------------------------------------------------------
    deletes an existing host

    arguments:
        group_id: the id number of the group where the host belongs
        object_uid: the uid number of the host

    return: if POST deletes the host, if GET renders the delete host page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('show-host', payload).data
    object = {
        'uid': call['uid'],
        'name': call['name'][10:],
        'ipv4_address': call['ipv4-address']
        }

    if request.method == 'POST':

        # call for removing the host from the group
        payload = {
            'uid': group_id,
            'members': {
                'remove': app.config['ID_COLE'] + 'HOST_' + object['name']
                }
            }
        call = api.api_call('set-group', payload)

        # check if used in more places than its group
        used = whereUsed(object_uid)
        if used > 0:
            flash(u"L'equip pertany a més grups i no es pot eliminar")
            return redirect(url_for(url_back))

        # call for deleting the host
        payload = {'uid': object_uid}
        api.api_call('delete-host', payload)

        api.api_call('publish')
        flash('Equip eliminat')
        return redirect(url_for(url_back))

    return render_template(
        'delete-host.html',
        group_id=group_id,
        object=object,
        url_back=url_back
        )


@app.route('/set-host/<object_uid>/<url_back>', methods=['GET', 'POST'])
@login_required
def setHost(object_uid, url_back):
    '''
    edit host (to be continued)
    ---------------------------------------------------------------------------
    edits an existing host

    arguments:
        object_uid:

    return: renders the show group members page

    '''
    form = HostForm(request.form)
    payload = {'uid': object_uid}
    call = api.api_call('show-host', payload).data
    object = {
        'uid': object_uid,
        'name': call['name'][10:],
        'ipv4_address': call['ipv4-address']
        }

    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'new-name': app.config['ID_COLE'] + 'HOST_' + form.name.data,
            'ipv4-address': form.ipv4_address.data
            }
        api.api_call('set-host', payload)
        api.api_call('publish')
        flash('Equip editat!')
        return redirect(url_for(url_back))
    else:
        return render_template(
            'edit-host.html',
            object=object,
            form=form,
            url_back=url_back
            )


@app.route('/add-existing-application/<app_list>/<url_back>', methods=['POST'])
@login_required
def addExistingApplication(app_list, url_back):
    '''
    add existing application
    ----------------------------------------------------------------
    adds an existing host to a group

    arguments:
        host_id: the id of the host to be added to the group
        group_id: the id of the group where the host has to be added

    return: when POST adds the host to the group, if NO renders the
        show groups page

    '''
    form = ApplicationSelectForm(request.form)
    # call for adding the host to the group
    payload = {
        'uid': app_list,
        'members': {
            'add': form.name.data
            }
        }
    api.api_call('set-application-site-group', payload)
    api.api_call('publish')
    flash('URL afegida')
    return redirect(url_for(url_back))


@app.route('/add-application-site/<app_list>/<url_back>', methods=['POST'])
@login_required
def addApplicationSite(app_list, url_back):
    '''
    add application-site
    --------------------------------------------------------------------------
    add a new application-site inside a group

    arguments:
        group_id: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    form = ApplicationSiteForm(request.form)
    if form.validate():

        # call for adding the application
        payload = {
            'name': app.config['ID_COLE'] + 'APPL_' + form.name.data,
            'url-list': form.url_list.data,
            'primary-category': 'Custom_Application_Site'  # required
        }

        api.api_call('add-application-site', payload)

        # call for adding the application to the group
        payload = {
            'uid': app_list,
            'members': {
                'add': app.config['ID_COLE'] + 'APPL_' + form.name.data
                }
            }
        api.api_call('set-application-site-group', payload)

        # call for adding the application to general group
        payload = {
            'name': app.config['ID_COLE'] + app.config['LLISTA_GENERAL'],
            'members': {
                'add': app.config['ID_COLE'] + 'APPL_' + form.name.data
                }
            }
        api.api_call('set-application-site-group', payload)

        api.api_call('publish')
        flash(u'URL afegida')
        return redirect(url_for(url_back))
    else:
        return render_template(
            'new-application-site.html',
            form=form,
            app_list=app_list,
            url_back=url_back
            )


@app.route(
    '/delete-application-site/<app_list>/<object_uid>/<url_back>',
    methods=['GET', 'POST']
    )
@login_required
def deleteApplicationSite(app_list, object_uid, url_back):
    '''
    delete application-site
    --------------------------------------------------------------------------
    delete an existing application-site

    arguments:
        app_list: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('show-application-site', payload).data
    object = {
        'uid': call['uid'],
        'name': call['name'][10:],
        'url_list': call['url-list'][0],
        }

    if request.method == 'POST':

        # call for removing the application from the application group
        payload = {
            'uid': app_list,
            'members': {
                'remove': app.config['ID_COLE'] + 'APPL_' + object['name']
                }
            }
        api.api_call('set-application-site-group', payload)

        # check if used in more places than its group and the general group
        used = whereUsed(object_uid)
        if used > 1:
            flash(u"La URL pertany a més llistes i no s'eliminarà totalment")
            return redirect(url_for(url_back))

        # call for removing the application from the general group
        payload = {
            'name': app.config['ID_COLE'] + app.config['LLISTA_GENERAL'],
            'members': {
                'remove': app.config['ID_COLE'] + 'APPL_' + object['name']
                }
            }
        api.api_call('set-application-site-group', payload)

        # call for deleting the application
        payload = {'uid': object_uid}
        api.api_call('delete-application-site', payload)
        api.api_call('publish')
        flash(u'URL eliminada')
        return redirect(url_for(url_back))

    return render_template(
        'delete-application-site.html',
        app_list=app_list,
        object=object,
        url_back=url_back
        )


@app.route(
    '/set-application-site/<object_uid>/<url_back>',
    methods=['GET', 'POST']
    )
@login_required
def setApplicationSite(object_uid, url_back):
    '''
    edit application-site
    --------------------------------------------------------------------------
    edit an existing application-site

    arguments:
        group_id: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    form = ApplicationSiteForm(request.form)
    payload = {'uid': object_uid}
    call = api.api_call('show-application-site', payload).data
    object = {
        'uid': object_uid,
        'name': call['name'][10:],
        'url_list': call['url-list'][0]
        }

    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'new-name': app.config['ID_COLE'] + 'APPL_' + form.name.data,
            'url-list': form.url_list.data,
            }
        api.api_call('set-application-site', payload)
        api.api_call('publish')
        flash(u'URL modificada')
        return redirect(url_for(url_back))

    return render_template(
        'edit-application-site.html',
        object=object,
        form=form,
        url_back=url_back
        )


@app.route('/allow-url')
@login_required
def allowURL():
    '''
    show application-site groups
    ------------------------------------
    show the application-site groups

    return: renders the show application-site groups page

    '''
    payload = {'name': app.config['ID_COLE'] + 'APGR_LlistaBlancaURLsVIP'}
    app_vip = api.api_call('show-application-site-group', payload).data
    payload = {'name': app.config['ID_COLE'] + 'APGR_LlistaBlancaURLsMedium'}
    app_medium = api.api_call('show-application-site-group', payload).data

    return render_template(
        'show-application-site-groups.html',
        app_vip=app_vip,
        app_medium=app_medium,
        url_back='allowURL'
        )


@app.route('/manage-groups')
@login_required
def manageGroups():
    '''
    manage groups
    ------------------------------------
    show the application-site groups

    return: renders the show application-site groups page

    '''
    payload = {'name': app.config['ID_COLE'] + 'GRUP_LlistaBlancaVIP'}
    group_vip = api.api_call('show-group', payload).data
    payload = {'name': app.config['ID_COLE'] + 'GRUP_LlistaBlancaMedium'}
    group_medium = api.api_call('show-group', payload).data

    return render_template(
        'show-groups.html',
        group_vip=group_vip,
        group_medium=group_medium,
        url_back='manageGroups'
        )


@app.route('/where-used/object_uid')
@login_required
def whereUsed(object_uid):
    '''
    edit application-site
    --------------------------------------------------------------------------
    edit an existing application-site

    arguments:
        group_id: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('where-used', payload).data
    return call['used-directly']['total']


@app.route('/smartview')
def smartview():

    # from selenium import webdriver
    # from selenium.webdriver.common.keys import Keys

    # driver = webdriver.Chrome()
    # webdriver.Chrome().execute_script("window.open('','_blank');")
    # driver.get('https://' + app.config['SERVER'] + '/smartview')
    # assert "Python" in driver.title
    # elem = driver.find_element_by_name("q")
    # input1 = driver.find_element_by_tag_name('body')
    # input1.send_keys("admin")
    # elem.send_keys(Keys.TAB)
    # elem.send_keys("developer")
    # elem.send_keys(Keys.ENTER)
    # assert "No results found." not in driver.page_source
    # driver.close()

    return redirect('https://' + app.config['SERVER'] + '/smartview', code=302)


@app.route('/install-policy')
@login_required
def installPolicy():
    '''
    edit application-site
    --------------------------------------------------------------------------
    edit an existing application-site

    arguments:
        group_id: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    payload = {'policy-package': 'standard'}
    api.api_call('install-policy', payload)
    return redirect(url_for('home'))

























@app.route('/show-access-rulebase')
@login_required
def showAccessRules():
    '''
    show access rules
    ------------------------------------------
    shows all the existing access rules

    return: renders the show access rules page

    '''
    objects = []
    payload = {'name': app.config['LAYER']}
    call = api.api_call('show-access-rulebase', payload).data
    for element in call['rulebase']:
        payload = {
            'uid': element['uid'],
            'layer': app.config['LAYER']
            }
        call = api.api_call('show-access-rule', payload).data
        object = {
            'uid': call['uid'],
            'name': call['name'],
            'source': call['source'][0]['name'],
            'service': call['service'][0]['name'],
            'action': call['action']['name']
            }
        objects.append(object)
    return render_template('show-access-rules.html', objects=objects)


@app.route('/add-rule', methods=['GET', 'POST'])
@login_required
def addAccessRule():
    '''
    add access rule
    -------------------------------------------------------------------------
    adds a new access rule

    return: if POST adds the new rule and renders the show access rules page,
        if GET renders the new access rule page

    '''
    # access rule form
    form = AccessRuleForm(request.form)

    # choices for source, groups
    hosts = [('', 'seleccionar')]
    call = api.api_call('show-groups').data
    for element in call['objects']:
        hosts.append((element['uid'], element['name'][2:]))
    form.source.choices = hosts

    # choices for destination, application groups
    app_groups = [('', 'seleccionar'), ('Any', 'Qualsevol')]
    call = api.api_call('show-application-site-groups').data
    for element in call['objects']:
        app_groups.append((element['uid'], element['name']))
    form.service.choices = app_groups

    # choices for actions, accept and drop
    form.action.choices = [
        ('', 'seleccionar'),
        ('Accept', 'Acceptar'),
        ('Drop', 'Denegar')
        ]

    if request.method == 'POST' and form.validate():
        payload = {
            'layer': app.config['LAYER'],
            'position': 'top',
            'action': form.action.data,
            'enabled': True,
            'name': app.config['ID_COLE'] + 'RULE_' + form.name.data,
            'source': form.source.data,
            'service': form.service.data
            }
        api.api_call('add-access-rule', payload)
        api.api_call('publish')
        flash('Regla afegida')
        return redirect(url_for('showAccessRules'))

    return render_template('new-access-rule.html', form=form)


@app.route('/show-group-content/<group_id>')
@login_required
def showGroupContent(group_id):
    '''
    show group content
    --------------------------------------------------------------------------
    shows the group content when selecting a source in the dropdown menu while
    adding a new rule, can be hosts or networks

    argument:
        group_id: the group that's been selected in the drowdown menu

    return: renders the show group content page just below the select

    '''
    hosts, networks = [], []
    # call for group detail
    payload = {'uid': group_id, 'details-level': 'full'}
    call = api.api_call('show-group', payload).data
    # separate hosts and members
    for element in call['members']:

        if element['type'] == 'host':
            object = {
                'name': element['name'],
                'ipv4_address': element['ipv4-address']
                }
            hosts.append(object)

        if element['type'] == 'network':
            object = {
                'name': element['name'],
                'subnet4': element['subnet4'],
                }
            networks.append(object)

    return render_template(
        'show-group-content.html',
        hosts=hosts,
        networks=networks
        )


@app.route('/delete-rule/<object_uid>', methods=['GET', 'POST'])
@login_required
def deleteAccessRule(object_uid):
    '''
    delete access rule
    --------------------------------------------------------------------------
    deletes an existing access rule

    arguments:
        object_uid: uid number of the access rule to be deleted

    return: if POST deletes the slected access rule, if GET renders the delete
        access rule page

    '''
    # call for access rule detail
    payload = {
        'uid': object_uid,
        'layer': app.config['LAYER']
        }
    call = api.api_call('show-access-rule', payload).data
    object = {
        'uid': object_uid,
        'name': call['name']
        }

    if request.method == 'POST':
        api.api_call('delete-access-rule', payload)
        api.api_call('publish')
        flash(u'Regla eliminada')
        return redirect(url_for('showAccessRules'))

    return render_template('delete-access-rule.html', object=object)


@app.route('/show-groups')
@login_required
def showGroups():
    '''
    show groups
    ------------------------------------
    shows the groups

    return: renders the show groups page

    '''
    call = api.api_call('show-groups').data
    return render_template('show-groups.html', objects=call['objects'])


@app.route('/add-network/<group_id>', methods=['POST'])
@login_required
def addNetwork(group_id):
    '''
    add network
    ---------------------------------------------------------------------------
    adds a new network inside a group

    arguments:
        group_id: the id number of the group where the network has to be added

    return: if YES creates the network and adds it to the group, if NO renders
        the show groups page

    '''
    form = NetworkForm(request.form)

    if form.validate():
        # call for adding the network
        payload = {
            'name': app.config['ID_COLE'] + 'NETW_' + form.name.data,
            'subnet4': form.subnet4.data,
            'subnet-mask': form.subnet_mask.data
        }
        api.api_call('add-network', payload)
        # call for adding the network to group
        payload = {
            'uid': group_id,
            'members': {
                'add': 'Net ' + form.name.data
                }
            }
        api.api_call('set-group', payload)
        api.api_call('publish')
        flash('Xarxa afegida')
        return redirect(url_for('showGroups'))

    return render_template('new-network.html', form=form)


@app.route('/delete-network/<group_id>/<object_uid>', methods=['GET', 'POST'])
@login_required
def deleteNetwork(group_id, object_uid):
    '''
    delete network
    ---------------------------------------------------------------------------
    deletes an existing network

    arguments:
        group_id: the id number of the group where the network belongs
        object_uid: the uid number of the network

    return: if POST deletes the network, if GET renders the delete network page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('show-network', payload).data
    object = {
        'uid': object_uid,
        'name': call['name'],
        'subnet4': call['subnet4'],
        'subnet_mask': call['subnet-mask']
        }
    if request.method == 'POST':
        # call for removing the network from the group
        payload = {
            'uid': group_id,
            'members': {
                'remove': object['name']
                }
            }
        api.api_call('set-group', payload)
        # call for deleting the network
        payload = {'uid': object_uid}
        api.api_call('delete-network', payload)
        api.api_call('publish')
        flash('Xarxa eliminada')
        return redirect(url_for('showGroups'))
    else:
        return render_template(
            'delete-network.html',
            group_id=group_id,
            object=object
            )


@app.route('/set-network/<object_uid>', methods=['GET', 'POST'])
@login_required
def setNetwork(object_uid):
    '''
    edit network
    ---------------------------------------------------------------------------
    edit an existing network

    arguments:
        group_id: the id number of the group
        object_uid:

    return: renders the show group members page

    '''
    form = NetworkForm(request.form)
    payload = {'uid': object_uid}
    call = api.api_call('show-network', payload).data
    object = {
        'uid': object_uid,
        'name': call['name'],
        'subnet4': call['subnet4'],
        'subnet_mask': call['subnet-mask']
        }

    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'new-name': 'Net ' + form.name.data,
            'subnet4': form.subnet4.data,
            'subnet-mask': form.subnet_mask.data
            }
        api.api_call('set-network', payload)
        api.api_call('publish')
        flash('Xarxa editada')
        return redirect(url_for('showGroups'))

    return render_template('edit-network.html', object=object, form=form)


@app.route('/add-group', methods=['GET', 'POST'])
@login_required
def addGroup():
    '''
    add group
    -------------------------------------------------------------------
    add a new group

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    form = GroupForm(request.form)

    if request.method == 'POST' and form.validate():
        payload = {'name': app.config['ID_COLE'] + 'GRUP_' + form.name.data}
        api.api_call('add-group', payload)
        api.api_call('publish')
        flash('Grup afegit')
        return redirect(url_for('showGroups'))

    return render_template('new-group.html', form=form)


@app.route('/delete-group/<object_uid>', methods=['GET', 'POST'])
@login_required
def deleteGroup(object_uid):
    '''
    delete group
    -------------------------------------------------------------------
    delete an existing group

    arguments:
        object_uid

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('show-group', payload).data
    if request.method == 'POST':
        api.api_call('delete-group', payload)
        api.api_call('publish')
        flash('Grup eliminat')
        return redirect(url_for('showGroups'))

    return render_template('delete-group.html', object=call)


@app.route('/set-group/<object_uid>', methods=['GET', 'POST'])
@login_required
def setGroup(object_uid):
    '''
    edit group
    -------------------------------------------------------------------
    edit an existing group

    arguments:
        object_uid

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    form = GroupForm(request.form)

    payload = {'uid': object_uid}
    call = api.api_call('show-group', payload).data
    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'new-name': 'Gr ' + form.name.data,
            }
        api.api_call('set-group', payload)
        api.api_call('publish')
        flash('Grup editat')
        return redirect(url_for('showGroups'))

    return render_template('edit-group.html', object=call, form=form)


@app.route('/show-application-sites/<group_id>')
@login_required
def showApplicationSites(group_id):
    '''
    show application-sites
    --------------------------------------------------------------------------
    show the application-sites of each group of applications, allows the user
    to add an application, either selecting it from the list or creating a new
    one

    arguments:
        group_id: the id number of the application-site groups

    return: renders the show application-sites page

    '''
    # form for selecting an application
    form_select_app = ApplicationSelectForm(request.form)
    # fill the applications selection list
    applications = [('', 'seleccionar')]
    call = api.api_call('show-application-sites').data
    for element in call['objects']:
        applications.append((element['uid'], element['name']))
    form_select_app.name.choices = applications

    # form for adding an application
    form = ApplicationSiteForm(request.form)

    # call for application groups
    objects = []
    payload = {'uid': group_id, 'details-level': 'full'}
    call = api.api_call('show-application-site-group', payload).data
    for element in call['members']:
        object = {
            'uid': element['uid'],
            'name': element['name'],
            'url': element['url-list'][0],
            'description': element['description']
            }
        objects.append(object)
    objects = orderList(objects)
    return render_template(
        'show-application-sites.html',
        objects=objects,
        form_select_app=form_select_app,
        form=form,
        group_id=group_id
        )


@app.route('/add-application-site-group', methods=['GET', 'POST'])
@login_required
def addApplicationSiteGroup():
    '''
    add application-site group
    -------------------------------------------------------------------
    add a new application-site group

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    form = ApplicationSiteGroupForm(request.form)

    if request.method == 'POST' and form.validate():
        payload = {'name': app.config['ID_COLE'] + 'APGR_' + form.name.data}
        api.api_call('add-application-site-group', payload)
        api.api_call('publish')
        flash("Grup d'aplicacions afegit")
        return redirect(url_for('showApplicationSiteGroups'))

    return render_template('new-application-site-group.html', form=form)


@app.route(
    '/delete-application-site-group/<object_uid>',
    methods=['GET', 'POST']
    )
@login_required
def deleteApplicationSiteGroup(object_uid):
    '''
    delete application-site group
    -------------------------------------------------------------------
    delete an existing application-site group

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    payload = {'uid': object_uid}
    call = api.api_call('show-application-site-group', payload).data

    if request.method == 'POST':
        api.api_call('delete-application-site-group', payload)
        api.api_call('publish')
        flash("Grup d'aplicacions eliminat")
        return redirect(url_for('showApplicationSiteGroups'))

    return render_template('delete-application-site-group.html', object=call)


@app.route('/set-application-site-group/<object_uid>', methods=['GET', 'POST'])
@login_required
def setApplicationSiteGroup(object_uid):
    '''
    edit application-site group
    -------------------------------------------------------------------
    edit an existing application-site group

    arguments:
        object_uid:

    return: if POST redirect to show groups page after adding group and
    publish, if GET renders the new group page

    '''
    form = GroupForm(request.form)

    payload = {'uid': object_uid}
    call = api.api_call('show-application-site-group', payload).data

    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'new-name': form.name.data,
            }
        api.api_call('set-application-site-group', payload)
        api.api_call('publish')
        flash("Grup d'aplicacions editat")
        return redirect(url_for('showApplicationSiteGroups'))

    return render_template(
            'edit-application-site-group.html',
            object=call,
            form=form
            )


#################
# OLD FUNCTIONS #
#################

# Edit rule
@app.route('/set-rule/<object_uid>', methods=['GET', 'POST'])
@login_required
def setAccessRule(object_uid):
    form = AccessRuleForm(request.form)

    # call hosts
    objects = []
    call = api.api_call('show-hosts').data
    for element in call['objects']:
        objects.append((element['uid'], element['name']))

    # call networks
    call = api.api_call('show-networks').data
    for element in call['objects']:
        objects.append((element['uid'], element['name']))

    # call groups
    call = api.api_call('show-groups').data
    for element in call['objects']:
        objects.append((element['uid'], element['name']))

    # add options
    form.source.choices = objects
    form.destination.choices = objects

    payload = {
        'uid': object_uid,
        'layer': app.config['LAYER']
        }
    call = api.api_call('show-access-rule', payload).data
    object = {
        'uid': object_uid,
        'Nom': call['name'],
        }
    if request.method == 'POST' and form.validate():
        payload = {
            'uid': object_uid,
            'layer': app.config['LAYER'],
            'new-name': form.name.data,
            'source': form.source.data,
            'destination': form.destination.data
            }
        api.api_call('set-access-rule', payload)
        api.api_call('publish')
        flash('Regla editada')
        return redirect(url_for('showAccessRules'))
    else:
        return render_template(
            'edit-access-rule.html',
            object=object,
            form=form
            )


# Show hosts
@app.route('/show-hosts')
@login_required
def showHosts():
    objects = []
    call = api.api_call('show-hosts').data
    for element in call['objects']:
        payload = {'uid': element['uid']}
        call = api.api_call('show-host', payload)
        object = {
            'uid': call['uid'],
            'name': call['name'],
            'ipv4_address': call['ipv4-address']
        }
        objects.append(object)
    return render_template('show-hosts.html', objects=objects)


# Show networks
@app.route('/show-networks')
@login_required
def showNetworks():
    objects = []
    call = api.api_call('show-networks').data
    for element in call['objects']:
        payload = {'uid': element['uid']}
        call = api.api_call('show-network', payload).data
        object = {
            'uid': call['uid'],
            'name': call['name'],
            'subnet4': call['subnet4'],
            'subnet_mask': call['subnet-mask']
            }
        objects.append(object)
    return render_template('show-networks.html', objects=objects)
