"""Convenience interface for incremental axis moves."""

import logging
from functools import partial

from one_axis_stage.controller import StageController


class MoveInterface:
    """Attaches per-axis increment helpers to a StageController.

    For each axis registered on the controller, four bound methods are
    created dynamically at construction time:

    - ``<axis>p``  - move forward by small_increment
    - ``<axis>m``  - move backward by small_increment
    - ``<axis>pp`` - move forward by large_increment
    - ``<axis>mm`` - move backward by large_increment

    Example:
        With axes ``x`` and ``y`` registered, the following are available::

            move.xp()   # small step forward on x
            move.ymm()  # large step backward on y
    """

    controller: StageController
    small_increment: int
    large_increment: int

    def __init__(
        self,
        controller: StageController,
        small_increment: int = 20,
        large_increment: int = 40,
    ):
        super().__init__()
        self.controller = controller
        self.small_increment = small_increment
        self.large_increment = large_increment

        for axis_name in self.controller.axes:
            logging.info(f"Creating move methods for axis '{axis_name}'")
            # slow
            setattr(
                self,
                f"{axis_name}p",
                partial(
                    self.move_axis_by_increment,
                    axis_name=axis_name,
                    direction_forward=True,
                    fast_mode=False,
                ),
            )
            setattr(
                self,
                f"{axis_name}m",
                partial(
                    self.move_axis_by_increment,
                    axis_name=axis_name,
                    direction_forward=False,
                    fast_mode=False,
                ),
            )
            # fast
            setattr(
                self,
                f"{axis_name}pp",
                partial(
                    self.move_axis_by_increment,
                    axis_name=axis_name,
                    direction_forward=True,
                    fast_mode=True,
                ),
            )
            setattr(
                self,
                f"{axis_name}mm",
                partial(
                    self.move_axis_by_increment,
                    axis_name=axis_name,
                    direction_forward=False,
                    fast_mode=True,
                ),
            )

    def move_axis_by_increment(
        self,
        axis_name: str,
        direction_forward: bool = True,
        fast_mode: bool = False,
    ):
        """Move a named axis by one increment step.

        Uses small_increment when fast_mode is False, large_increment otherwise.
        Out-of-bounds moves are silently swallowed and logged as errors.

        Args:
            axis_name: Name of the axis to move.
            direction_forward: True to increase position, False to decrease.
            fast_mode: If True, use large_increment instead of small_increment.

        Raises:
            ValueError: If axis_name is not registered on the controller.
        """
        axis = self.controller.axes.get(axis_name)
        if axis:
            increment_speed = (
                self.small_increment if not fast_mode else self.large_increment
            )
            increment = increment_speed if direction_forward else -increment_speed
            new_position = axis.position_raw + increment
            logging.info(
                f"Moving axis '{axis.name}' {axis.position_raw}->{new_position} ({increment})"
            )

            # try to move, but ignore errors, only report
            try:
                axis.set_position(new_position)
            except AssertionError as e:
                logging.error(e)

        else:
            raise ValueError(f"Axis '{axis_name}' not found in controller")
