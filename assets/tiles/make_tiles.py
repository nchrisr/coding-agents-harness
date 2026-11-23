"""Builds README tiles: a light card with a logo and a label. Usage: python3 -I make_tiles.py <simple-icons dir> <out dir>"""
import re, sys, os
si, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
tiles = [  # file, label, simple-icons slug or None, brand colour
    ('typescript', 'TypeScript', 'typescript', '3178C6'),
    ('javascript', 'JavaScript', 'javascript', 'F7DF1E'),
    ('python', 'Python', 'python', '3776AB'),
    ('rust', 'Rust', 'rust', '000000'),
    ('github', 'GitHub', 'github', '181717'),
    ('gitlab', 'GitLab', 'gitlab', 'FC6D26'),
    ('azure-repos', 'Azure Repos', None, '0078D4'),
    ('claude-code', 'Claude Code', 'claude', 'D97757'),
    ('codex', 'Codex', 'openai', '000000'),
    ('gemini-cli', 'Gemini CLI', 'googlegemini', '8E75B2'),
]
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
for name, label, slug, colour in tiles:
    if slug:
        path = re.search(r' d="([^"]+)"', open(f'{si}/icons/{slug}.svg').read()).group(1)
        icon = f'<g transform="translate(48 30) scale(2.6667)"><path fill="#{colour}" d="{path}"/></g>'
    else:  # no logo in the set: a plain coloured square with initials
        icon = (f'<rect x="48" y="30" width="64" height="64" rx="10" fill="#{colour}"/>'
                f'<text x="80" y="72" text-anchor="middle" font-family="{FONT}" font-size="26" '
                f'font-weight="700" fill="#ffffff">Az</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160" '
           f'role="img" aria-label="{label}">'
           f'<rect x="1" y="1" width="158" height="158" rx="14" fill="#F6F5F1" stroke="#D8D6D0" stroke-width="2"/>'
           f'{icon}'
           f'<text x="80" y="128" text-anchor="middle" font-family="{FONT}" font-size="17" '
           f'font-weight="600" fill="#24292F">{label}</text></svg>\n')
    open(os.path.join(out, name + '.svg'), 'w').write(svg)
    print('wrote', name)
