from itertools import product
from multiprocessing import Pool, Queue, get_context
from queue import Empty
from os import makedirs, getpid
from os.path import exists
from numpy import linspace
import numpy as np
from scipy.io import loadmat
import time

from ErgodicHarvestingLib.Simulation import EIDSim
from ErgodicHarvestingLib.EIH_API_Sim_Entropy import EIH_Sim
from ErgodicHarvestingLib.ParameterIO import loadParams
from ErgodicHarvestingLib.Targets import RealTarget, Distractor
from ErgodicHarvestingLib.utils import print_color


# Load and normalize moth tracking data for EIH simulations
# Returns [sensor, target] trajectory
def flatten(x):
    out = []
    for r in x[0]:
        out.append(r[0])
    return np.array(out)


def normalize(s, t, mid=0.5, gain=0.1):
    # Remove offset
    sMean = np.mean(s)
    s -= np.mean(s)
    t -= sMean
    # Scale
    sScale = np.max(s) * gain ** -1
    s /= sScale
    t /= sScale
    # Offset
    s += mid
    t += mid
    return s, t


def loadMothData(target="M300lux", trialID=0, nrmMid=0.5, nrmGain=0.1):
    traj = flatten(
        loadmat(
            "../Production-Figure-Code/PublishedData/animal_behavior_data/Moth/MothData.mat"
        )[f"trial_{target}"]
    )[trialID, :, :]
    s, t = normalize(traj[:, 0], traj[:, 1], nrmMid, nrmGain)
    return [s, t]


def QueueWorker(mp_queue):
    while True:
        try:
            args = mp_queue.get(block=True, timeout=5.0)
            if isinstance(args, list):
                # wiggle attenuation sim
                print_color(
                    f"[WorkerNode-{getpid()}] Received new job {args[3]}",
                    color="yellow",
                )
                EIH_Sim(*args)
            else:
                # other sims
                print_color(
                    f"[WorkerNode-{getpid()}] Received new job {args[1].filename}",
                    color="yellow",
                )
                # Do the extra initialization here to speed up.
                if isinstance(args[1].rawTraj, str) and "moth" in args[1].rawTraj:
                    args[1].rawTraj = np.array(
                        loadMothData(
                            target="M300lux", trialID=0, nrmGain=args[1].objAmp
                        )[1]
                    )
                args[0].time = linspace(0.0, args[0].timeHorizon, args[0].tRes)
                args[0].eidTime = linspace(0.0, args[0].timeHorizon, args[1].res)
                EIDSim(*args)
        except Empty:
            print_color(
                f"[WorkerNode-{getpid()}] no more work to be done, existing",
                color="yellow",
            )
            return
        except Exception:
            raise


