import sys
sys.path.append("")

from dataclasses import dataclass
import pybullet as p
import time
import numpy as np
import amazing_utils as utils
import argparse
import assets as assets

dt = 0.01

@dataclass
class Point:
    x: float
    y: float

@dataclass
class World:
    """A dataclass to hold the world objects"""
    plate: int
    sphere: int

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setpoint", type=float, nargs=2, default=(0.0,0.0))
    parser.add_argument("--kp", type=float, default=0.5)
    parser.add_argument("--kd", type=float, default=2)
    parser.add_argument("--ki", type=float, default=0.007)
    parser.add_argument("--noise", action="store_true", help="Add noise to the measurements")
    parser.add_argument("--filtered", action="store_true", help="filter the measurements")
    # parser.add_argument("--endless-demo", type=bool, default=False, help="If you want to demo endlessly, set to True")
    cmd_args = parser.parse_args()
    print(cmd_args)
    cmd_args.setpoint = Point(*cmd_args.setpoint)
    return cmd_args

global x_position
global y_position
init_position = Point(np.random.uniform(-0.2, 0.2),np.random.uniform(-0.2, 0.2))
x_position = init_position.x
y_position = init_position.y

class PID:
    def __init__(self, kp, ki, kd):
        self.prev_error = 0.0
        self.integral = 0.0
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def pid(self, error):
        self.integral += error * dt
        error_diff = (error - self.prev_error) / dt
        self.prev_error = error
        output = error * self.kp - self.integral * self.ki + error_diff * self.kd
        return np.clip(output, -0.1, 0.1)

def run_controller(kp, kd, ki, setpoint, noise, filtered, world: World, endless_demo=False):
    pid_x = PID(kp=kp, ki=ki, kd=kd)
    pid_y = PID(kp=kp, ki=ki, kd=kd)
    x_filter = utils.Butterworth_filter(butterworth_order=5, cutoff_freq=20)
    y_filter = utils.Butterworth_filter(butterworth_order=5, cutoff_freq=20)
    def set_plate_angles(theta_x, theta_y):
    
        p.setJointMotorControl2(world.plate, 1, p.POSITION_CONTROL, targetPosition=np.clip(theta_x, -0.1, 0.1), force=5, maxVelocity=2)
        p.setJointMotorControl2(world.plate, 0, p.POSITION_CONTROL, targetPosition=np.clip(-theta_y, -0.1, 0.1), force=5, maxVelocity=2)

    def produce_forces(x,y):
        return (pid_x.pid(setpoint.x - x),  pid_y.pid(setpoint.y - y))

    def pid_loop(i: int, t: float):
        '''This function is called every ms and performs the following:
        1. Get the measurement of the position of the ball
        2. Calculate the forces to be applied to the plate
        3. Apply the forces to the plate
        '''
        global x_position 
        global y_position
        (x,y,z), orientation = p.getBasePositionAndOrientation(world.sphere)
        x_position = x
        y_position = y
        oob = False
        if noise:
            x += utils.noise(t)
            y += utils.noise(t, seed = 43) # so that the noise on y is different than the one on x
        
        if filtered:
            x = x_filter.step(x)
            y = y_filter.step(y)
        (angle_x, angle_y) = produce_forces(x, y)
        set_plate_angles(angle_x, angle_y)

        if i%10 == 0:
            print(f"t: {t:.2f}, x: {x:.3f},\ty: {y:.3f},\tax: {angle_x:.3f},\tay: {angle_y:.3f}")

        if x < -0.5 or x > 0.5 or y < -0.7 or y > 0.7:
            oob = True

        return oob, endless_demo

    utils.loop_every(dt, pid_loop)


def run_simulation( human, initial_ball_position = init_position):
    if human:
        p.connect(p.GUI)
    else:
        p.connect(p.DIRECT)
    p.setAdditionalSearchPath("assets")
    plate = p.loadURDF("/Users/rithvikdoshi/workspace/balance-ball/py/env/assets/plate.urdf")
    #zoom to the plate
    p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])

    p.setJointMotorControl2(plate, 0, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)
    p.setJointMotorControl2(plate, 1, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)

    p.setGravity(0, 0, -9.8)
    sphere = p.createMultiBody(0.2
        , p.createCollisionShape(p.GEOM_SPHERE, radius=0.04)
        , basePosition = [initial_ball_position.x,initial_ball_position.y,0.5]
    )
    #update the simulation at 100 Hz
    p.setTimeStep(dt)
    p.setRealTimeSimulation(1)
    return World(plate=plate, sphere=sphere)

def reset_simulation_demo( human, initial_ball_position = init_position):
    pass
    # p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])
    # plate = p.loadURDF("/Users/rithvikdoshi/workspace/balance-ball/py/env/assets/plate.urdf")
    # p.setJointMotorControl2(plate, 0, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)
    # p.setJointMotorControl2(plate, 1, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)
    # sphere = p.createMultiBody(0.2
    #     , p.createCollisionShape(p.GEOM_SPHERE, radius=0.04)
    #     , basePosition = [initial_ball_position.x,initial_ball_position.y,0.5]
    # )
    
    # return World(plate=plate, sphere=sphere)

def observe():
    global x_position
    global y_position
    
    # if not x_position or not y_position:
    #     #observe for first time
    #     x_position = init_position.x
    #     y_position = init_position.y
    return np.array([x_position,y_position] , dtype=np.float32)

def action(angle_x, angle_y, world):
    def set_plate_angles(theta_x, theta_y):
        p.setJointMotorControl2(world.plate, 1, p.POSITION_CONTROL, targetPosition=np.clip(theta_x, -0.1, 0.1), force=5, maxVelocity=2)
        p.setJointMotorControl2(world.plate, 0, p.POSITION_CONTROL, targetPosition=np.clip(-theta_y, -0.1, 0.1), force=5, maxVelocity=2)
    set_plate_angles(angle_x, angle_y)

def reward():
    ob = observe()
    x = ob[0]
    y = ob[1]
    if x < -0.4 or x > 0.4 or y < -0.25 or y > 0.25:
        return float('-inf')
    return -1 * (x ** 2 + y** 2)

if __name__ == "__main__":
    cmd_args = parse_args()
    world = run_simulation(True)
    while (True):
        run_controller(**vars(cmd_args), world=world)
        # world = reset_simulation_demo(True)