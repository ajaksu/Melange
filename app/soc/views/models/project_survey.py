#!/usr/bin/python2.5
#
# Copyright 2009 the Melange authors.
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

"""Views for ProjectSurveys.
"""

__authors__ = [
  '"Lennard de Rijk" <ljvderijk@gmail.com>',
  ]


from soc.logic import dicts
from soc.logic.models.survey import project_logic as project_survey_logic
from soc.views.helper import access
from soc.views.helper import decorators
from soc.views.models import survey


class View(survey.View):
  """View methods for the ProjectSurvey model.
  """

  def __init__(self, params=None):
    """Defines the fields and methods required for the base View class
    to provide the user with list, public, create, edit and delete views.

    Params:
      params: a dict with params for this View
    """

    rights = access.Checker(params)
    rights['any_access'] = ['allow']
    rights['show'] = [('checkIsSurveyReadable', project_survey_logic)]
    rights['create'] = ['checkIsUser']
    rights['edit'] = [('checkIsSurveyWritable', project_survey_logic)]
    rights['delete'] = [('checkIsSurveyWritable', project_survey_logic)]
    rights['list'] = ['checkDocumentList']
    rights['pick'] = ['checkDocumentPick']

    new_params = {}
    new_params['logic'] = project_survey_logic
    new_params['rights'] = rights

    new_params['name'] = "Project Survey"

    new_params['extra_dynaexclude'] = ['taking_access']

    params = dicts.merge(params, new_params)

    super(View, self).__init__(params=params)


view = View()

admin = decorators.view(view.admin)
create = decorators.view(view.create)
edit = decorators.view(view.edit)
delete = decorators.view(view.delete)
list = decorators.view(view.list)
public = decorators.view(view.public)
export = decorators.view(view.export)
pick = decorators.view(view.pick)
results = decorators.view(view.viewResults)
json = decorators.view(view.exportSerialized)
