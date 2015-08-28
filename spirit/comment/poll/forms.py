# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text

from .models import CommentPollChoice, CommentPollVote


class PollVoteManyForm(forms.Form):
    """
    This special form allows single vote and multi vote as well.
    Its beauty is that it doesn't care if the choice_limit
    is increased or decreased later.
    """

    def __init__(self, poll, user=None, *args, **kwargs):
        super(PollVoteManyForm, self).__init__(*args, **kwargs)
        self.user = user
        self.poll = poll
        choices = ((c.pk, c.description) for c in poll.choices)

        if poll.is_multiple_choice:
            self.fields['choices'] = forms.MultipleChoiceField(
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                label=_("Poll choices")
            )
        else:
            self.fields['choices'] = forms.ChoiceField(
                choices=choices,
                widget=forms.RadioSelect,
                label=_("Poll choices")
            )

        self.fields['choices'].label_from_instance = lambda obj: smart_text(obj.description)

    def load_initial(self, votes):
        votes = list(votes)

        if not votes:
            return

        if not self.poll.is_multiple_choice:
            votes = votes[0]

        self.initial = {'choices': votes, }

    def clean_choices(self):
        choices = self.cleaned_data['choices']

        if len(choices) > self.poll.choice_limit:
            raise forms.ValidationError(
                _("Too many selected choices. Limit is %s")
                % self.poll.choice_limit
            )

        return choices

    def clean(self):
        cleaned_data = super(PollVoteManyForm, self).clean()

        if self.poll.is_closed:
            raise forms.ValidationError(_("This poll is closed"))

        return cleaned_data

    def save_m2m(self):
        choices = self.cleaned_data['choices']

        if not self.poll.is_multiple_choice:
            choices = [choices, ]

        CommentPollVote.objects\
            .filter(voter=self.user, choice__poll=self.poll)\
            .update(is_removed=True)

        for choice in choices:
            CommentPollVote.objects.update_or_create(
                voter=self.user,
                choice_id=choice,
                defaults={'is_removed': False}
            )
