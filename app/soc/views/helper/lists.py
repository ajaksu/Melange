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

"""Helpers used to render lists.
"""

__authors__ = [
  '"Chen Lunpeng" <forever.clp@gmail.com>',
  '"Pawel Solyga" <pawel.solyga@gmail.com>',
  ]


from soc.logic import dicts
from soc.logic.models.user import logic as user_logic

import soc.views.helper.forms


DEF_DEFAULT_PAGINATION = 50
DEF_MAX_PAGINATION = 100
DEF_MAX_DEV_PAGINATION = 1000

DEF_PAGINATION_CHOICES = [
    ('10', '10 items per page'),
    ('25', '25 items per page'),
    ('50', '50 items per page'),
    ('100', '100 items per page'),
]

DEF_DEVELOPER_CHOICES = [
    ('500', '500 items per page'),
    ('1000', '1000 items per page'),
    ]


def getPreferredListPagination(user=None):
  """Returns User's preferred list pagination limit.

  Args:
    user: User entity containing the list pagination preference;
      default is None, to use the current logged-in User
  """
  # TODO: eventually this limit should be a User profile preference
  #   (stored in the site-wide User Model) preference
  return DEF_DEFAULT_PAGINATION


OFFSET_KEY = 'offset_%d'
LIMIT_KEY = 'limit_%d'


def makeOffsetKey(limit_idx):
  return OFFSET_KEY % limit_idx


def makeLimitKey(limit_idx):
  return LIMIT_KEY % limit_idx


def getListParameters(request, list_index):
  """Retrieves, converts and validates values for one list

  Args:
    list_index, int: which list to get the values for.
      (there may be multiple lists on one page, which are multiplexed
       by an integer.)

  Returns:
    a dictionary of str -> str.  field name -> field value.
  """

  offset = request.GET.get(makeOffsetKey(list_index))
  limit = request.GET.get(makeLimitKey(list_index))

  if offset is None:
    offset = ''

  if limit is None:
    limit = ''

  try:
    offset = int(offset)
  except ValueError:
    offset = 0

  try:
    limit = int(limit)
  except ValueError:
    limit = getPreferredListPagination()

  offset = max(0, offset)
  limit = max(1, limit)

  if user_logic.isDeveloper():
    limit = min(DEF_MAX_DEV_PAGINATION, limit)
  else:
    limit = min(DEF_MAX_PAGINATION, limit)

  return dict(limit=limit, offset=offset)


def generateLinkFromGetArgs(request, offset_and_limits):
  """Constructs the get args for the url.
  """

  args = ["%s=%s" % (k, v) for k, v in offset_and_limits.iteritems()]
  link_suffix = '?' + '&'.join(args)

  return request.path + link_suffix


def generateLinkForRequest(request, base_params, updated_params):
  """Create a link to the same page as request but with different params

  Params:
    request: the request for the page
    base_params: the base parameters
    updated_params: the parameters to update
  """
  params = base_params.copy()
  params.update(updated_params)
  return generateLinkFromGetArgs(request, params)


