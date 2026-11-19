"""Offline test shim only: production installs the real openai package."""
import sys
import types
if 'openai' not in sys.modules:
    try: import openai
    except ImportError:
        mod=types.ModuleType('openai')
        class OpenAI:
            def __init__(self,*args,**kwargs): pass
        mod.OpenAI=OpenAI
        sys.modules['openai']=mod

import pytest

@pytest.fixture(autouse=True)
def restore_workspace_singleton():
    """Each offline test may swap the global SQLite workspace connection."""
    import workspace
    fields=('_db_file','_archive_reader','_static_checker','_sandbox_runner',
            '_model_provider','_advanced_model','_reasoning_config')
    old={k:getattr(workspace,k) for k in fields}
    yield
    for k,v in old.items(): setattr(workspace,k,v)
