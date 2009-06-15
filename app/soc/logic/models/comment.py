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

"""Comment query functions.
"""

__authors__ = [
  '"Matthew Wilkes" <matthew@matthewwilkes.co.uk>',
  ]


from soc.logic.models import base
from soc.logic.models import linkable as linkable_logic
from soc.logic.models.news_feed import logic as newsfeed_logic
import soc.models.comment


class Logic(base.Logic):
  """Logic methods for the comment model
  """

  def __init__(self, model=soc.models.comment.Comment,
               base_model=None, scope_logic=linkable_logic):
    """Defines the name, key_name and model for this entity.
    """

    super(Logic, self).__init__(model=model, base_model=base_model,
                                scope_logic=scope_logic)


  def _onCreate(self, entity):
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "created")

  def _onUpdate(self, entity):
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "updated")

  def _onDelete(self, entity):
    receivers = [entity.scope]
    newsfeed_logic.addToFeed(entity, receivers, "deleted")
    
logic = Logic()
