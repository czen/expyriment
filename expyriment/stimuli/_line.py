#!/usr/bin/env python

"""
A Line stimulus.

This module contains a class implementing a line stimulus.

"""
from __future__ import absolute_import, print_function, division
from builtins import *


__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''


import math
from copy import copy
import pygame

from . import defaults
from ._visual import Visual
from ._shape import Shape
from .. import _internals
from ..misc.geometry import XYPoint, vertices_rectangle, lines_intersect, points2vertices
from ..misc._timer import get_time


class Line(Visual):
    """A class implementing a line stimulus."""

    def __init__(self, start_point, end_point, line_width, colour=None,
                 anti_aliasing=None):
        """Create a line between two points.

        Parameters
        ----------
        start_point : (int, int)
            start point of the line (x,y)
        end_point : (int, int)
            end point of the line (x,y)
        line_width : int
            width of the plotted line
        colour : (int, int, int), optional
            line colour (int, int, int)
        anti_aliasing : int, optional
            anti aliasing parameter (good anti_aliasing with 10)

        """

        self._start_point = list(start_point)
        self._end_point = list(end_point)
        self._line_width = line_width
        Visual.__init__(self, position=[0,0]),
        if colour is None:
            colour = defaults.line_colour
            if colour is None:
                colour = _internals.active_exp.foreground_colour
        self._colour = colour
        if anti_aliasing is not None:
            self._anti_aliasing = anti_aliasing
        else:
            self._anti_aliasing = defaults.line_anti_aliasing

    _getter_exception_message = "Cannot set {0} if surface exists!"

    @property
    def start_point(self):
        """Getter for start_point."""
        return self._start_point

    @property
    def end_point(self):
        """Getter for end_point."""
        return self._end_point

    @property
    def line_width(self):
        """Getter for line_width."""
        return self._line_width

    @line_width.setter
    def line_width(self, value):
        """Setter for line_width."""

        if self.has_surface:
            raise AttributeError(Line._getter_exception_message.format(
                "line_width"))
        else:
            self._line_width = value

    @property
    def colour(self):
        """Getter for colour."""
        return self._colour

    @colour.setter
    def colour(self, value):
        """Setter for colour."""

        if self.has_surface:
            raise AttributeError(Line._getter_exception_message.format(
                "colour"))
        else:
            self._colour = value

    @property
    def anti_aliasing(self):
        """Getter for anti_aliasing."""

        return self._anti_aliasing

    @anti_aliasing.setter
    def anti_aliasing(self, value):
        """Setter for anti_aliasing."""

        if self.has_surface:
            raise AttributeError(Line._getter_exception_message.format(
                "anti_aliasing"))
        self._anti_aliasing = value

    @property
    def position(self):
        """Getter for position."""
        return (int(self.start_point[0] + (self.end_point[0] - self.start_point[0]) / 2.0),
                int(self.start_point[1] + (self.end_point[1] - self.start_point[1]) / 2.0))

    @position.setter
    def position(self, value):
        """Setter for position."""

        self.move(offset = (value[0] - self.position[0],
                            value[1] - self.position[1]))

    def move(self, offset):
        """Moves the stimulus in 2D space.

        Parameters
        ----------
        offset : list, optional
            translation along x and y axis

        Returns
        -------
        time : int
            the time it took to execute this method

        Notes
        -----
        When using OpenGL, this can take longer then 1ms!

        """

        start = get_time()
        self._start_point = (self._start_point[0] + offset[0],
                             self._start_point[1] + offset[1])
        self._end_point = (self._end_point[0] + offset[0],
                          self._end_point[1] + offset[1])
        if self._ogl_screen is not None and (offset[0]!=0 or offset[1]!=0):
                self._ogl_screen.refresh_position()
        return int((get_time() - start) * 1000)

    def get_shape(self):
        """returns the shape representation of the line

        Returns
        -------
        shape : stimuli.Shape
            Shape representation of the line

        """

        dist = XYPoint(self._start_point).distance(XYPoint(self._end_point))
        shape = Shape(vertex_list=vertices_rectangle(size=(dist, self.line_width)),
                      colour=self.colour, position=self.position, line_width=0,
                      anti_aliasing= self.anti_aliasing,
                      contour_colour = self.colour)
        diff = (self._end_point[0] - self._start_point[0],
                self._end_point[1] - self._start_point[1])
        shape.native_rotate(degree = math.atan2(diff[1], diff[0]) * -180 / math.pi)

        return shape

    def get_connecting_shape(self, other_line, sharp_corner=False):
        """returns a modified line shape that connects without gap with
        another line, if the two lines do indeed touch each other. Otherwise,
        a runtime error is raised.

        Parameter
        ---------
        other_line : stimuli.Line
            the other line to join with
        sharp_corner : boolean (optional)
            if True, corner will be sharp and not cropped

        Returns
        -------
        shape : stimuli.Shape
            Shape representation of the modified line

        Example
        -------
        ```
            line_1 = stimuli.Line((100,100), (140, 190), line_width=20, colour=constants.C_BLUE)
            line_2 = stimuli.Line((140, 190), (260, 230), line_width=20, colour=constants.C_BLUE)
            line1_mod = line_1.get_connecting_shape(line_2)

            #plot
            bl = stimuli.BlankScreen()
            line1_mod.plot(bl)
            line_2.plot(bl)
            bl.present()
        ```

        """

        self_shape = self.get_shape()
        other_shape = other_line.get_shape()

        for a_end, b_start in ((True, True), (True, False), (False, False), (False, True)):
            rtn = Line.__join_end(self_shape, other_shape, a_end=a_end, b_start=b_start, sharp_corner=sharp_corner)
            if rtn is not None:
                return rtn

        raise RuntimeWarning("The two lines do not connected and can't be joined.")


    @staticmethod
    def __join_end(line_shape_a, line_shape_b, a_end=True, b_start=True, sharp_corner=False):
        """helper function: returns the modified line_shape_a"""

        a_points = line_shape_a.xy_points_on_screen
        if a_end:
            a_edge = (1, 2)
        else:
            a_edge = (3, 0)

        b_points = line_shape_b.xy_points_on_screen
        if b_start:
            b_edge = (3, 0)
        else:
            b_edge = (1, 2)

        if lines_intersect(a_points[a_edge[0]], a_points[a_edge[1]],
                           b_points[b_edge[0]], b_points[b_edge[1]]):
            #two start line edges intersect
            if line_shape_a.overlapping_with_position(b_points[b_edge[0]].tuple):
                b_join_point = b_edge[1]
            else:
                b_join_point = b_edge[0]

            a_modified = copy(a_points)
            if a_end:
                # 0, 1, contact point, 2, 3
                insert_pos = 2
            else:
                # 0, 1, 2, 3, contact point
                insert_pos = 4
            a_modified.insert(insert_pos, b_points[b_join_point]) # insert contact point

            if sharp_corner:
                # calc sharp corner point before contact point
                _edge(a_modified[insert_pos-1])
                _edge(a_modified[insert_pos])
                sharp_corner_point = None
                a_modified.insert(insert_pos, sharp_corner_point)

            rtn = Shape(colour=line_shape_a.colour,
                        line_width=line_shape_a.line_width,
                        anti_aliasing=line_shape_a.anti_aliasing,
                        vertex_list=points2vertices(a_modified),
                        contour_colour = line_shape_a.contour_colour)
            rtn.move((b_points[b_join_point].x - rtn.xy_points_on_screen[insert_pos].x,
                     b_points[b_join_point].y - rtn.xy_points_on_screen[insert_pos].y))
            return rtn
        else:
            return None




        pass

    def _create_surface(self):
        """Create the surface of the stimulus."""

        return self.get_shape()._create_surface()

def _edge(id):
    """helper function"""
    if id == 0:
        return (1, 0)
    elif id == 1:
        return (0, 1)
    elif id == 3:
        return (2, 3)
    elif id == 2:
        return (3, 2)

if __name__ == "__main__":
    from .. import control
    control.set_develop_mode(True)
    control.defaults.event_logging = 0
    exp = control.initialize()
    p1 = (-180, 15)
    p2 = (200, 0)
    line = Line(p1, p2, 2)
    line.present()
    exp.clock.wait(1000)
