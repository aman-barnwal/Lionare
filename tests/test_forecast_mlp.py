import pytest
import torch

from lqie.models import MultiHorizonMLP


def test_output_shape():
    model = MultiHorizonMLP(input_dim=32)
    x = torch.randn(64, 32)

    assert model(x).shape == (64, 3)


def test_gradient_and_training_step():
    model = MultiHorizonMLP(input_dim=32)
    optimizer = torch.optim.Adam(model.parameters())

    x = torch.randn(64, 32)
    target = torch.randn(64, 3)

    optimizer.zero_grad()
    prediction = model(x)
    loss = torch.nn.functional.mse_loss(prediction, target)
    loss.backward()

    assert torch.isfinite(loss)
    assert model.head.weight.grad is not None

    optimizer.step()


def test_invalid_input_dimensions():
    model = MultiHorizonMLP(input_dim=32)

    with pytest.raises(ValueError):
        model(torch.randn(64, 16))


def test_custom_horizons():
    model = MultiHorizonMLP(
        input_dim=16,
        horizons=(1, 5, 10, 20),
        hidden_dims=(64, 32),
    )

    assert model(torch.randn(8, 16)).shape == (8, 4)


def test_no_nan_output():
    model = MultiHorizonMLP()
    output = model(torch.randn(32, 32))

    assert torch.isfinite(output).all()
