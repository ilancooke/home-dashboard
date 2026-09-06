"""Whole-home audio integration for the Monoprice multizone amplifier."""

from .controller import MonopriceController
from .routes import create_audio_blueprint

__all__ = ["MonopriceController", "create_audio_blueprint"]
