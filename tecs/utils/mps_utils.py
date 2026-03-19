"""Apple Silicon MPS acceleration utilities."""
import numpy as np

_TORCH_AVAILABLE = False
_MPS_AVAILABLE = False

try:
    import torch
    _TORCH_AVAILABLE = True
    _MPS_AVAILABLE = torch.backends.mps.is_available()
except ImportError:
    pass

def get_device():
    """Get the best available device."""
    if _MPS_AVAILABLE:
        return torch.device("mps")
    if _TORCH_AVAILABLE:
        return torch.device("cpu")
    return None

def to_tensor(arr: np.ndarray) -> "torch.Tensor | None":
    """Convert numpy array to torch tensor on best device. Returns None if torch unavailable."""
    if not _TORCH_AVAILABLE:
        return None
    device = get_device()
    return torch.tensor(arr, dtype=torch.float32, device=device)

def to_numpy(tensor) -> np.ndarray:
    """Convert torch tensor back to numpy."""
    return tensor.detach().cpu().numpy()

def is_gpu_available() -> bool:
    return _MPS_AVAILABLE
