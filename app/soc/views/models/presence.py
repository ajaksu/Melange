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

"""Views for Models with a "presence" on a Melange site.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


from google.appengine.ext import db

from django import forms
from django.utils.translation import ugettext_lazy

from soc.logic import dicts
from soc.logic import validate
from soc.logic.models import document as document_logic
from soc.views import helper
from soc.views.helper import access
from soc.views.models import base

import soc.models.presence
import soc.logic.models.presence
import soc.logic.dicts
import soc.views.helper
import soc.views.helper.widgets


class SettingsValidationForm(helper.forms.BaseForm):
  """Django form displayed when creating or editing Settings.
  
  This form includes validation functions for Settings fields.
  """

  # TODO(tlarsen): scope_path will be a hard-coded read-only
  #   field for some (most?) User Roles
  home_scope_path = forms.CharField(required=False,
      label=ugettext_lazy('home page Document scope path'),
      help_text=soc.models.work.Work.scope_path.help_text)

  # TODO(tlarsen): actually, using these two text fields to specify
  #   the Document is pretty cheesy; this needs to be some much better
  #   Role-scoped Document selector that we don't have yet.  See:
  #     http://code.google.com/p/soc/issues/detail?id=151
  home_link_id = forms.CharField(required=False,
      label=ugettext_lazy('home page Document link ID'),
      help_text=soc.models.work.Work.link_id.help_text)

  # TODO(tlarsen): scope_path will be a hard-coded read-only
  #   field for some (most?) User Roles
  tos_scope_path = forms.CharField(required=False,
      label=ugettext_lazy('Terms of Service Document scope path'),
      help_text=soc.models.work.Work.scope_path.help_text)

  # TODO(tlarsen): actually, using these two text fields to specify
  #   the Document is pretty cheesy; this needs to be some much better
  #   Role-scoped Document selector that we don't have yet
  #   See:
  #     http://code.google.com/p/soc/issues/detail?id=151
  tos_link_id = forms.CharField(required=False,
      label=ugettext_lazy('Terms of Service Document link ID'),
      help_text=soc.models.work.Work.link_id.help_text)

  def clean_feed_url(self):
    feed_url = self.cleaned_data.get('feed_url')

    if feed_url == '':
      # feed url not supplied (which is OK), so do not try to validate it
      return None
    
    if not validate.isFeedURLValid(feed_url):
      raise forms.ValidationError('This URL is not a valid ATOM or RSS feed.')

    return feed_url


class CreateForm(SettingsValidationForm):
  """Django form displayed when creating or editing Settings.
  """

  class Meta:
    """Inner Meta class that defines some behavior for the form.
    """
    #: db.Model subclass for which the form will gather information
    model = soc.models.presence.Presence

    #: list of model fields which will *not* be gathered by the form
    exclude = ['scope',
      # TODO(tlarsen): this needs to be enabled once a button to a list
      #   selection "interstitial" page is implemented, see:
      #     http://code.google.com/p/soc/issues/detail?id=151
      'home', 'tos']


class EditForm(CreateForm):
  """Django form displayed a Document is edited.
  """

  pass


class View(base.View):
  """View methods for the Document model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = {}
    rights['any_access'] = [access.allow]
    rights['show'] = [access.allow]

    new_params = {}
    new_params['logic'] = soc.logic.models.presence.logic
    new_params['rights'] = rights

    new_params['name'] = "Home Settings"
    new_params['url_name'] = "home/settings"
    new_params['module_name'] = "presence"

    new_params['edit_form'] = EditForm
    new_params['create_form'] = CreateForm

    # Disable the presence sidebar until we have some use for it
    new_params['sidebar_defaults'] = []

    params = dicts.merge(params, new_params)

    super(View, self).__init__(params=params)

  def _public(self, request, entity, context):
    """See base.View._public().
    """

    if not entity:
      return

    try:
      home_doc = entity.home
    except db.Error:
      home_doc = None

    if home_doc:
      home_doc.content = helper.templates.unescape(home_doc.content)
      context['home_document'] = home_doc

    try:
      tos_doc = entity.tos
    except db.Error:
      tos_doc = None

    if tos_doc:
      # TODO(tlarsen): This may not be the correct way to do this...  Also,
      #   at some point, this needs to be a link to *all* of the various
      #   Terms of Service that might apply to the scope of this particular
      #   page (e.g. site-wide ToS, program ToS, group ToS, etc.).  See:
      #     http://code.google.com/p/soc/issues/detail?id=153
      #   So, this probably needs to be added to base.py, but these
      # overridden _public() methods do not seem to call it.
      context['tos_link'] = '/document/show/%s/%s' % (
        tos_doc.scope_path, tos_doc.link_id)

  def _editGet(self, request, entity, form):
    """See base.View._editGet().
    """

    try:
      if entity.home:
        form.fields['home_scope_path'].initial = entity.home.scope_path
        form.fields['home_link_id'].initial = entity.home.link_id

      if entity.tos:
        form.fields['tos_scope_path'].initial = entity.tos.scope_path
        form.fields['tos_link_id'].initial = entity.tos.link_id
    except db.Error:
      pass

    super(View, self)._editGet(request, entity, form)

  def _editPost(self, request, entity, fields):
    """See base.View._editPost().
    """

    home_scope_path = fields['home_scope_path']
    home_link_id = fields['home_link_id']

    # TODO notify the user if home_doc is not found
    home_doc = document_logic.logic.getFromFields(
      scope_path=home_scope_path, link_id=home_link_id)

    fields['home'] = home_doc

    tos_scope_path = fields['tos_scope_path']
    tos_link_id = fields['tos_link_id']

    # TODO notify the user if tos_doc is not found
    tos_doc = document_logic.logic.getFromFields(
      scope_path=tos_scope_path, link_id=tos_link_id)

    fields['tos'] = tos_doc

    super(View, self)._editPost(request, entity, fields)


view = View()

create = view.create
edit = view.edit
delete = view.delete
list = view.list
public = view.public

