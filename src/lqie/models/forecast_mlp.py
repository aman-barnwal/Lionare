import torch
from torch import nn


class MultiHorizonMLP(nn.Module):
    """Numerical financial forecasting network."""

    def __init__(
        self,
        input_dim: int = 32,
        horizons: tuple[int, ...] = (1, 5, 20),
        hidden_dims: tuple[int, ...] = (128, 64),
        dropout: float = 0.10,
    ):
        super().__init__()

        if input_dim <= 0:
            raise ValueError("input_dim must be positive")
        if not horizons or any(h <= 0 for h in horizons):
            raise ValueError("horizons must contain positive integers")
        if not hidden_dims or any(w <= 0 for w in hidden_dims):
            raise ValueError("hidden_dims must contain positive integers")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in [0, 1)")

        self.input_dim = input_dim
        self.horizons = horizons

        layers = []
        previous_dim = input_dim

        for width in hidden_dims:
            layers.extend([
                nn.Linear(previous_dim, width),
                nn.LayerNorm(width),
                nn.GELU(),
                nn.Dropout(dropout),
            ])
            previous_dim = width

        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(previous_dim, len(horizons))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if features.ndim != 2:
            raise ValueError("Expected [batch_size, input_dim]")

        if features.shape[1] != self.input_dim:
            raise ValueError(
                f"Expected {self.input_dim} features, "
                f"received {features.shape[1]}"
            )

        return self.head(self.backbone(features))