def getListContent(request, params, filter=None, order=None,
                   idx=0, need_content=False):
  """Returns a dict with fields used for rendering lists.

  TODO(dbentley): we need better terminology. List, in this context, can have
    one of two meanings.
    Meaning 1:  the underlying list, which may be very large.
    Meaning 2:  the returned list, which is at most 'limit' items.

  Args:
    request: the Django HTTP request object
    params: a dict with params for the View this list belongs to
    filter: a filter for this list
    order: the order which should be used for the list (in getForFields format)
    idx: the index of this list
    need_content: iff True will return None if there is no data

  Returns:
    A dictionary with the following values set:

    {
      'data': list data to be displayed
      'main': url to list main template
      'pagination': url to list pagination template
      'row': url to list row template
      'heading': url to list heading template
      'limit': max amount of items per page,
      'newest': url to first page of the list
      'prev': url to previous page
      'next': url to next page
      'first': offset of the first item in the list
      'last': offset of the last item in the list
    }
  """
  # TODO(dbentley): this appears to be unnecessary indirection,
  # as we only use this logic for getForFields, which is never overridden
  logic = params['logic']

  limit_key, offset_key = makeLimitKey(idx), makeOffsetKey(idx)

  list_params = getListParameters(request, idx)
  limit, offset = list_params['limit'], list_params['offset']
  pagination_form = makePaginationForm(request, list_params['limit'],
                                       limit_key)

  # Fetch one more to see if there should be a 'next' link
  data = logic.getForFields(filter=filter, limit=limit+1, offset=offset,
                            order=order)

  if need_content and not data:
    return None

  more = len(data) > limit

  if more:
    del data[limit:]

  newest = next = prev = export_link = ''

  base_params = dict(i for i in request.GET.iteritems() if
                     i[0].startswith('offset_') or i[0].startswith('limit_'))

  if params.get('list_key_order'):
    export_link = generateLinkForRequest(request, base_params, {'export': idx})

  if more:
    # TODO(dbentley): here we need to implement a new field "last_key"
    next = generateLinkForRequest(request, base_params, 
                                  {offset_key: offset + limit,
                                   limit_key: limit})

  if offset > 0:
    # TODO(dbentley): here we need to implement previous in the good way.
    prev = generateLinkForRequest(request, base_params,
                                  {offset_key: max(0, offset-limit),
                                   limit_key: limit})

  if offset > limit:
    # Having a link to the first doesn't make sense on the first page (we're on
    # it).  It also doesn't make sense on the second page (because the first
    # page is the previous page).

    # NOTE(dbentley): I personally disagree that it's simpler to do that way,
    # because sometimes you want to go to the first page without having to
    # consider what page you're on now.
    newest = generateLinkForRequest(request, base_params, {offset_key: 0,
                                                           limit_key: limit})

  content = {
      'idx': idx,
      'data': data,
      'export': export_link,
      'first': offset+1,
      'last': len(data) > 1 and offset+len(data) or None,
      'logic': logic,
      'limit': limit,
      'newest': newest,
      'next': next,
      'pagination_form': pagination_form,
      'prev': prev,
      }

  updates = dicts.rename(params, params['list_params'])
  content.update(updates)

  return content


def makePaginationForm(
  request, limit, arg_name, choices=DEF_PAGINATION_CHOICES,
  field_name_fmt=soc.views.helper.forms.DEF_SELECT_QUERY_ARG_FIELD_NAME_FMT):
  """Returns a customized pagination limit selection form.

  Args:
    request: the standard Django HTTP request object
    limit: the initial value of the selection control
    arg_name: see soc.views.helper.forms.makeSelectQueryArgForm(); default is 'limit'
    choices: see soc.views.helper.forms.makeSelectQueryArgForm(); default is
      DEF_PAGINATION_CHOICES
    field_name_fmt: see soc.views.helper.forms.makeSelectQueryArgForm()
  """
  choices = makeNewPaginationChoices(limit=limit, choices=choices)

  return soc.views.helper.forms.makeSelectQueryArgForm(
      request, arg_name, limit, choices)


def makeNewPaginationChoices(limit=DEF_DEFAULT_PAGINATION,
                             choices=DEF_PAGINATION_CHOICES):
  """Updates the pagination limit selection form.

  Args:
    limit: the initial value of the selection control;
      default is DEF_DEFAULT_PAGINATION
    choices: see soc.views.helper.forms.makeSelectQueryArgForm();
      default is DEF_PAGINATION_CHOICES

  Returns:
    a new pagination choices list if limit is not in
    DEF_PAGINATION_CHOICES, or DEF_PAGINATION_CHOICES otherwise
  """

  new_choices = []
  new_choice = (str(limit), '%s items per page' % limit)

  new_choices.append(new_choice)
  new_choices.extend(choices)

  if user_logic.isDeveloper():
    new_choices.extend(DEF_DEVELOPER_CHOICES)

  new_choices = set(new_choices)

  return sorted(new_choices, key=lambda (x, y): int(x))
