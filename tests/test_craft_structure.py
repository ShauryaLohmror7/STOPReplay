"""Structural checks on existing templates; these are not visual-quality scores."""
from html.parser import HTMLParser
import pytest
from src.craft.email_templates import build_html_email
from src.craft.landing_pages import build_landing_page, get_fields_for_lane
from src.craft.story import build_story
from src.models.schemas import TargetProfile
from src.orchestrator.strategy_planner import LANES_CATALOG, StrategySelector


class Structure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields, self.labels, self.tags = [], [], []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == 'input':
            self.fields.append(attrs['name'])
        if tag == 'label':
            self.labels.append(attrs.get('for'))


@pytest.mark.parametrize('lane', list(LANES_CATALOG))
def test_templates_build_and_registered_fields_match_markup(lane):
    profile = TargetProfile('synthetic', 'Synthetic Lead', organization='Synthetic Company')
    hook = StrategySelector().build_hook(lane, profile)
    story = build_story(lane, profile)
    mail = build_html_email(lane, hook, profile, story)
    parsed = Structure(mail)
    assert parsed.tags.count('html') == parsed.tags.count('body') == 1
    assert 'script' not in parsed.tags
    assert 'Synthetic Lead' in mail
    if hook.landing_page_url:
        page = Structure(build_landing_page(lane, story))
        assert page.tags.count('form') == 1
        assert set(page.fields) == set(get_fields_for_lane(lane)) == set(page.labels)
        assert len(page.fields) == len(set(page.fields))


def test_unregistered_pages_fail_instead_of_using_unrelated_portal():
    with pytest.raises(ValueError, match='No registered'):
        build_landing_page('unknown')
