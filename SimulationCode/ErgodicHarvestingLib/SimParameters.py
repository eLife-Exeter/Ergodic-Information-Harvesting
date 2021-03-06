# -*- coding: utf-8 -*-
import numpy as np


class ErgodicParameters:
    nIter = 14  # Number of iterations in ergodic optimization loop
    nFourier = 15  # Number of Fourier Coefficients used in Fisher Information EID
    # Cost Weights
    wBarrCost = 100  # Weight of the Barr Cost
    wErgCost = 5  # Weight of the Ergodic Cost
    wControl = 0.05  # Weight of the Control Cost
    wInitCtrl = 0  # Weight of the Initial Condition of the Control
    tRes = 101  # Time resolution for ODE
    res = 101  # Spatial Resolution
    dt = 0.02  # Time step
    # Armijo Line Search Parameters
    alpha = 0.1
    beta = 0.4
    # Time horizon and delta time used in ergodic optimizations, including ndsolver
    timeHorizon = 1

    def __init__(self):
        # Initialize Time Horizon
        self.time = np.linspace(0, self.timeHorizon, self.tRes)


class EIDParameters:
    maxIter = 40  # Number of iterations
    SNR = 30  # SNR of the sensor measurement
    Sigma = 0.05  # Sigma of Sensor measurement model
    mass = 1  # Mass of the simulated sensor
    objAmp = 0.10  # Amplitude of Object Oscillation
    objCenter = 0.5  # Center of Object Oscillation
    sInitPos = 0.4  # Initial position of the sensor
    maxT = 80  # Length of the simulation in seconds
    pLHistDepth = 1  # depth of the queue used to update likelihood function
    procNoiseSigma = 0.01  # Sigma of the process noise
    # Indexes of simulation iterations where the sensor will be blinded with randomized noise
    blindIdx = False
    # Flag to indicate whether this is a trajectory sim. Use false for sinusoid
    # and actual trajectory for perscribed trajectory sim.
    trajSim = False
    # DeltaT for trajectory simulation
    dt = 0.02
    # for multiple targets tracking
    multiTargetTracking = False
    res = 101  # Spatial Resolution of Ergodic Simulation, [# of points]
    tRes = 101  # Time resolution

    def __init__(self):
        self.maxIter = np.int(np.ceil(self.maxT / (self.dt * self.tRes)))

    def UpdateDeltaT(self, dt):
        self.dt = dt
        self.maxIter = np.int(np.ceil(self.maxT / (self.dt * self.tRes)))
