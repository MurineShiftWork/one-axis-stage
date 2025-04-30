import logging
from functools import partial

from one_axis_stage.controller import StageController


class MoveInterface:
    """"""

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
        axis = self.controller.axes.get(axis_name)
        if axis:
            increment_speed = self.small_increment if not fast_mode else self.large_increment
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
