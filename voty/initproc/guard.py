# -*- coding: utf-8 -*-
# ==============================================================================
# voty initproc guard - single one place, where all permissions are defined
# ==============================================================================
#
# parameters (*default)
# ------------------------------------------------------------------------------

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.apps import apps
from django.utils.functional import cached_property

from functools import wraps
from voty.initadmin.models import UserConfig
from voty.initproc.models import Moderation
from .globals import STATES, PUBLIC_STATES, TEAM_ONLY_STATES, INITIATORS_COUNT
from .models import Initiative, Supporter
from django.conf import settings
from django.utils import six
from django.utils.translation import ugettext as _

def _compound_action(func):
    @wraps(func)
    def wrapped(self, obj=None, *args, **kwargs):
        if obj is None: # if none given, fall back to the initiative of the request
            obj = self.request.initiative
        try:
            return getattr(self, "_{}_{}".format(func.__name__, obj._meta.model_name))(obj, *args, **kwargs)
        except (AttributeError, ContinueChecking):
            return func(self, obj)
    return wrapped

# ================================= CLASSES ====================================   
# ---------------------------- continue checking -------------------------------
class ContinueChecking(Exception):
  pass

# ---------------- Instance of the Guard for the given user --------------------
class Guard:

  def __init__(self, user, request=None):
    self.user = user
    self.request = request

    # XXX REASON IS NOT THREAD SAFE, but works good enough for us for now.
    self.reason = None

  # --------------------- missing moderation reviews to continue -----------------
  def _missing_moderation_reviews(self, policy):
  
    # total moderators required are based on percentage/minimum person
    total = policy.required_moderations 
    raise Exception(total)
    # overall moderations on this policy
    # XXX what if only policy team proposes and not enough moderators?
    moderations = policy.policy_moderations.filter(stale=False)
    total -= moderations.count()
  
    # moderator diversity are optional
    if bool(int(settings.USE_DIVERSE_MODERATION_TEAM)):
      female  = int(settings.PLATFORM_MODERATION_SETTING_LIST.MINIMUM_FEMALE_MODERATOR_VOTES)
      diverse = int(settings.PLATFORM_MODERATION_SETTING_LIST.MINIMUM_DIVERSE_MODERATOR_VOTES)
  
      # exclude moderator from required quotas if he/she is initiator
      for user_config in UserConfig.objects.filter(user_id__in=moderations.values("user_id")):
        if user_config.is_female_mod:
          female -= 1
        if user_config.is_diverse_mod:
          diverse -= 1
      return (female, diverse, total)
  
    # by default only check for total
    return (0, 0, total)

  def make_intiatives_query(self, filters):
      if not self.user.is_authenticated:
          filters = [f for f in filters if f in PUBLIC_STATES]
      elif not self.user.has_perm('initproc.add_moderation'):
          filters = [f for f in filters if f not in TEAM_ONLY_STATES]

      if self.user.is_authenticated and not self.user.has_perm('initproc.add_moderation'):
          return Initiative.objects.filter(Q(state__in=filters) | Q(state__in=TEAM_ONLY_STATES,
                  id__in=Supporter.objects.filter(Q(first=True) | Q(initiator=True), user_id=self.user.id).values('initiative_id')))

      return Initiative.objects.filter(state__in=filters)

  @_compound_action
  def can_comment(self, obj=None):
      if (isinstance (obj,Moderation)):
          return True

      self.reason = None
      latest_comment = obj.comments.order_by("-created_at").first()

      if not latest_comment and obj.user == self.user:
          self.reason = _("You can comment on your Argument only after another person has added a comment.")
          return False
      elif latest_comment and latest_comment.user == self.user:
          self.reason = _("To foster the discussion you can comment on your Argument only after another person has added a comment.")
          return False

      return True

  def can_like(self, obj=None):
      if obj.user == self.user: # should apply for both arguments and comments
          return False

      return True

  def is_editable(self, obj=None): #likes
      initiative = self.find_parent_initiative(obj)
      if initiative and initiative.state in [STATES.ACCEPTED, STATES.REJECTED]: # no liking of closed inis
          return False
      return True

  def find_parent_initiative(self, obj=None):
      # find initiative in object tree
      while not hasattr(obj, "initiative") and hasattr(obj, "target"):
          obj = obj.target
      return obj.initiative if hasattr(obj, "initiative") else obj

  def is_initiator(self, init):
      return init.supporting_initiative.filter(initiator=True, user_id=self.user.id)

  def is_supporting(self, init):
      return init.supporting_initiative.filter(user_id=self.user.id)

  def my_vote(self, init):
      return init.votes.filter(user=self.user.id).first()

  @_compound_action
  def can_view(self, obj=None):
      # fallback if compound doesn't match
      return False

  @_compound_action
  def can_edit(self, obj=None):
      # fallback if compound doesn't match
      return False

  @_compound_action
  def can_publish(self, obj=None):
      # fallback if compound doesn't match
      return False

  @_compound_action
  def can_support(self, obj=None):
      # fallback if compound doesn't match
      return False

  @_compound_action
  def can_moderate(self, obj=None):
      # fallback if compound doesn't match
      return False

  # 
  #    INITIATIVES
  #    -----------
  # 
  def should_moderate_initiative(self, init=None):
      init = init or self.request.initiative
      if not self._can_moderate_initiative(init):
          return False

      moderations = init.moderations.filter(stale=False)

      if moderations.filter(user=self.user):
          # has already voted, thanks, bye
          return False

      (female,diverse,total) = self._missing_moderation_reviews(init)
      try:
          if female > 0:
              if self.user.config.is_female_mod:
                  return True

          if diverse > 0:
              if self.user.config.is_diverse_mod:
                  return True
      except User.config.RelatedObjectDoesNotExist:
          pass

      # user cannot contribute to fulfilling quota -- should moderate unless we already know it'll be wasted
      return (total > female) & (total > diverse)

  def can_inivite_initiators(self, init=None):
      init = init or self.request.initiative
      if init.state != STATES.PREPARE:
          return False

      if not self._can_edit_initiative(init):
          return False

      return init.supporting_initiative.filter(initiator=True).count() < INITIATORS_COUNT

  ## compounds

  def _can_view_initiative(self, init):
      if init.state not in TEAM_ONLY_STATES:
          return True

      if not self.user.is_authenticated:
          return False

      if not self.user.has_perm('initproc.add_moderation') and \
         not init.supporting_initiative.filter(Q(first=True) | Q(initiator=True), user_id=self.request.user.id):
          return False

      return True

  def _can_edit_initiative(self, init):
      if not init.state in [STATES.PREPARE, STATES.FINAL_EDIT]:
          return False
      if not self.user.is_authenticated:
          return False
      if self.user.is_superuser:
          return True
      if not init.supporting_initiative.filter(initiator=True, user_id=self.request.user.id):
          return False

      return True

  def _can_publish_initiative(self, init):
      if not self.user.has_perm('initproc.add_moderation'):
          return False

      if init.supporting_initiative.filter(ack=True, initiator=True).count() != INITIATORS_COUNT:
          return False

      if init.moderations.filter(stale=False, vote='n'): # We have NAYs
          return False

      (female,diverse,total) = self._missing_moderation_reviews(init)

      return (female <= 0) & (diverse <= 0) & (total <= 0)

  def _can_support_initiative(self, init):
      return init.state == STATES.SEEKING_SUPPORT and self.user.is_authenticated

  def _can_moderate_initiative(self, init):
      if init.state in [STATES.INCOMING, STATES.MODERATION] and self.user.has_perm('initproc.add_moderation'):
          if init.supporting_initiative.filter(user=self.user, initiator=True):
              self.reason = _("As Co-Initiator you are not authorized to moderate.")
              return False
          return True
      return False

  def _can_comment_pro(self, obj=None):
      if obj.initiative.state == STATES.DISCUSSION:
          raise ContinueChecking()
      return False

  def _can_comment_contra(self, obj=None):
      if obj.initiative.state == STATES.DISCUSSION:
          raise ContinueChecking()
      return False

  def _can_comment_proposal(self, obj=None):
      if obj.initiative.state == STATES.DISCUSSION:
          raise ContinueChecking()
      return False

  # XXX permissions contain a lot of duplicate code, improve later once all set

  # XXX this should be calculated elsewhere?
  # @cached_property
  # def minimum_moderation_reviews(self):
  #  return self._get_policy_minium_moderator_votes()

  # ----------------- invite co-initiators/supporters to policy ----------------
  def policy_invite(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if policy.state != settings.PLATFORM_POLICY_STATE_DICT.STAGED:
      return False
    if not self.policy_edit(policy):
      return False
    if user.is_superuser:
      return False

    # XXX Initiators will change depending on level
    return policy.supporting_policy.filter(initiator=True).count() < int(settings.PLATFORM_POLICY_INITIATORS_COUNT)

  # ---------------------------- view policy -----------------------------------
  # used to be in can_access_initiative
  def policy_view(self, policy=None):
    policy = policy or self.request.policy
    user = self.user
    
    if policy.state in settings.PLATFORM_POLICY_ADMIN_STATE_LIST:
      if user.has_perm("initproc.policy_can_validate") or user.is_superuser:
        return True
      if policy.supporting_policy.filter(initiator=True, user=user.id):
        return True
      return False

    if policy.state == settings.PLATFORM_POLICY_STATE_DICT.DRAFT and \
      not policy.supporting_policy.filter(first=True, user_id=user.id):
      return False

    return True

  # ---------------------------- edit policy -----------------------------------
  def policy_edit(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not user.is_authenticated:
      return False
    if not policy.state in settings.PLATFORM_POLICY_EDIT_STATE_LIST:
      return False
    if user.is_superuser:
      return True
    if not policy.supporting_policy.filter(initiator=True, ack=True, user_id=user.id):
      return False
    return True

  # ---------------------------- stage policy -----------------------------------
  def policy_stage(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not user.is_authenticated:
      return False
    if policy.state == settings.PLATFORM_POLICY_STATE_DICT.DRAFT:
      if policy.supporting_policy.filter(initiator=True) or \
        user.is_superuser:
          return True
    return False

  # ---------------------------- delete policy ---------------------------------
  def policy_delete(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not user.is_authenticated:
      return False
    if policy.state in settings.PLATFORM_POLICY_DELETE_STATE_LIST:
      if policy.supporting_policy.filter(initiator=True) or \
        user.has_perm("initproc.policy_can_delete") or \
        user.is_superuser:
          return True
    return False

  # --------------------------- undelete policy --------------------------------
  def policy_undelete(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not user.is_authenticated:
      return False
    if policy.state in settings.PLATFORM_POLICY_STATE_DICT.DELETED and \
      (user.has_perm("initproc.policy_can_delete") or user.is_superuser):
      return True
    return False

  # --------------------------- unhide policy --------------------------------
  def policy_unhide(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not user.is_authenticated:
      return False
    if policy.state in settings.PLATFORM_POLICY_STATE_DICT.HIDDEN and \
      (user.has_perm("initproc.policy_can_unhide") or user.is_superuser):
      return True
    return False

  # ---------------------------- submit policy ---------------------------------
  def policy_submit(self, policy=None):
    policy = policy or self.request.policy
    user = self.user
    initiators = policy.supporting_policy.filter(initiator=True, ack=True)

    if not user.is_authenticated:
      return False
    if not policy.supporting_policy.filter(initiator=True, ack=True, user_id=user.id):
      return False
    if policy.state == settings.PLATFORM_POLICY_STATE_DICT.STAGED or \
      policy.state == settings.PLATFORM_POLICY_STATE_DICT.INVALIDATED:
      if initiators.count() >= int(settings.PLATFORM_POLICY_INITIATORS_COUNT):
        if policy.supporting_policy.filter(initiator=True, ack=True, user_id=user.id) or user.is_superuser:
          return True
    return False

  # -------------------------- review policy ---------------------------------
  # checks if user technically CAN review/validate
  def policy_validate(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    #if policy.state == settings.PLATFORM_POLICY_STATE_DICT.INVALIDATED:
    #  if policy.supporting_policy.filter(initiator=True) or user.is_superuser:
    #    return True

    if policy.state in settings.PLATFORM_POLICY_MODERATION_STATE_LIST:
      if user.has_perm("initproc.policy_can_validate") or user.is_superuser:

        # leaving this means, moderator/initiators never see feedback
        # moved to should moderate
        #if policy.supporting_policy.filter(user=user, initiator=True):
        #  self.reason = _("Moderation not possible: Initiators cannot moderate own Policy")
        #  return False
        return True
    return False

  # ---------------------- should validate policy ------------------------------
  # checks if user SHOULD validate - this method should test against all "soft"
  # criteria, like female/diverse etc moderators
  def policy_review_eligible(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if not self.policy_validate(policy):
      return False

    if policy.supporting_policy.filter(user=user, initiator=True):
      self.reason = _("Moderation not possible: Initiators can not moderate own Policy")
      return False

    moderations = policy.policy_moderations.filter(stale=False)

    # already moderated, done
    if moderations.filter(user=self.user):
      return False
    
    # custom criteria
    (female, diverse, total) = self._missing_moderation_reviews(policy)
    try:
      if female > 0:
        if self.user.config.is_female_mod:
          return True
      if diverse > 0:
        if self.user.config.is_diverse_mod:
          return True
    except User.config.RelatedObjectDoesNotExist:
      pass

    # XXX "user cannot contribute to fulfilling quota -- should moderate unless 
    # we already know it'll be wasted" => why?
    return (total > female) & (total > diverse)

  # ---------------------- comment X (anything...) -----------------------------
  def target_comment(self, target_object=None):

    # XXX why should moderations have no restrictions toward multiple comments?
    #if (isinstance (target_object, Moderation)):
    #  return True

    self.reason = None
    last_comment = target_object.comments.order_by("-created_at").first()

    if not last_comment and target_object.user == self.user:
      self.reason = _("Comment not possible: Please wait for another user to comment.")
      return False

    # XXX what's the difference?
    elif last_comment and last_comment.user == self.user:
      self.reason = _("Comment not possible: Please wait for another user to comment.")
      return False

    return True

  # ------------------------- invalidate policy --------------------------------
  def policy_invalidate(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if policy.state in settings.PLATFORM_POLICY_MODERATION_STATE_LIST:
      if user.has_perm("initproc.policy_can_invalidate") or user.is_superuser:
        if policy.supporting_policy.filter(user=user, initiator=True):
          self.reason = _("Moderation not possible: Initiators can not moderate own Policy")
          return False
        return True
    return False

  # --------------------------- reject policy ----------------------------------
  def policy_reject(self, policy=None):
    policy = policy or self.request.policy
    user = self.user

    if policy.state in settings.PLATFORM_POLICY_MODERATION_STATE_LIST:
      if user.has_perm("initproc.policy_can_reject") or user.is_superuser:
        if policy.supporting_policy.filter(user=user, initiator=True):
          self.reason = _("Moderation not possible: Initiators can not moderate own Policy")
          return False
        return True
    return False

# ----------------------------- Publish Guard ----------------------------------
# Add guard of the request.user and make it accessible directly at request.guard
# This will be called from middleware, see settings.py
def add_guard(get_response):
  def middleware(request):
    guard = Guard(request.user, request)
    request.guard = guard
    request.user.guard = guard

    response = get_response(request)
    return response

  return middleware

