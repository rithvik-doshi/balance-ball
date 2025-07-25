from os import path
from typing import Optional
import numpy as np
import gymnasium as gym
import pid
import utils
import time
import pygame
import pybullet as p
import os
from gymnasium import spaces
from gymnasium.envs.classic_control import utils
from gymnasium.error import DependencyNotInstalled
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

@dataclass
class World:
    """A dataclass to hold the world objects"""
    plate: int
    sphere: int

class AmazingEnv(gym.Env):
    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_fps": 60,
    }

    def __init__(self, g, human=False):
        #initialze env
        if human:
            p.connect(p.GUI)
        else:
            p.connect(p.DIRECT)
        self.g = g
        self.max_angle = 0.1
        self.action_space = spaces.Box(low=-self.max_angle, high=self.max_angle, shape=(2,), dtype=np.float32)
        high = np.array([0.5, 0.3], dtype=np.float32) #dimesion of plate: 0.4, 0.25
        self.observation_space = spaces.Box(            
            low=np.array([-0.5, -0.3,-1,-1]),
            high=np.array([0.5, 0.3, 1, 1]),
            dtype=np.float32) #dimension of the board
        self.init_position = Point(np.random.uniform(-0.2, 0.2),np.random.uniform(-0.2, 0.2))
        
        self.sphere = p.createMultiBody(0.2
        , p.createCollisionShape(p.GEOM_SPHERE, radius=0.04)
        , basePosition = [self.init_position.x, self.init_position.x,0.5])

        self.plate = p.loadURDF("./env/amazingball/assets/plate.urdf")

        self.world = World(plate=self.plate, sphere=self.sphere)
        
        
    def reset(self):
        # if self.sphere is not None or self.plate is not None or self.world is not None:
        #     p.disconnect()

        # p.resetSimulation()???????????????????????????????????????????
        # p.connect(p.DIRECT)

        p.setGravity(0.0, 0.0, -9.8)
        #zoom to the plate
        p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])
        p.setRealTimeSimulation(0)
        #creating world
    
        self.init_position = [np.random.uniform(-0.2, 0.2),np.random.uniform(-0.2, 0.2,), 0.1]

        #reset ball position
        p.resetBasePositionAndOrientation(self.world.sphere, self.init_position, [0, 0, 0, 1])
        #reset velocity!!!!!!!!!!!
        p.resetBaseVelocity(self.world.sphere, [0,0,0], [0,0,0])
        #reset plate
        p.resetBasePositionAndOrientation(self.world.plate, [0,0,0], [0, 0, 0, 1])
        #reset plate velocity
        p.resetBaseVelocity(self.world.plate, [0,0,0], [0,0,0])

        p.setJointMotorControl2(self.world.plate, 0, p.POSITION_CONTROL, targetPosition=0, force=100, maxVelocity=100)
        p.setJointMotorControl2(self.world.plate, 1, p.POSITION_CONTROL, targetPosition=0, force=100, maxVelocity=100)

        p.setTimeStep(0.005)

        for _ in range(10):
            p.stepSimulation()

        p.setTimeStep(0.02)

        return self._get_observation(), {}

        # super().reset()
        # del self.world
        # #close simulation??????????
        # self.world = pid.run_simulation(False)
        # obs = self.pygame.observe()
        # return obs, {}

    def step(self, action):
        theta_x, theta_y = action
        #print(theta_x, theta_y)
        p.setJointMotorControl2(self.world.plate, 1, p.POSITION_CONTROL, targetPosition=np.clip(theta_x, -0.1, 0.1), force=7, maxVelocity=4) #MBW!
        p.setJointMotorControl2(self.world.plate, 0, p.POSITION_CONTROL, targetPosition=np.clip(-theta_y, -0.1, 0.1), force=7, maxVelocity=4)#MBW!
        # Step the simulation
        p.stepSimulation()
        # Update the observation
        self.observation = self._get_observation()
        # Calculate the normalized reward
        reward = self._get_reward() 
        # Check if the episode is done
        done = self._is_done()
        # Return the observation, reward, and done flag
        return self.observation, reward, done, False, {}       

        # angle_x, angle_y = action
        # self.pygame.action(angle_x, angle_y, self.world) #where is parameter action defined?
        # obs = self.pygame.observe()
        # reward = self.pygame.reward()

        # return obs, reward, False, False, {}
    
    # def render(self):
    #     # if self.world is None:
    #     #     raise Exception("Cannot render: environment has not been initialized.")
    #     # view_matrix = p.computeViewMatrixFromYawPitchRoll(cameraTargetPosition=[0, 0, 0], distance=1.5, yaw=0, pitch=-45, roll=0, upAxisIndex=2)
    #     # proj_matrix = p.computeProjectionMatrixFOV(fov=60, aspect=1, nearVal=0.1, farVal=100.0)
    #     # img_arr = p.getCameraImage(300, 300, viewMatrix=view_matrix, projectionMatrix=proj_matrix)
    #     # rgb = img_arr[2]
    #     # p.connect(p.GUI)
    #     # return rgb
    #     p.connect(p.GUI)
    #     #zoom to the plate
    #     p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])

    

    def _get_observation(self):
        (x,y,z), orientation = p.getBasePositionAndOrientation(self.world.sphere)
        velocity = p.getBaseVelocity(self.sphere)[0][0:2]
        #print(velocity[0], " ", velocity[1])
        #return np.array([x,y,velocity[0], velocity[1]] , dtype=np.float32)
        return np.array([x,y,velocity[0],velocity[1]] , dtype=np.float32)
    
    def _get_reward(self):
        ob = self._get_observation()
        x = ob[0]
        y = ob[1]
        # if x < -0.4 or x > 0.4 or y < -0.25 or y > 0.25: #fell off
        #     return -100000
        r = np.clip(1.0 - ( ((x ** 2 + y ** 2)/ (0.4 ** 2 + 0.25 ** 2))**2 ), 0, 1)
        #print(r)
        return r
    
    def _is_done(self):
        ob = self._get_observation()
        x = ob[0]
        y = ob[1]
        # If the has fallen off the plate, the episode is done
        if x < -0.4 or x > 0.4 or y < -0.25 or y > 0.25:
            return True
        
        #if already stablizied!

        # e = 0.01
        # if np.abs(x - 0) < e and np.abs(x - 0) < e:
        #     return True
        return False

        # if True:
        #     p.connect(p.GUI)
        # else:
        #     p.connect(p.DIRECT)
        # p.setAdditionalSearchPath("assets")
        # plate = p.loadURDF("C:\\Users\\Han\\Desktop\\CS\\454\\FuzzyActorCritic\\fuzzy_rl\env\\amazingball\\assets\\plate.urdf")

        # #zoom to the plate
        # p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])

        # p.setJointMotorControl2(plate, 0, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)
        # p.setJointMotorControl2(plate, 1, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)

        # p.setGravity(0, 0, -9.8)
        # sphere = p.createMultiBody(0.2
        #     , p.createCollisionShape(p.GEOM_SPHERE, radius=0.04)
        #     , basePosition = [0,0,0.5]
        # )
        # #update the simulation at 100 Hz
        # p.setTimeStep(0.01)
        # p.setRealTimeSimulation(1)

        # pygame.init()
        # screen = pygame.display.set_mode((800, 600))
        # clock = pygame.time.Clock()

        # p.setAdditionalSearchPath("assets")
        # plate = p.loadURDF("C:\\Users\\Han\\Desktop\\CS\\454\\FuzzyActorCritic\\fuzzy_rl\\env\\amazingball\\assets\\plate.urdf")

        # # zoom to the plate
        # p.resetDebugVisualizerCamera(cameraDistance=1.0, cameraYaw=0, cameraPitch=-45, cameraTargetPosition=[0,0,0])

        # p.setJointMotorControl2(plate, 0, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)
        # p.setJointMotorControl2(plate, 1, p.POSITION_CONTROL, targetPosition=0, force=5, maxVelocity=2)

        # p.setGravity(0, 0, -9.8)
        # sphere = p.createMultiBody(0.2, p.createCollisionShape(p.GEOM_SPHERE, radius=0.04), basePosition=[0, 0, 0.5]) #CHANGE INIT POSITI
        # # update the simulation at 100 Hz
        # p.setTimeStep(0.01)
        # p.setRealTimeSimulation(1)

        # running = True
        # while running:
        #     for event in pygame.event.get():
        #         if event.type == pygame.QUIT:
        #             running = False

        #     # clear the screen
        #     screen.fill((255, 255, 255))

        #     # get the sphere position and orientation
        #     sphere_pos, sphere_orn = p.getBasePositionAndOrientation(sphere)

        #     # # draw the sphere as a circle on the screen
        #     # pygame.draw.circle(screen, (255, 0, 0), (int(sphere_pos[0] * 100 + 400), int(-sphere_pos[1] * 100 + 300)), 20)

        #     # update the simulation
        #     p.stepSimulation()

        #     # limit the framerate
        #     clock.tick(100)

        #     # update the screen
        #     pygame.display.flip()

        pygame.quit()
        
