# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def migrate_users(apps, schema_editor):
    UserOld = apps.get_model(settings.OLD_AUTH_USER_MODEL)
    UserProfile = apps.get_model('spirit', 'UserProfile')
    profiles = []

    for user in UserOld.objects.all():
        st = UserProfile()
        st.user = user
        st.slug = user.slug
        st.location = user.location
        st.last_seen = user.last_seen
        st.last_ip = user.last_ip
        st.timezone = user.timezone
        st.is_administrator = user.is_administrator
        st.is_moderator = user.is_moderator
        st.is_verified = user.is_verified
        st.topic_count = user.topic_count
        st.comment_count = user.comment_count
        profiles.append(st)

    UserProfile.objects.bulk_create(profiles)


class Migration(migrations.Migration):

    dependencies = [
        ('spirit', '0007_userprofile'),
    ]

    operations = [
        migrations.RunPython(migrate_users),
    ]
