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

"""Views for Programs.
"""

__authors__ = [
    '"Daniel Hans" <daniel.m.hans@gmail.com>',
    '"Sverre Rabbelier" <sverre@rabbelier.nl>',
    '"Lennard de Rijk" <ljvderijk@gmail.com>',
  ]


import os

from django import forms
from django import http
from django.utils.translation import ugettext

from soc.logic import allocations
from soc.logic import cleaning
from soc.logic import dicts
from soc.logic.helper import timeline as timeline_helper
from soc.logic.models import host as host_logic
from soc.logic.models import mentor as mentor_logic
from soc.logic.models import organization as org_logic
from soc.logic.models import org_admin as org_admin_logic
from soc.logic.models import org_app as org_app_logic
from soc.logic.models import student_proposal as student_proposal_logic
from soc.logic.models import program as program_logic
from soc.logic.models import student as student_logic
from soc.views import helper
from soc.views import out_of_band
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.helper import lists
from soc.views.helper import redirects
from soc.views.helper import widgets
from soc.views.models import presence
from soc.views.models import document as document_view
from soc.views.models import sponsor as sponsor_view
from soc.views.models import survey as survey_view
from soc.views.sitemap import sidebar

import soc.cache.logic
import soc.logic.models.program
import soc.models.work


class View(presence.View):
  """View methods for the Program model.
  """

  DEF_ACCEPTED_ORGS_MSG_FMT = ugettext("These organizations have"
      " been accepted into %(name)s, but they have not yet completed"
      " their organization profile. You can still learn more about"
      " each organization by visiting the links below.")

  DEF_CREATED_ORGS_MSG_FMT = ugettext("These organizations have been"
      " accepted into %(name)s and have completed their organization"
      " profiles. You can learn more about each organization by"
      " visiting the links below.")

  DEF_SLOTS_ALLOCATION_MSG = ugettext("Use this view to assign slots.")

  DEF_ACCEPTED_PROJECTS_MSG_FMT = ugettext("These projects have been"
      " accepted into %(name)s. You can learn more about each project"
      " by visiting the links below.")

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = access.Checker(params)
    rights['any_access'] = ['allow']
    rights['show'] = ['allow']
    rights['create'] = [('checkSeeded', ['checkHasActiveRoleForScope', 
        host_logic.logic])]
    rights['edit'] = ['checkIsHostForProgram']
    rights['delete'] = ['checkIsDeveloper']
    rights['assign_slots'] = ['checkIsHostForProgram']
    rights['slots'] = ['checkIsHostForProgram']
    rights['show_duplicates'] = ['checkIsHostForProgram']
    rights['assigned_proposals'] = ['checkIsHostForProgram']
    rights['accepted_orgs'] = [('checkIsAfterEvent',
        ['accepted_organization_announced_deadline', '__all__'])]
    rights['list_projects'] = [('checkIsAfterEvent',
        ['accepted_students_announced_deadline', '__all__'])]

    new_params = {}
    new_params['logic'] = soc.logic.models.program.logic
    new_params['rights'] = rights

    new_params['scope_view'] = sponsor_view
    new_params['scope_redirect'] = redirects.getCreateRedirect

    new_params['name'] = "Program"
    new_params['sidebar_grouping'] = 'Programs'
    new_params['document_prefix'] = "program"

    new_params['extra_dynaexclude'] = ['timeline', 'org_admin_agreement',
        'mentor_agreement', 'student_agreement', 'slots_allocation']

    patterns = []
    patterns += [
        (r'^%(url_name)s/(?P<access_type>assign_slots)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.assign_slots',
          'Assign slots'),
        (r'^%(url_name)s/(?P<access_type>slots)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.slots',
          'Assign slots (JSON)'),
        (r'^%(url_name)s/(?P<access_type>show_duplicates)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.show_duplicates',
          'Show duplicate slot assignments'),
        (r'^%(url_name)s/(?P<access_type>assigned_proposals)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.assigned_proposals',
          "Assigned proposals for multiple organizations"),
        (r'^%(url_name)s/(?P<access_type>accepted_orgs)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.accepted_orgs',
          "List all accepted organizations"),
        (r'^%(url_name)s/(?P<access_type>list_projects)/%(key_fields)s$',
          'soc.views.models.%(module_name)s.list_projects',
          "List all student projects"),
        ]

    new_params['extra_django_patterns'] = patterns

    new_params['create_dynafields'] = [
        {'name': 'link_id',
         'base': forms.fields.CharField,
         'label': 'Program Link ID',
         },
        ]

    # TODO add clean field to check for uniqueness in link_id and scope_path
    new_params['create_extra_dynaproperties'] = {
        'description': forms.fields.CharField(widget=helper.widgets.TinyMCE(
            attrs={'rows':10, 'cols':40})),
        'accepted_orgs_msg': forms.fields.CharField(
            widget=helper.widgets.TinyMCE(attrs={'rows':10, 'cols':40})),
        'scope_path': forms.CharField(widget=forms.HiddenInput, required=True),
        'workflow': forms.ChoiceField(choices=[('gsoc','Project-based'),
            ('ghop','Task-based')], required=True),
        }

    reference_fields = [
        ('org_admin_agreement_link_id', soc.models.work.Work.link_id.help_text,
         ugettext('Organization Admin Agreement Document link ID')),
        ('mentor_agreement_link_id', soc.models.work.Work.link_id.help_text,
         ugettext('Mentor Agreement Document link ID')),
        ('student_agreement_link_id', soc.models.work.Work.link_id.help_text,
         ugettext('Student Agreement Document link ID')),
        ('home_link_id', soc.models.work.Work.link_id.help_text,
         ugettext('Home page Document link ID')),
        ]

    result = {}

    for key, help_text, label in reference_fields:
      result[key] = widgets.ReferenceField(
          reference_url='document', filter=['__scoped__'],
          filter_fields={'prefix': new_params['document_prefix']},
          required=False, label=label, help_text=help_text)

    result['workflow'] = forms.CharField(widget=widgets.ReadOnlyInput(),
                                         required=True)
    result['clean'] = cleaning.clean_refs(new_params,
                                          [i for i,_,_ in reference_fields])

    new_params['edit_extra_dynaproperties'] = result

    document_references = [
        ('org_admin_agreement_link_id', 'org_admin_agreement',
         lambda x: x.org_admin_agreement),
        ('mentor_agreement_link_id', 'mentor_agreement',
         lambda x: x.mentor_agreement),
        ('student_agreement_link_id', 'student_agreement',
         lambda x: x.student_agreement),
        ]

    new_params['references'] = document_references

    params = dicts.merge(params, new_params, sub_merge=True)

    super(View, self).__init__(params=params)

  def _getAcceptedOrgsList(self, description, params, filter, use_cache):
    """Returns a list with all accepted orgs.

    Args:
      description: the description of the list
      params: the params to use
      filter: the filter to use
      use_cache: whether or not to use the cache
    """

    logic = params['logic']

    order = ['name']

    if not use_cache:
      fun = self._getData
    else:
      # only cache if all profiles are created
      fun =  soc.cache.logic.cache(self._getData)
    entities = fun(logic.getModel(), filter, order, logic)

    result = dicts.rename(params, params['list_params'])
    result['action'] = (redirects.getHomeRedirect, params)
    result['description'] = description
    result['pagination'] = 'soc/list/no_pagination.html'
    result['data'] = entities

    return result

  @decorators.merge_params
  @decorators.check_access
  def acceptedOrgs(self, request, access_type,
                   page_name=None, params=None, filter=None, **kwargs):
    """See base.View.list.
    """

    contents = []
    logic = params['logic']

    program_entity = logic.getFromKeyFieldsOr404(kwargs)

    fmt = {'name': program_entity.name}
    description = self.DEF_ACCEPTED_ORGS_MSG_FMT % fmt

    filter = {
        'status': 'accepted',
        'scope': program_entity,
        }

    from soc.views.models import org_app as org_app_view
    aa_params = org_app_view.view.getParams().copy() # accepted applications

    # define the list redirect action to show the notification
    del aa_params['list_key_order']
    aa_params['list_action'] = (redirects.getHomeRedirect, aa_params)
    aa_params['list_description'] = description

    aa_list = lists.getListContent(request, aa_params, filter, idx=0,
                                   need_content=True)

    if aa_list:
      contents.append(aa_list)

    use_cache = not aa_list # only cache if there are no aa's left
    description = self.DEF_CREATED_ORGS_MSG_FMT % fmt

    filter['status'] = ['new', 'active']

    from soc.views.models.organization import view as org_view
    ao_params = org_view.getParams().copy() # active orgs
    ao_list = self._getAcceptedOrgsList(description, ao_params, 
        filter, use_cache)

    contents.append(ao_list)

    params = params.copy()
    params['list_msg'] = program_entity.accepted_orgs_msg

    return self._list(request, params, contents, page_name)

  @decorators.merge_params
  @decorators.check_access
  def acceptedProjects(self, request, access_type,
                       page_name=None, params=None, filter=None, **kwargs):
    """See base.View.list.
    """
    contents = []
    logic = params['logic']

    program_entity = logic.getFromKeyFieldsOr404(kwargs)

    filter = {
        'status': 'accepted',
        'program': program_entity}

    fmt = {'name': program_entity.name}
    description = self.DEF_ACCEPTED_PROJECTS_MSG_FMT % fmt

    from soc.views.models import student_project as sp_view

    ap_params = sp_view.view.getParams().copy() # accepted projects
    ap_params['list_action'] = (redirects.getPublicRedirect, ap_params)
    ap_params['list_description'] = description
    ap_params['list_heading'] = 'soc/student_project/list/heading_all.html'
    ap_params['list_row'] = 'soc/student_project/list/row_all.html'

    return self.list(request, access_type, page_name=page_name,
                     params=ap_params, filter=filter)

  @decorators.merge_params
  @decorators.check_access
  def slots(self, request, acces_type, page_name=None, params=None, **kwargs):
    """Returns a JSON object with all orgs allocation.

    Args:
      request: the standard Django HTTP request object
      access_type : the name of the access type which should be checked
      page_name: the page name displayed in templates as page and header title
      params: a dict with params for this View, not used
    """
    
    from django.utils import simplejson

    program = program_logic.logic.getFromKeyFieldsOr404(kwargs)
    program_slots = program.slots

    filter = {
          'scope': program,
          'status': 'active',
          }

    query = org_logic.logic.getQueryForFields(filter=filter)
    organizations = org_logic.logic.getAll(query)

    locked_slots = adjusted_slots = {}

    if request.method == 'POST' and 'result' in request.POST:
      result = request.POST['result']
      submit = request.GET.get('submit')
      load = request.GET.get('load')
      stored = program.slots_allocation

      if load and stored:
        result = stored

      from_json = simplejson.loads(result)

      locked_slots = dicts.groupDictBy(from_json, 'locked', 'slots')

      if submit:
        program.slots_allocation = result
        program.put()

    orgs = {}
    applications = {}
    max = {}

    for org in organizations:
      orgs[org.link_id] = org
      applications[org.link_id] = org.nr_applications
      max[org.link_id] = min(org.nr_mentors, org.slots_desired)

    max_slots_per_org = program.max_slots
    min_slots_per_org = program.min_slots
    algorithm = 2

    allocator = allocations.Allocator(orgs.keys(), applications, max,
                                      program_slots, max_slots_per_org,
                                      min_slots_per_org, algorithm)

    result = allocator.allocate(locked_slots)

    data = []

    # TODO: remove adjustment here and in the JS
    for link_id, count in result.iteritems():
      org = orgs[link_id]
      data.append({
          'link_id': link_id,
          'slots': count,
          'locked': locked_slots.get(link_id, 0),
          'adjustment': adjusted_slots.get(link_id, 0),
          })

    return self.json(request, data)

  @decorators.merge_params
  @decorators.check_access
  def assignSlots(self, request, access_type, page_name=None,
                  params=None, **kwargs):
    """View that allows to assign slots to orgs.
    """

    from soc.views.models import organization as organization_view

    org_params = organization_view.view.getParams().copy()
    org_params['list_template'] = 'soc/program/allocation/allocation.html'
    org_params['list_heading'] = 'soc/program/allocation/heading.html'
    org_params['list_row'] = 'soc/program/allocation/row.html'
    org_params['list_pagination'] = 'soc/list/no_pagination.html'

    program = program_logic.logic.getFromKeyFieldsOr404(kwargs)

    description = self.DEF_SLOTS_ALLOCATION_MSG

    filter = {
        'scope': program,
        'status': 'active',
        }

    content = self._getAcceptedOrgsList(description, org_params, filter, False)

    contents = [content]

    return_url =  "http://%(host)s%(index)s" % {
      'host' : os.environ['HTTP_HOST'],
      'index': redirects.getSlotsRedirect(program, params)
      }

    context = {
        'total_slots': program.slots,
        'uses_json': True,
        'uses_slot_allocator': True,
        'return_url': return_url,
        }

    return self._list(request, org_params, contents, page_name, context)

  @decorators.merge_params
  @decorators.check_access
  def showDuplicates(self, request, access_type, page_name=None,
                     params=None, **kwargs):
    """View in which a host can see which students have been assigned 
       multiple slots.

    For params see base.view.Public().
    """

    from django.utils import simplejson

    from soc.logic.models.proposal_duplicates import logic as duplicates_logic

    program_entity = program_logic.logic.getFromKeyFieldsOr404(kwargs)

    if request.POST and request.POST.get('result'):
      # store result in the datastore
      fields = {'link_id': program_entity.link_id,
                'scope': program_entity,
                'scope_path': program_entity.key().id_or_name(),
                'json_representation' : request.POST['result']
                }
      key_name = duplicates_logic.getKeyNameFromFields(fields)
      duplicates_logic.updateOrCreateFromKeyName(fields, key_name)

      response = simplejson.dumps({'status': 'done'})
      return http.HttpResponse(response)

    context = helper.responses.getUniversalContext(request)
    helper.responses.useJavaScript(context, params['js_uses_all'])
    context['uses_duplicates'] = True
    context['uses_json'] = True
    context['page_name'] = page_name

    # get all orgs for this program who are active and have slots assigned
    fields = {'scope': program_entity,
              'slots >': 0,
              'status': 'active'}

    query = org_logic.logic.getQueryForFields(fields)

    to_json = {
        'nr_of_orgs': query.count(),
        'program_key': program_entity.key().id_or_name()}
    json = simplejson.dumps(to_json)
    context['info'] = json
    context['offset_length'] = 10

    fields = {'link_id': program_entity.link_id,
              'scope': program_entity}
    duplicates = duplicates_logic.getForFields(fields, unique=True)

    if duplicates:
      # we have stored information
      # pylint: disable-msg=E1103
      context['duplicate_cache_content'] = duplicates.json_representation
      context['date_of_calculation'] = duplicates.calculated_on
    else:
      # no information stored
      context['duplicate_cache_content'] = simplejson.dumps({})

    template = 'soc/program/show_duplicates.html'

    return helper.responses.respond(request, template=template, context=context)

  @decorators.merge_params
  @decorators.check_access
  def assignedProposals(self, request, access_type, page_name=None,
                        params=None, filter=None, **kwargs):
    """Returns a JSON dict containing all the proposals that would have
    a slot assigned for a specific set of orgs.

    The request.GET limit and offset determines how many and which
    organizations should be returned.

    For params see base.View.public().

    Returns: JSON object with a collection of orgs and proposals. Containing
             identification information and contact information.
    """

    get_dict = request.GET

    if not (get_dict.get('limit') and get_dict.get('offset')):
      return self.json(request, {})

    try:
      limit = max(0, int(get_dict['limit']))
      offset = max(0, int(get_dict['offset']))
    except ValueError:
      return self.json(request, {})

    program_entity = program_logic.logic.getFromKeyFieldsOr404(kwargs)

    fields = {'scope': program_entity,
              'slots >': 0,
              'status': 'active'}

    org_entities = org_logic.logic.getForFields(fields, 
        limit=limit, offset=offset)

    orgs_data = {}
    proposals_data = []

    # for each org get the proposals who will be assigned a slot
    for org in org_entities:

      org_data = {'name': org.name}

      fields = {'scope': org,
                'status': 'active',
                'user': org.founder}

      org_admin = org_admin_logic.logic.getForFields(fields, unique=True)

      if org_admin:
        # pylint: disable-msg=E1103
        org_data['admin_name'] = org_admin.name()
        org_data['admin_email'] = org_admin.email

      proposals = student_proposal_logic.logic.getProposalsToBeAcceptedForOrg(
          org, step_size=program_entity.max_slots)

      if not proposals:
        # nothing to accept, next organization
        continue

      # store information about the org
      orgs_data[org.key().id_or_name()] = org_data

      # store each proposal in the dictionary
      for proposal in proposals:
        student_entity = proposal.scope

        proposals_data.append(
            {'key_name': proposal.key().id_or_name(),
            'proposal_title': proposal.title,
            'student_key': student_entity.key().id_or_name(),
            'student_name': student_entity.name(),
            'student_contact': student_entity.email,
            'org_key': org.key().id_or_name()
            })

    # return all the data in JSON format
    data = {'orgs': orgs_data,
            'proposals': proposals_data}

    return self.json(request, data)

  def _editPost(self, request, entity, fields):
    """See base._editPost().
    """

    super(View, self)._editPost(request, entity, fields)

    if not entity:
      # there is no existing entity so create a new timeline
      fields['timeline'] = self._createTimelineForType(fields)
    else:
      # use the timeline from the entity
      fields['timeline'] = entity.timeline

  def _createTimelineForType(self, fields):
    """Creates and stores a timeline model for the given type of program.
    """

    workflow = fields['workflow']

    timeline_logic = program_logic.logic.TIMELINE_LOGIC[workflow]

    properties = timeline_logic.getKeyFieldsFromFields(fields)
    key_name = timeline_logic.getKeyNameFromFields(properties)

    properties['scope'] = fields['scope']

    timeline = timeline_logic.updateOrCreateFromKeyName(properties, key_name)
    return timeline

  @decorators.merge_params
  def getExtraMenus(self, id, user, params=None):
    """Returns the extra menu's for this view.

    A menu item is generated for each program that is currently
    running. The public page for each program is added as menu item,
    as well as all public documents for that program.

    Args:
      params: a dict with params for this View.
    """

    logic = params['logic']
    rights = params['rights']

    # only get all invisible and visible programs
    fields = {'status': ['invisible', 'visible']}
    entities = logic.getForFields(fields)

    menus = []

    rights.setCurrentUser(id, user)

    for entity in entities:
      items = []

      if entity.status == 'visible':
        # show the documents for this program, even for not logged in users
        items += document_view.view.getMenusForScope(entity, params)
        items += survey_view.view.getMenusForScope(entity, params)
        items += self._getTimeDependentEntries(entity, params, id, user)

      try:
        # check if the current user is a host for this program
        rights.doCachedCheck('checkIsHostForProgram',
                             {'scope_path': entity.scope_path,
                              'link_id': entity.link_id}, [])

        if entity.status == 'invisible':
          # still add the document links so hosts can see how it looks like
          items += document_view.view.getMenusForScope(entity, params)
          items += self._getTimeDependentEntries(entity, params, id, user)

        items += [(redirects.getReviewOverviewRedirect(
            entity, {'url_name': 'org_app'}),
            "Review Organization Applications", 'any_access')]
        # add link to edit Program Profile
        items += [(redirects.getEditRedirect(entity, params),
            'Edit Program Profile', 'any_access')]
        # add link to Assign Slots
        items += [(redirects.getAssignSlotsRedirect(entity, params),
            'Assign Slots', 'any_access')]
        # add link to Show Duplicate project assignments
        items += [(redirects.getShowDuplicatesRedirect(entity, params),
            'Show Duplicate Project Assignments', 'any_access')]
        # add link to edit Program Timeline
        items += [(redirects.getEditRedirect(entity, {'url_name': 'timeline'}),
            "Edit Program Timeline", 'any_access')]
        # add link to create a new Program Document
        items += [(redirects.getCreateDocumentRedirect(entity, 'program'),
            "Create a New Document", 'any_access')]
        # add link to list all Program Document
        items += [(redirects.getListDocumentsRedirect(entity, 'program'),
            "List Documents", 'any_access')]
        # add link to create a new Program Survey
        items += [(redirects.getCreateSurveyRedirect(entity, 'program'),
            "Create a New Survey", 'any_access')]
        # add link to list all Program Surveys
        items += [(redirects.getListSurveysRedirect(entity, 'program'),
            "List Surveys", 'any_access')]
        # add link to create a new Program Survey
        items += [(redirects.getCreateProjectSurveyRedirect(entity, 'program'),
            "Create a New Project Survey", 'any_access')]
        # add link to list all Program Surveys
        items += [(redirects.getListProjectSurveyRedirect(entity, 'program'),
            "List Project Surveys", 'any_access')]
        # add link to create a new Program Survey
        items += [(redirects.getCreateGradeSurveyRedirect(entity, 'program'),
            "Create a New Grading Survey", 'any_access')]
        # add link to list all Program Surveys
        items += [(redirects.getListGradeSurveysRedirect(entity, 'program'),
            "List Grading Surveys", 'any_access')]

      except out_of_band.Error:
        pass

      items = sidebar.getSidebarMenu(id, user, items, params=params)
      if not items:
        continue

      menu = {}
      menu['heading'] = entity.short_name
      menu['items'] = items
      menu['group'] = 'Programs'
      menus.append(menu)

    return menus

  def _getTimeDependentEntries(self, program_entity, params, id, user):
    """Returns a list with time dependent menu items.
    """
    items = []

    #TODO(ljvderijk) Add more timeline dependent entries
    timeline_entity = program_entity.timeline

    if timeline_helper.isActivePeriod(timeline_entity, 'org_signup'):
      # add the organization signup link
      items += [
          (redirects.getApplyRedirect(program_entity, {'url_name': 'org_app'}),
          "Apply to become an Organization", 'any_access')]

    if user and timeline_helper.isAfterEvent(timeline_entity, 
        'org_signup_start'):
      filter = {
          'applicant': user,
          'scope': program_entity,
          }

      if org_app_logic.logic.getForFields(filter, unique=True):
        # add the 'List my Organization Applications' link
        items += [
            (redirects.getListSelfRedirect(program_entity,
                                           {'url_name' : 'org_app'}),
             "List My Organization Applications", 'any_access')]

    # get the student entity for this user and program
    filter = {'user': user,
              'scope': program_entity,
              'status': 'active'}
    student_entity = student_logic.logic.getForFields(filter, unique=True)

    if student_entity:
      items += self._getStudentEntries(program_entity, student_entity,
                                       params, id, user)

    # get mentor and org_admin entity for this user and program
    filter = {'user': user,
              'program': program_entity,
              'status': 'active'}
    mentor_entity = mentor_logic.logic.getForFields(filter, unique=True)
    org_admin_entity = org_admin_logic.logic.getForFields(filter, unique=True)

    if mentor_entity or org_admin_entity:
      items += self._getOrganizationEntries(program_entity, org_admin_entity,
                                            mentor_entity, params, id, user)

    if user and not (student_entity or mentor_entity or org_admin_entity):
      if timeline_helper.isActivePeriod(timeline_entity, 'student_signup'):
        # this user does not have a role yet for this program
        items += [('/student/apply/%s' % (program_entity.key().id_or_name()),
            "Register as a Student", 'any_access')]

    deadline = 'accepted_organization_announced_deadline'

    if timeline_helper.isAfterEvent(timeline_entity, deadline):
      url = redirects.getAcceptedOrgsRedirect(program_entity, params)
      # add a link to list all the organizations
      items += [(url, "List participating Organizations", 'any_access')]

      if not student_entity:
        # add apply to become a mentor link
        items += [('/org/apply_mentor/%s' % (program_entity.key().id_or_name()),
         "Apply to become a Mentor", 'any_access')]

    deadline = 'accepted_students_announced_deadline'

    if timeline_helper.isAfterEvent(timeline_entity, deadline):
      items += [(redirects.getListProjectsRedirect(program_entity,
          {'url_name':'program'}),
          "List all student projects", 'any_access')]

    return items

  def _getStudentEntries(self, program_entity, student_entity, 
                         params, id, user):
    """Returns a list with menu items for students in a specific program.
    """

    items = []

    timeline_entity = program_entity.timeline

    if timeline_helper.isActivePeriod(timeline_entity, 'student_signup'):
      items += [('/student_proposal/list_orgs/%s' % (
          student_entity.key().id_or_name()),
          "Submit your Student Proposal", 'any_access')]

    if timeline_helper.isAfterEvent(timeline_entity, 'student_signup_start'):
      items += [(redirects.getListSelfRedirect(student_entity,
          {'url_name':'student_proposal'}),
          "List my Student Proposals", 'any_access')]

    items += [(redirects.getEditRedirect(student_entity, 
        {'url_name': 'student'}),
        "Edit my Student Profile", 'any_access')]

    if timeline_helper.isAfterEvent(timeline_entity,
                                   'accepted_students_announced_deadline'):
      # add a link to show all projects
      items += [(redirects.getListProjectsRedirect(program_entity,
          {'url_name':'student'}),
          "List my Student Projects", 'any_access')]

    return items

  def _getOrganizationEntries(self, program_entity, org_admin_entity,
                              mentor_entity, params, id, user):
    """Returns a list with menu items for org admins and mentors in a
       specific program.
    """

    # TODO(ljvderijk) think about adding specific org items like submit review

    items = []

    return items


view = View()

accepted_orgs = decorators.view(view.acceptedOrgs)
list_projects = decorators.view(view.acceptedProjects)
admin = decorators.view(view.admin)
assign_slots = decorators.view(view.assignSlots)
assigned_proposals = decorators.view(view.assignedProposals)
create = decorators.view(view.create)
delete = decorators.view(view.delete)
edit = decorators.view(view.edit)
list = decorators.view(view.list)
public = decorators.view(view.public)
export = decorators.view(view.export)
show_duplicates = decorators.view(view.showDuplicates)
slots = decorators.view(view.slots)
home = decorators.view(view.home)
pick = decorators.view(view.pick)
