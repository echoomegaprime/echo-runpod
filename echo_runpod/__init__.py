"""Echo RunPod — governed RunPod control plane for Echo Nexus."""

from echo_runpod.oauth import PACKAGE_VERSION

__version__ = PACKAGE_VERSION
__upstream__ = {
    "runpod_plugins_official_commit": "b669407688056642d09d2049df5432cb78ae33f0",
    "runpod_plugins_official_version": "1.1.2",
    "runpod_mcp_commit": "51d6fd9a0ff16a4eeb7d508972aeb5502f514939",
}

from echo_runpod.router import route_prompt
from echo_runpod.policy import evaluate_action, PolicyDecision

__all__ = [
    "__version__",
    "__upstream__",
    "route_prompt",
    "evaluate_action",
    "PolicyDecision",
]
