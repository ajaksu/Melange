#!/usr/bin/python2.5
#
# Copyright 2008 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module contains the User Model."""

__authors__ = [
  '"Todd Larsen" <tlarsen@google.com>',
  '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  '"Pawel Solyga" <pawel.solyga@gmail.com>',
]


from google.appengine.api import users
from google.appengine.ext import db

from django.utils.translation import ugettext_lazy

from soc.models import base


class User(base.ModelWithFieldAttributes):
  """A user and associated login credentials, the fundamental identity entity.

  User is a separate Model class from Person because the same login 
  ID may be used to, for example, serve as Contributor in one Program 
  and a Reviewer in another.

  Also, this allows a Person to, in the future, re-associate that 
  Person entity with a different Google Account if necessary.

  A User entity participates in the following relationships implemented 
  as a db.ReferenceProperty elsewhere in another db.Model:

   persons)  a 1:many relationship of Person entities identified by the
     User.  This relation is implemented as the 'persons' back-reference
     Query of the Person model 'user' reference.
     
   documents)  a 1:many relationship of Document entities identified by the
     User.  This relation is implemented as the 'user' back-reference
     Query of the Document model 'user' reference.

   groups)  a 1:many relationship of Group entities "founded" by the User.
     This relation is implemented as the 'groups' back-reference Query of
     the Group model 'founder' reference.

   responses)  a 1:many relationship of Reponse entities submitted by the
     User.  This relation is implemented as the 'responses' back-reference
     Query of the Response model 'respondent' reference.
  """

  #: A Google Account, which also provides a "private" email address.
  #: This email address is only used in an automated fashion by 
  #: Melange web applications and is not made visible to other users 
  #: of any Melange application.
  account = db.UserProperty(required=True,
      verbose_name=ugettext_lazy('User account'))
  account.help_text = ugettext_lazy(
      'A valid Google Account.')

  #: A list (possibly empty) of former Google Accounts associated with
  #: this User.
  former_accounts = db.ListProperty(users.User)

  #: Required field storing publicly-displayed name.  Can be a real name
  #: (though this is not recommended), or a nick name or some other public
  #: alias.  Public names can be any valid UTF-8 text.
  public_name = db.StringProperty(required=True,
      verbose_name=ugettext_lazy('Public name'))
      
  #: Required field storing link_id used in URLs to identify user.
  #: Lower ASCII characters only.
  link_id = db.StringProperty(required=True,
      verbose_name=ugettext_lazy('Link ID'))
  link_id.help_text = ugettext_lazy(
      'Field used in URLs to identify user. '
      'Lower ASCII characters only.')

  #: field storing whether User is a Developer with site-wide access.
  is_developer = db.BooleanProperty(
      verbose_name=ugettext_lazy('Is Developer'))
  is_developer.help_text = ugettext_lazy(
      'Field used to indicate user with site-wide "Developer" access.')
