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

"""Views for PresenceWithToS.
"""

__authors__ = [
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
  ]


from google.appengine.ext import db

from django import forms
from django.utils.translation import ugettext

from soc.logic import dicts
from soc.logic.models import document as document_logic
from soc.views.models import presence

import soc.logic.models.presence_with_tos
import soc.models.work


class View(presence.View):
  """View methods for the PresenceWithToS model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    new_params = {}
    new_params['logic'] = soc.logic.models.presence_with_tos.logic

    new_params['create_extra_dynafields'] = {
        'tos_link_id': forms.CharField(required=False,
            label=ugettext('Terms of Service Document link ID'),
            help_text=soc.models.work.Work.link_id.help_text),
        }

    params = dicts.merge(params, new_params, sub_merge=True)

    super(View, self).__init__(params=params)

  def _editGet(self, request, entity, form):
    """See base.View._editGet().
    """

    try:
      if entity.tos:
        form.fields['tos_link_id'].initial = entity.tos.link_id
    except db.Error:
      pass

    super(View, self)._editGet(request, entity, form)

  def _editPost(self, request, entity, fields):
    """See base.View._editPost().
    """

    key_fields = self._logic.getKeyFieldsFromDict(fields)
    scope_path = self._logic.getKeyNameForFields(key_fields)

    tos_link_id = fields['tos_link_id']

    # TODO notify the user if tos_doc is not found
    tos_doc = document_logic.logic.getFromFields(
      scope_path=scope_path, link_id=tos_link_id)

    fields['tos'] = tos_doc

    super(View, self)._editPost(request, entity, fields)