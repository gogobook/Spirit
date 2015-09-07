# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from ...core.tests import utils
from ..models import Comment
from .models import CommentPoll, CommentPollChoice, CommentPollVote
from .forms import PollVoteManyForm

User = get_user_model()


class PollViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = utils.create_user()
        self.user2 = utils.create_user()
        self.category = utils.create_category()
        self.topic = utils.create_topic(self.category, user=self.user)
        self.topic2 = utils.create_topic(self.category, user=self.user2)
        self.comment = utils.create_comment(topic=self.topic)
        self.user_comment = utils.create_comment(topic=self.topic, user=self.user)
        self.poll = CommentPoll.objects.create(comment=self.comment, name='foo')

    def test_poll_close_logged_in(self):
        """
        User must be logged in
        """
        response = self.client.post(reverse('spirit:comment:poll:close', kwargs={'pk': self.poll.pk, }),
                                    {})
        self.assertEqual(response.status_code, 302)

    def test_poll_close_wrong_user(self):
        """
        Try to close another user poll should return 404
        """
        utils.login(self)
        response = self.client.post(reverse('spirit:comment:poll:close', kwargs={'pk': self.poll.pk, }),
                                    {})
        self.assertEqual(response.status_code, 404)

    def test_poll_close_get(self):
        """
        GET, poll_close
        """
        utils.login(self)
        response = self.client.get(reverse('spirit:comment:poll:close', kwargs={'pk': self.poll.pk, }))
        self.assertEqual(response.status_code, 405)

    def test_poll_close_post(self):
        """
        POST, poll_close
        """
        utils.login(self)
        poll = CommentPoll.objects.create(comment=self.user_comment, name='foo')
        response = self.client.post(reverse('spirit:comment:poll:close', kwargs={'pk': poll.pk, }),
                                    {})
        expected_url = poll.get_absolute_url()
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=302)
        self.assertTrue(CommentPoll.objects.get(pk=poll.pk).is_closed)

    def test_poll_close_open_post(self):
        """
        POST, poll_open
        """
        utils.login(self)
        poll = CommentPoll.objects.create(comment=self.user_comment, name='foo', close_at=timezone.now())
        self.assertTrue(poll.is_closed)
        response = self.client.post(reverse('spirit:comment:poll:open', kwargs={'pk': poll.pk, }),
                                    {})
        expected_url = poll.get_absolute_url()
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=302)
        self.assertFalse(CommentPoll.objects.get(pk=poll.pk).is_closed)

    def test_poll_vote_logged_in(self):
        """
        User must be logged in
        """
        response = self.client.post(reverse('spirit:comment:poll:vote', kwargs={'pk': self.poll.pk, }),
                                    {})
        expected_url = reverse('spirit:user:auth:login') + "?next=" + self.poll.get_absolute_url()
        self.assertRedirects(response, expected_url, status_code=302)

    def test_poll_vote_get(self):
        """
        GET, poll_vote
        Post is required
        """
        utils.login(self)
        response = self.client.get(reverse('spirit:comment:poll:vote', kwargs={'pk': self.poll.pk, }))
        self.assertEqual(response.status_code, 405)

    def test_poll_vote_post(self):
        """
        POST, poll_vote
        """
        utils.login(self)
        choice = CommentPollChoice.objects.create(poll=self.poll, number=1, description="op1")
        form_data = {'choices': choice.pk, }
        response = self.client.post(reverse('spirit:comment:poll:vote', kwargs={'pk': self.poll.pk, }),
                                    form_data)
        expected_url = self.poll.get_absolute_url()
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=302)
        self.assertEqual(len(CommentPollVote.objects.filter(choice=choice)), 1)

    def test_poll_vote_post_invalid(self):
        """
        POST, poll_vote
        """
        utils.login(self)
        response = self.client.post(reverse('spirit:comment:poll:vote', kwargs={'pk': self.poll.pk, }),
                                    {}, follow=True)
        self.assertEqual(len(response.context['messages']), 1)  # error message

    def test_poll_vote_post_invalid_redirect(self):
        """
        POST, poll_vote
        """
        utils.login(self)
        response = self.client.post(reverse('spirit:comment:poll:vote', kwargs={'pk': self.poll.pk, }),
                                    {})
        expected_url = self.poll.get_absolute_url()
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=302)


class PollFormTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = utils.create_user()
        self.user2 = utils.create_user()
        self.category = utils.create_category()
        self.topic = utils.create_topic(self.category, user=self.user)
        self.comment = utils.create_comment(topic=self.topic)
        self.comment2 = utils.create_comment(topic=self.topic)

        # Single choice
        self.poll = CommentPoll.objects.create(comment=self.comment, name='foo')

        self.poll_choice = CommentPollChoice.objects.create(poll=self.poll, number=1, description="op1")
        self.poll_choice2 = CommentPollChoice.objects.create(poll=self.poll, number=2, description="op2")

        self.poll_vote = CommentPollVote.objects.create(voter=self.user, choice=self.poll_choice)
        self.poll_vote2 = CommentPollVote.objects.create(voter=self.user2, choice=self.poll_choice)

        # ...poor man prefetch
        self.poll_choice.votes = [self.poll_vote]
        self.poll.choices = [self.poll_choice, self.poll_choice2]

        # Multi choice
        self.poll_multi = CommentPoll.objects.create(comment=self.comment2, name='bar', choice_max=2)

        self.poll_multi_choice = CommentPollChoice.objects.create(poll=self.poll_multi, number=1, description="op1")
        self.poll_multi_choice2 = CommentPollChoice.objects.create(poll=self.poll_multi, number=2, description="op2")
        self.poll_multi_choice3 = CommentPollChoice.objects.create(poll=self.poll_multi, number=3, description="op3")

        self.poll_multi_vote = CommentPollVote.objects.create(voter=self.user, choice=self.poll_multi_choice)
        self.poll_multi_vote2 = CommentPollVote.objects.create(voter=self.user, choice=self.poll_multi_choice2)
        self.poll_multi_vote3 = CommentPollVote.objects.create(voter=self.user2, choice=self.poll_multi_choice)

        # ...poor man prefetch
        self.poll_multi_choice.votes = [self.poll_multi_vote]
        self.poll_multi_choice2.votes = [self.poll_multi_vote2]
        self.poll_multi.choices = [self.poll_multi_choice, self.poll_multi_choice2]

    def test_vote_load_initial_single(self):
        """
        TopicPollVoteManyForm
        """
        form = PollVoteManyForm(user=self.user, poll=self.poll)
        form.load_initial()
        self.assertEqual(form.initial, {'choices': self.poll_choice.pk, })

    def test_vote_load_initial_multi(self):
        """
        TopicPollVoteManyForm
        """
        form = PollVoteManyForm(user=self.user, poll=self.poll_multi)
        form.load_initial()
        self.assertDictEqual(form.initial, {'choices': [self.poll_multi_choice.pk, self.poll_multi_choice2.pk], })

    def test_vote_load_initial_empty(self):
        """
        TopicPollVoteManyForm
        """
        self.poll_choice.votes = []

        form = PollVoteManyForm(user=self.user, poll=self.poll)
        form.load_initial()
        self.assertEqual(form.initial, {})

    def test_vote_load_initial_choice_limit(self):
        """
        Load initial for a single choice poll that was previously a multi choice poll
        """
        # multi to single
        self.poll_multi.choice_max = 1

        form = PollVoteManyForm(user=self.user, poll=self.poll_multi)
        form.load_initial()
        self.assertDictEqual(form.initial, {'choices': self.poll_multi_choice.pk, })

        # single to multi
        self.poll.choice_max = 2

        form = PollVoteManyForm(user=self.user, poll=self.poll)
        form.load_initial()
        self.assertDictEqual(form.initial, {'choices': [self.poll_choice.pk, ], })

    def test_vote_poll_closed(self):
        """
        Cant vote on closed poll
        """
        self.poll.close_at = timezone.now()
        self.poll.save()

        form_data = {'choices': self.poll_choice.pk, }
        form = PollVoteManyForm(user=self.user, poll=self.poll, data=form_data)
        self.assertFalse(form.is_valid())

    def test_create_vote_single(self):
        """
        TopicPollVoteManyForm
        """
        CommentPollVote.objects.all().delete()

        form_data = {'choices': self.poll_choice.pk, }
        form = PollVoteManyForm(user=self.user, poll=self.poll, data=form_data)
        self.assertTrue(form.is_valid())
        form.save_m2m()
        self.assertEqual(len(CommentPollVote.objects.all()), 1)
        self.assertEqual(len(CommentPollVote.objects.filter(choice=self.poll_choice, is_removed=False)), 1)

    def test_create_vote_multi(self):
        """
        TopicPollVoteManyForm
        """
        CommentPollVote.objects.all().delete()
        self.poll_multi_choice.votes = []
        self.poll_multi_choice2.votes = []

        form_data = {'choices': [self.poll_multi_choice.pk, self.poll_multi_choice2.pk], }
        form = PollVoteManyForm(user=self.user, poll=self.poll_multi, data=form_data)
        self.assertTrue(form.is_valid())

    def test_create_vote_multi_invalid(self):
        """
        Limit selected choices to choice_limit
        """
        CommentPollVote.objects.all().delete()
        self.poll_multi_choice.votes = []
        self.poll_multi_choice2.votes = []

        form_data = {'choices': [self.poll_multi_choice.pk,
                                 self.poll_multi_choice2.pk,
                                 self.poll_multi_choice3.pk], }
        form = PollVoteManyForm(user=self.user, poll=self.poll_multi, data=form_data)
        self.assertFalse(form.is_valid())

    def test_update_vote_single(self):
        """
        TopicPollVoteManyForm
        """
        self.assertEqual(len(CommentPollVote.objects.filter(choice=self.poll_choice2, is_removed=False)), 0)
        self.assertEqual(len(CommentPollVote.objects.filter(choice=self.poll_choice, is_removed=False)), 2)

        form_data = {'choices': self.poll_choice2.pk, }
        form = PollVoteManyForm(user=self.user, poll=self.poll, data=form_data)
        self.assertTrue(form.is_valid())
        form.save_m2m()
        self.assertEqual(len(CommentPollVote.objects.filter(choice=self.poll_choice2, is_removed=False)), 1)
        self.assertEqual(len(CommentPollVote.objects.filter(choice=self.poll_choice, is_removed=False)), 1)
