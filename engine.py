from .core_runtime import *
from .automotive import AutomotiveMixin
from .tc_engine import TcEngineMixin
from .ai_engine import AiEngineMixin
from .storage import StorageMixin
from .ui_main import UiMainMixin
from .ui_components import UiComponentsMixin


class ValidationAssistant(AutomotiveMixin, TcEngineMixin, AiEngineMixin, StorageMixin, UiMainMixin, UiComponentsMixin, QWidget):
    pass