def SimulationMainQueue(dataFiles, nThread=1):
    if type(dataFiles) is not list:
        dataFiles = [dataFiles]
    paramList = []
    simParamList = []
    nSimJobsList = []
    for dat in dataFiles:
        # Load parameters
        paramList.append(loadParams(dat))
        # Permutate conditions
        simParamList.append(
            list(
                product(
                    paramList[-1]["SNR"],
                    paramList[-1]["procNoiseSigma"],
                    paramList[-1]["pLSigmaAmp"],
                    paramList[-1]["Sigma"],
                    paramList[-1]["objAmp"],
                    paramList[-1]["dt"],
                    paramList[-1]["wControl"],
                    paramList[-1]["randSeed"],
                )
            )
        )
        nSimJobsList.append(len(simParamList[-1]))

    nTrials = len(nSimJobsList)
    # additional wiggle attenuation sims
    with open("./SimParameters/SimJobList.txt", "r") as fp:
        attenuation_sim_trials = fp.readlines()
        attenuation_sim_trials.sort()
        attenuation_sim_trials.clear()
    nAttenuationSimTrials = len(attenuation_sim_trials)

    nTotalJobs = sum(nSimJobsList) + nAttenuationSimTrials
    # Limit pool size when job size is smaller than total available threads
    if nTotalJobs < nThread:
        nThread = nTotalJobs
    # Start a new parallel pool
    print("Starting parallel pool with {0} threads".format(nThread))
    ctx = get_context("fork")
    pool = Pool(processes=nThread)
    max_queue_size = min(2 * nThread, nTotalJobs)
    work_queue = Queue(maxsize=max_queue_size)
    jobs = []
    remaining_jobs = nTotalJobs
    # Kick off worker threads
    for _ in range(nThread):
        # Start a new job thread
        try:
            p = pool.Process(target=QueueWorker, args=(work_queue,))
        except Exception:
            if ctx is not None:
                # Fallback to use context
                p = ctx.Process(target=QueueWorker, args=(work_queue,))
        p.start()
        jobs.append(p)
    for trial in range(nTrials):
        # Parse parameters
        param = paramList[trial]
        simParam = simParamList[trial]
        nJobs = nSimJobsList[trial]
        eidParam = param["eidParam"]
        ergParam = param["ergParam"]
        filename = param["filename"]
        # Check if saveDir exists, create the folder if not
        if not exists(eidParam.saveDir):
            print(f"Save folder {eidParam.saveDir} does not exist, creating...")
            makedirs(eidParam.saveDir)
        ergParam.time = None
        ergParam.eidTime = None
        for it in range(nJobs):
            eidParam.SNR = simParam[it][0]
            eidParam.procNoiseSigma = simParam[it][1]
            eidParam.pLSigmaAmp = simParam[it][2]
            eidParam.pLSigmaAmpBayesian = simParam[it][2]
            eidParam.pLSigmaAmpEID = simParam[it][2]
            eidParam.Sigma = simParam[it][3]
            eidParam.objAmp = simParam[it][4]
            ergParam.dt = simParam[it][5]
            eidParam.UpdateDeltaT(simParam[it][5])
            if eidParam.simType == "IF":
                eidParam.maxIter = round(eidParam.maxT / ergParam.dt)
            ergParam.wControl = simParam[it][6]
            eidParam.randSeed = simParam[it][7]
            eidParam.filename = (
                filename.replace("SNR", "SNR-" + str(eidParam.SNR))
                .replace("wC", "wC-" + str(ergParam.wControl))
                .replace("RandSeed", "RandSeed-" + str(eidParam.randSeed))
            )
            # initialize multiple targets tracking
            if eidParam.multiTargetTracking == "dual":
                print(
                    f"Entering multiple target tracking with {eidParam.multiTargetTracking}!!!!!!!!!"
                )
                eidParam.multiTargetTracking = True
                eidParam.otherTargets = [RealTarget(eidParam.multiTargetInitialPos)]
            elif eidParam.multiTargetTracking == "distractor":
                print(
                    f"Entering multiple target tracking with {eidParam.multiTargetTracking}!!!!!!!!!"
                )
                eidParam.multiTargetTracking = True
                eidParam.otherTargets = [Distractor(eidParam.multiTargetInitialPos)]

            # Fill in work queue if it's not full
            work_queue.put((ergParam, eidParam, False), block=True, timeout=None)
            remaining_jobs -= 1
            print_color(
                f"[MasterNode-{getpid()}]: Adding new job {eidParam.filename}, "
                f"remaining jobs {remaining_jobs}",
                color="green",
            )
            # Unfortunately we need to wait briefly before adding new data into the queue.
            # This is because it takes some time for the object to get properly ingested.
            time.sleep(0.1)

    for it in range(nAttenuationSimTrials):
        # Fill in work queue
        work_queue.put(attenuation_sim_trials[it].split(), block=True, timeout=None)
        remaining_jobs -= 1
        print_color(
            f"[MasterNode-{getpid()}]: Adding new job {attenuation_sim_trials[it].split()[3]}, "
            f"remaining jobs {remaining_jobs}",
            color="green",
        )
        # Unfortunately we need to wait briefly before adding new data into the queue.
        # This is because it takes some time for the object to get properly ingested.
        time.sleep(0.1)

    # Wait until all the active thread to finish
    for job in jobs:
        job.join()
