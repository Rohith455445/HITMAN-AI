from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
    def handle_starttag(self,tag, attrs):
        d=dict(attrs)
        if 'id' in d: self.ids.append(d['id'])


def test_chat_interface_all_existing_handlers_have_targets():
    p=IdParser(); p.feed((ROOT/'static/index.html').read_text('utf-8'))
    expected={'sidebar','newChat','threads','menuBtn','chat','welcome','messages','projectResult',
              'chatForm','prompt','send','modeSelect','fileInput','fileName','voiceBtn','debugBtn',
              'modelBtn','buildBtn','repairBtn','imageBtn','liveBtn','memoryBtn','exportBtn','logoutChat'}
    assert expected.issubset(p.ids)
    assert len(p.ids)==len(set(p.ids)), 'Duplicate HTML IDs cause handlers to target the wrong element.'


def test_ui_feature_controls_and_safe_rendering():
    p=IdParser();p.feed((ROOT/'static/index.html').read_text('utf-8'))
    assert {'toolsMenu','chatSearch','themeBtn','attachmentPreview','clearFile','navImages',
            'navResearch','navMemory','sidebarBackdrop'}.issubset(p.ids)
    script=(ROOT/'static/app.js').read_text('utf-8')
    assert 'renderAssistantMarkdown' in script
    assert 'element.textContent=code' in script
    assert 'innerHTML' not in script
