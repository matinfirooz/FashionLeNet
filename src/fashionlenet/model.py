"""ReLU/max-pool LeNet variant specified in docs/REQUIREMENTS.md."""
import torch
from torch import nn


class LeNet(nn.Module):
    def __init__(self, input_size=32, channels=(6, 16, 120, 84)):
        super().__init__()
        if input_size not in (28, 32) or len(channels) != 4 or min(channels) < 1:
            raise ValueError("Expected input 28/32 and four positive widths")
        c1, c2, c3, f1 = channels
        self.input_size = input_size
        self.channels = tuple(channels)
        self.conv1 = nn.Conv2d(1, c1, 5)
        self.conv2 = nn.Conv2d(c1, c2, 5)
        self.conv3 = nn.Conv2d(c2, c3, 5 if input_size == 32 else 4)
        self.fc1 = nn.Linear(c3, f1)
        self.fc2 = nn.Linear(f1, 10)

    def intermediates(self, x):
        a = torch.relu(self.conv1(x))
        p1 = torch.nn.functional.max_pool2d(a, 2)
        b = torch.relu(self.conv2(p1))
        p2 = torch.nn.functional.max_pool2d(b, 2)
        c = torch.relu(self.conv3(p2)).flatten(1)
        d = torch.relu(self.fc1(c))
        z = self.fc2(d)
        return [a, b, c, d, z]

    def forward(self, x):
        return self.intermediates(x)[-1]

    def weighted_layers(self):
        return [self.conv1, self.conv2, self.conv3, self.fc1, self.fc2]


def save_checkpoint(model, path, **metadata):
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "input_size": model.input_size,
                "channels": model.channels, "metadata": metadata}, path)


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = LeNet(checkpoint["input_size"], checkpoint["channels"])
    model.load_state_dict(checkpoint["state_dict"])
    return model.eval(), checkpoint.get("metadata", {})
