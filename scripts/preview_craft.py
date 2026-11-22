"""Build sandboxed synthetic template sheets without models or simulator calls.

Usage: .venv/bin/python -B scripts/preview_craft.py --output /tmp/stopreplay-visual-review
Open index.html locally in a browser. Forms and scripts are disabled in previews.
"""
import argparse
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.craft.email_templates import build_html_email
from src.craft.landing_pages import build_landing_page
from src.craft.story import build_story
from src.models.schemas import TargetProfile, Hook, Persona
from src.orchestrator.strategy_planner import LANES_CATALOG, StrategySelector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = TargetProfile('synthetic', 'Synthetic Lead', organization='Synthetic Company')
    items = []
    for lane in LANES_CATALOG:
        hook = StrategySelector().build_hook(lane, profile)
        story = build_story(lane, profile)
        items.append((lane + ' EMAIL', build_html_email(lane, hook, profile, story)))
        if hook.landing_page_url:
            items.append((lane + ' PAGE', build_landing_page(lane, story)))
    nda = Hook('nda', 'synthetic', 'NDA', Persona('Sarah Weber', 'Procurement',
               'DAX Sourcing Group', 'Fixture'), 'NDA', 'action', 'email')
    items.append(('NDA FOLLOWUP', build_html_email('NDA_FOLLOWUP', nda, profile,
                                                 build_story('NDA_FOLLOWUP', profile))))
    groups = (len(items) + 2) // 3
    links = []
    for width, height, scale, kind in [(640, 1100, .6, 'desktop'), (360, 1500, .5, 'mobile')]:
        for group in range(groups):
            title = f'{kind} review — group {group + 1}/{groups} — {width}px viewport'
            css = f'''body{{margin:0;padding:12px;background:#e8edf2;font:12px system-ui}}
                main{{display:flex;gap:14px}} section{{width:{width * scale}px;flex-shrink:0}}
                h1{{font-size:16px}} h2{{font-size:11px;min-height:45px;overflow-wrap:anywhere}}
                .frame{{height:{height * scale}px;overflow:hidden}}
                iframe{{border:0;transform:scale({scale});transform-origin:top left;
                        width:{width}px;height:{height}px}}'''
            page = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head><body>'
            page += f'<h1>{title}</h1><p>Synthetic offline fixtures. Forms and scripts disabled.</p><main>'
            for label, html in items[group * 3:group * 3 + 3]:
                page += (f'<section><h2>{escape(label)}</h2><div class="frame">'
                         f'<iframe title="{escape(label)}" sandbox srcdoc="{escape(html, quote=True)}"></iframe>'
                         '</div></section>')
            page += '</main></body></html>'
            filename = f'{kind}-{group}.html'
            (args.output / filename).write_text(page)
            links.append(f'<li><a href="{filename}">{title}</a></li>')
    (args.output / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>STOPReplay template review</title><body style="font:16px system-ui;padding:32px">'
        '<h1>STOPReplay template review</h1><p>22 synthetic templates at 640px and 360px. '
        'Browser rendering checks; not live-model outputs or organizer-renderer verification.</p><ul>'
        + ''.join(links) + '</ul></body></html>')
    print(f'Wrote {len(items)} templates at two viewport widths to {args.output / "index.html"}')


if __name__ == '__main__':
    main()
