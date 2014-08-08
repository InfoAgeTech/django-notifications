from __future__ import unicode_literals

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django_core.db.models.mixins.base import AbstractBaseModel
from django_core.db.models.mixins.generic import AbstractGenericObject
from django_core.db.models.mixins.urls import AbstractUrlLinkModelMixin
from django_core.utils.loading import get_class_from_settings

from .constants import Action
from .constants import Source
from .managers import NotificationReplyManager


try:
    AbstractNotificationMixin = get_class_from_settings(
        settings_key='NOTIFICATION_MODEL_MIXIN'
    )
except NotImplementedError:
    from django_core.db.models import AbstractHookModelMixin as AbstractNotificationMixin

try:
    NotificationManager = get_class_from_settings(
        settings_key='NOTIFICATION_MANAGER'
    )
except NotImplementedError:
    from .managers import NotificationManager


class AbstractNotification(AbstractBaseModel):
    """Abstract extensible model for Notifications.

    Attributes:

    * about: object the notification is referring to.
    * about_id: id this object the notification pertains to.
    * about_content_type: the content type of the about object
    * text: the text of the notification.  This can include html. This is not
        required because you can construct the text based on the other object
        attributes.  For example, if I have an object ``car`` with a status of
        ``CREATED`` then I can construct the text as follows:

            ``Car object`` was ``created`` by ``created_user``
    * replies: list of replies to this notification
    * for_objs: list of docs this notification is for. For example,
        if a comment is made on a object "A" which has an object "B", then this
        list will include references to the::

            1. object "A"
            2. object "B"
            4. users who are sharing this object

    * source: the source of notification.  Can be one if constant.Source
        choices (i.e. 'USER' generated comment, 'SYSTEM' activity on an
        object, etc)
    * action: the action (verb) that describes what happend ('CREATED',
        'UPDATED', 'DELETED', 'COMMENTED')
    """
    text = models.TextField(blank=True, null=True)
    about = generic.GenericForeignKey(ct_field='about_content_type',
                                      fk_field='about_id')
    about_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    about_id = models.PositiveIntegerField(null=True, blank=True)
    replies = models.ManyToManyField('NotificationReply',
                                     related_name='replies',
                                     blank=True,
                                     null=True)
    for_objs = models.ManyToManyField('NotificationFor',
                                      related_name='for_objs',
                                      blank=True,
                                      null=True)
    source = models.CharField(max_length=20, choices=Source.CHOICES)
    action = models.CharField(max_length=20, choices=Action.CHOICES)
    objects = NotificationManager()

    class Meta:
        abstract = True

    def is_comment(self):
        """Boolean indicating if the notification type is a comment."""
        return self.action == Action.COMMENTED

    def is_activity(self):
        """Boolean indicating if the notification type is an activity."""
        return self.source == Source.SYSTEM

    def add_reply(self, user, text, reply_to=None):
        """Adds a reply to a Notification

        :param user: the user the reply is from.
        :param text: the text for the reply.
        :param reply_to: is a reply to a specific reply.

        """
        reply = self.replies.create(created_user=user,
                                    last_modified_user=user,
                                    text=text,
                                    reply_to=reply_to,
                                    notification=self)
        # TODO: If the user isn't part of the for_objs they should be added
        #       because they are not part of the conversation?
        # self.notificationfor_set.get_or_create_generic(content_object=user)
        return reply

    def get_text(self):
        """Gets the text for an object.  If text is None, this will construct
        the text based on the notification attributes.
        """
        if self.text:
            return self.text

        action = Action.get_display(self.action) or self.action
        # `troy` created the `movie` (movie name)
        # TODO: need to differentiate system activity from user created
        #       activity.
        return '{created_user} {action} the {object_name} {object}'.format(
            created_user=self.created_user.username,
            action=action.lower(),
            object_name=self.about_content_type.model_class()._meta.verbose_name,
            object=self.about
        )

    def get_for_objects(self):
        """Gets the actual objects the notification is for."""
        return [obj.content_object
                for obj in self.for_objs.all().prefetch_related(
                                                            'content_object')]

    def get_replies(self):
        """Gets the notification reply objects for this notification."""
        return self.notificationreply_set.all()

    def get_reply_by_id(self, reply_id):
        """Gets the reply for a notification by it's id."""
        return self.notificationreply_set.get(id=reply_id)

    def delete_reply(self, reply_id):
        """Delete an individual notification reply.

        :param notification_id: ID of the notification reply to delete

        """
        self.notificationreply_set.filter(id=reply_id).delete()
        return True


class Notification(AbstractUrlLinkModelMixin, AbstractNotificationMixin,
                   AbstractNotification):
    """Concrete model for notifications."""

    class Meta:
        db_table = u'notifications'
        ordering = ('-id',)
        index_together = (('about_content_type', 'about_id'),)

    def get_absolute_url(self):
        return reverse('notification_view', args=[self.id])

    def get_edit_url(self):
        return reverse('notification_edit', args=[self.id])

    def get_delete_url(self):
        return reverse('notification_delete', args=[self.id])


class NotificationReply(AbstractUrlLinkModelMixin, AbstractBaseModel):
    """Represents a notification reply object.

    Attributes:

    * text: the text of the notification.  This can include html.
    * created_user: the person the notification was from.  This is the user who
            caused the notification to change.  This can be the same user as
            the notification is intended for (users can create notifications
            for themselves)
    * reply_to: this is a reply to a reply and is a recursive reference.

    """
    text = models.TextField(max_length=500)
    notification = models.ForeignKey('Notification')
    reply_to = models.ForeignKey('self', blank=True, null=True)
    objects = NotificationReplyManager()

    class Meta:
        ordering = ('id',)

    def get_absolute_url(self):
        return reverse('notification_reply', args=[self.notification_id,
                                                   self.id])

    def get_edit_url(self):
        return reverse('notification_reply_edit', args=[self.notification_id,
                                                        self.id])

    def get_delete_url(self):
        return reverse('notification_reply_delete', args=[self.notification_id,
                                                          self.id])


@python_2_unicode_compatible
class NotificationFor(AbstractGenericObject):
    """Defines the generic object a notification is for."""
#
#     class Meta:
#         proxy = True

    def __str__(self):
        return '{0} {1}'.format(self.content_type, self.object_id)
