#! /usr/bin/env python

# This node interprets messages from the joy topic
# and applies the potential field approach to create
# a safe navigation vector from the joystick command
# and the surrounding obstacles

import roslib, sys, rospy
from sensor_msgs.msg import LaserScan, Joy
from geometry_msgs.msg import Point, Twist
import numpy as np

#-------------------------------------------------

class safe_teleop:
    def __init__(self):
        rospy.init_node("safe_teleop")

        joy_topic = rospy.get_param("~joy_topic", "joy")
        potential_field_topic = rospy.get_param("~potential_field_topic", "potential_field_sum")
        cmd_vel_topic = rospy.get_param("~cmd_vel_topic", "husky/cmd_vel")

        self.joy_sub = rospy.Subscriber(joy_topic, Joy, self.handle_joy)
        self.field_sub = rospy.Subscriber(potential_field_topic, Point, self.handle_potential_field)

        self.cmd_pub = rospy.Publisher(cmd_vel_topic, Twist)

        self.obstacle_vector = None
        self.joy_vector = None

        self.magnitude = rospy.get_param("~joy_vector_magnitude", 10)
        self.drive_scale = rospy.get_param("~drive_scale", 1)
        self.turn_scale = rospy.get_param("~turn_scale", 1)

        self.joy_data = None

        # TODO: figure out which buttons correspond to the bumpers
        self.override_buttons = [0, 6, 7]
        self.deadman_button = 0

        self.safe_motion = False
        self.override = False

#-------------------------------------------------

    def start(self):
        rate = rospy.Rate(rospy.get_param("~cmd_rate", 20))
        while not rospy.is_shutdown():
            cmd = self.compute_motion_cmd()
            if cmd != None:
                self.cmd_pub.publish(cmd)
            rate.sleep()

#-------------------------------------------------

    # take the joystick vector and obstacle vector,
    # and sum them together to get a desired motion vector,
    # then create a motion command that corresponds to this
    def compute_motion_cmd(self):
        cmd = None

        if self.override:
            cmd = Twist()
            cmd.linear.x = data.axes[1] * self.drive_scale
            cmd.angular.z = data.axes[0] * self.turn_scale

        elif self.safe_motion:
            if self.joy_vector == None or self.obstacle_vector == None:
                cmd = None
            
            else:
                vector_sum = self.joy_vector + self.obstacle_vector
                vector_sum /= np.linalg.norm(vector_sum)

                # multiply by the norm of the joystick command,
                # so we only move a little when the axes are only
                # slightly pressed

                joy_cmd_vector = np.array([self.joy_data.axes[1], self.joy_data.axes[0]])
                vector_sum *= np.linalg.norm(joy_cmd_vector)

                # we can't see backward, so don't allow backward motion
                vector_sum[0] = max(0, vector_sum[0])

                # convert the resultant vector into a
                # linear and angular velocity for moving the robot

                cmd = Twist()
                cmd.linear.x = vector_sum[0] * self.drive_scale
                cmd.angular.z = vector_sum[1] * self.turn_scale
        return cmd

#-------------------------------------------------

    def handle_joy(self, joy_data):
        self.joy_data = joy_data

        self.override = True
        for button in self.override_buttons:
            if joy_data.buttons[button] == 0:
                self.override = False

        self.safe_motion = (not self.override) and joy_data.buttons[self.deadman_button] != 0

        x = joy_data.axes[1]
        y = joy_data.axes[0]
        joy_vector = np.array([x, y])
        joy_vector /= np.linalg.norm(joy_vector)
        joy_vector *= self.magnitude

        self.joy_vector = joy_vector

#-------------------------------------------------

    def handle_potential_field(self, potential_field):
        self.obstacle_vector = np.array([potential_field.x, potential_field.y])

#-------------------------------------------------

if __name__ == "__main__":
    st = safe_teleop()
    st.start()