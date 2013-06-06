'''
MASSIVE LDAP Authentication module.

.. moduleauthor:: James Wettenhall <james.wettenhall@monash.edu>

Assumes that an SSH tunnel is available, forwarding MASSIVE's LDAP
to localhost::389.
'''

import logging

from django.contrib.auth.models import User, Group

from tardis.tardis_portal.auth.interfaces import AuthProvider, GroupProvider, UserProvider

import subprocess

logger = logging.getLogger(__name__)


auth_key = u'massiveldap'
auth_display_name = u'MASSIVE LDAP'


class DjangoAuthBackend(AuthProvider):
    """Authenticate against MASSIVE's LDAP directory, via an SSH tunnel.

    """

    def authenticate(self, request):
        """authenticate a user, this expect the user will be using
        form based auth and the *username* and *password* will be
        passed in as **POST** variables.

        :param request: a HTTP Request instance
        :type request: :class:`django.http.HttpRequest`
        """
        username = request.POST['username']
        password = request.POST['password']

        if not username or not password:
            return None

        authenticated = False

        try:
            command = ['/usr/bin/ldapsearch','-H','ldap://localhost/','-b','cn=users,dc=massive,dc=org,dc=au','-D','uid=%s,cn=users,dc=massive,dc=org,dc=au' % username,'-x','-w',password,'uid=%s' % username]
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if proc.returncode!=0:
                return None
            authenticated = True
            lines = stdout.split("\n")
            name = None
            names = None
            email = None
            for line in lines:
                if line.startswith("cn: "):
                    lineComponents = line.split("cn: ")
                    name = lineComponents[1]
                    names = name.split(" ")
                if line.startswith("mail: "):
                    lineComponents = line.split("mail: ")
                    email = lineComponents[1]

            if name!=None and names!=None and len(names)>=2 and email!=None:
                return {"id": username,
                        "display": name,
                        "email": email,
                        "first_name": names[0],
			"last_name": names[1]}

        except:
            authenticated = False
            return None

        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            user = None
        return user

class DjangoGroupProvider(GroupProvider):
    name = u'django_group'

    def getGroups(self, request):
        """return an iteration of the available groups.
        """
        groups = request.user.groups.all()
        return [g.id for g in groups]

    def getGroupById(self, id):
        """return the group associated with the id::

            {"id": 123,
            "display": "Group Name",}

        """
        groupObj = Group.objects.get(id=id)
        if groupObj:
            return {'id': id, 'display': groupObj.name}
        return None

    def searchGroups(self, **filter):
        result = []
        groups = Group.objects.filter(**filter)
        for g in groups:
            users = [u.username for u in User.objects.filter(groups=g)]
            result += [{'id': g.id,
                        'display': g.name,
                        'members': users}]
        return result


class DjangoUserProvider(UserProvider):
    name = u'django_user'

    def getUserById(self, id):
        """
        return the user dictionary in the format of::

            {"id": 123,
            "display": "John Smith",
            "email": "john@example.com"}

        """
        try:
            userObj = User.objects.get(username=id)
            return {'id': id, 'display': userObj.first_name + ' ' +
                    userObj.last_name, 'first_name': userObj.first_name,
                    'last_name': userObj.last_name, 'email': userObj.email}
        except User.DoesNotExist:
            return None


django_user = DjangoUserProvider.name
django_group = DjangoGroupProvider.name
