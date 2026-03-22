import numpy as np
import sys
from unittest.mock import MagicMock

# Quick monkeypatch for numpy >= 2.0 deprecations
if not hasattr(np, 'float_'):
    np.float_ = np.float64
if not hasattr(np, 'object_'):
    np.object_ = object

# Mock chromadb to avoid onnxruntime / numpy 2.0 C-extension conflicts during testing
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()
