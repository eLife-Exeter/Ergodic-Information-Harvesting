# -*- coding: utf-8 -*-
import numpy as np
from scipy.integrate import trapz, quad, solve_ivp
from scipy.interpolate import interp1d

from ErgodicHarvestingLib.utils import matmult


class ProjectionBasedOpt(object):
    def __init__(self, nx, nu, R, time, Quinit):
        """
        Class to represent an optimization problem for a system with dynamic constraints.
        :nx dimension of state
        :nu dimension of the control
        """

        self.nx = nx  # Dimension of State   X
        self.nu = nu  # Dimension of Control U

        self.mass = 1.0  # Mass of the Dynamics Model

        self.Q = np.eye(self.nx)
        self.R = R * np.eye(self.nu)
        self.Quinit = Quinit  # weight for the initial control

        self.P1 = 1.0
        self.Qn = 1.0
        self.Rn = 1.0
        self.Qk = 1.0
        self.Rk = 1.0

        self.time = time

        odeDeltaT = time[1] - time[0]
        self.odeParam = {
            "method": "RK23",
            "t_span": (time[0], time[-1]),
            "rtol": 1e-4,
            "atol": 1e-7,
            "t_eval": time,
            "min_step": odeDeltaT,
            "first_step": odeDeltaT,
            "max_step": odeDeltaT,
        }
        self.odeIntegrator = lambda fun, y0: solve_ivp(
            fun, y0=y0, **self.odeParam
        ).y.flatten()

    def peqns(self, t, pp, Al, Bl, Rn, Qn):
        if t > self.time[-1] or t < self.time[0]:
            return 0
        pp = np.array(pp).flatten()
        pp = pp.reshape(self.nx, self.nx)
        matdiffeq = (
            matmult(pp, Al(t)) + matmult(Al(t), pp) - matmult(pp, Bl(t), Bl(t), pp) + Qn
        )
        return matdiffeq.flatten()

    def reqns(self, t, rr, Al, Bl, a, b, Psol, Rn, Qn):
        if t > self.time[-1] or t < self.time[0]:
            return np.array([0.0])
        t = self.time[-1] - t
        matdiffeq = (
            matmult((Al(t) - matmult(Bl(t), Bl(t), Psol(t))), rr)
            + a(t)
            - matmult(Psol(t), Bl(t), b(t))
        )
        return matdiffeq.flatten()

    def veqns(self, zz, Al, Bl, a, b, Psol, Rsol, Rn, Qn):
        vmatdiffeq = matmult(-Bl, Psol, zz) - matmult(Bl, Rsol) - b
        return vmatdiffeq

    def zeqns(self, t, zz, Al, Bl, a, b, Psol, Rsol, Rn, Qn):
        if t > self.time[-1] or t < self.time[0]:
            return 0
        vmateq = self.veqns(zz, Al(t), Bl(t).T, a(t), b(t), Psol(t), Rsol(t), Rn, Qn)
        matdiffeq = matmult(Al(t), zz) + matmult(Bl(t), vmateq)
        return matdiffeq.flatten()

    def Ksol(self, X, U):
        time = self.time
        P1 = np.array([1.0])
        soln = self.odeIntegrator(
            lambda t, y: self.peqns(
                t, y, self.A_interp, self.B_interp, self.Rk, self.Qk
            ),
            P1,
        )
        # Convert the list to a numpy array.
        psoln = np.array(soln).reshape(len(soln), 1)
        K = np.empty((time.shape[0], self.nx))
        for tindex, t in np.ndenumerate(time):
            K[tindex, :] = matmult(self.B_current[tindex, 0], psoln[tindex])
        self.K = K
        return K

    def Psol(self, X, U, time):
        P1 = np.array([1.0])
        soln = self.odeIntegrator(
            lambda t, y: self.peqns(
                t, y, self.A_interp, self.B_interp, self.Rn, self.Qn
            ),
            P1,
        )
        soln = np.array(soln).reshape(len(soln), 1)
        return soln

    def Rsol(self, X, U, P_interp, time):
        rinit2 = np.array([0])
        Qn = 1.0
        Rn = 1.0
        soln = self.odeIntegrator(
            lambda t, y: self.reqns(
                t,
                y,
                self.A_interp,
                self.B_interp,
                self.a_interp,
                self.b_interp,
                P_interp,
                Rn,
                Qn,
            ),
            rinit2,
        )
        soln = np.array(soln)
        soln = np.flip(soln, 0).reshape(len(soln), 1)
        return soln

    # pointwise dynamics linearizations
    def fofx_pointwise(self, X, U):
        return U

    def fofx(self, t, X, U):
        if t > self.time[-1] or t < self.time[0]:
            return 0
        return U(t)

    def dfdx_pointwise(self, x, u):
        return np.array([0])

    def dfdx(self):
        time = self.time
        dfdxl = np.empty([time.shape[0], self.nx])
        for tindex, _ in np.ndenumerate(time):
            dfdxl[tindex, :] = np.array([0])
        self.A_current = dfdxl
        return dfdxl

    def dfdu_pointwise(self, x, u):
        return np.array([1])

    def dfdu(self):
        time = self.time
        dfdul = np.empty([time.shape[0], self.nx])
        for tindex, _ in np.ndenumerate(time):
            dfdul[tindex, :] = np.array([1])
        self.B_current = dfdul
        return dfdul

    def cost_pointwise(self, x, u):
        R = self.R
        return 0.5 * matmult(u, R, u)

    def cost(self, X, U):
        cost = np.empty(self.time.shape[0])
        for tindex, _ in np.ndenumerate(self.time):
            cost[tindex] = self.cost_pointwise(X[tindex], U[tindex])
        return trapz(cost, self.time)  # Integrate over time

    def eval_cost(self):
        # return the evaluated cost function
        return self.cost(self.X_current, self.U_current)

    def dldu_pointwise(self, x, u):
        # return the pointwise linearized cost WRT state
        return matmult(self.R, u)

    def dldx_pointwise(self, x, u):
        # return pointwise linearized cost WRT input
        return np.array([0.0])

    def dldx(self):
        # evaluate linearized cost WRT state
        X = self.X_current
        U = self.U_current
        time = self.time
        dldxl = np.empty((time.shape[0], self.nx))
        for tindex, _ in np.ndenumerate(time):
            dldxl[tindex, :] = self.dldx_pointwise(X[tindex], U[tindex])
        self.a_current = dldxl
        return self.a_current

    def dldu(self):
        # evaluate linearized cost WRT input
        X = self.X_current
        U = self.U_current
        time = self.time
        dldul = np.empty((time.shape[0], 1))
        for tindex, _ in np.ndenumerate(time):
            dldul[tindex, :] = self.dldu_pointwise(X[tindex], U[tindex])
        dldul[0, :] += self.uinit * self.Quinit  # initial control
        self.b_current = dldul
        return dldul

    def dcost(self, descdir):
        # evaluate directional derivative
        dX = descdir[0]
        dU = descdir[1]
        time = self.time
        dc = np.empty(time.shape[0])
        for tindex, _ in np.ndenumerate(time):
            dc[tindex] = matmult(self.a_current[tindex], dX[tindex]) + matmult(
                self.b_current[tindex], dU[tindex]
            )
        intdcost = trapz(dc, time)
        return intdcost

    def descentdirection(self):
        # solve for the descent direction by
        X = self.X_current
        U = self.U_current
        time = self.time
        Ps = self.Psol(X, U, time)
        self.P_current = Ps
        P_interp = interp1d(time, Ps.T)
        Rs = self.Rsol(X, U, P_interp, time).flatten()
        self.R_current = Rs
        r_interp = interp1d(time, Rs.T)

        zinit = -matmult(P_interp(0) ** -1, r_interp(0))
        soln = self.odeIntegrator(
            lambda t, y: self.zeqns(
                t,
                y,
                self.A_interp,
                self.B_interp,
                self.a_interp,
                self.b_interp,
                P_interp,
                r_interp,
                self.Rn,
                self.Qn,
            ),
            zinit,
        )
        # Convert the list to a numpy array.
        zsoln = np.array(soln)
        zsoln = zsoln.reshape(time.shape[0], 1)
        vsoln = np.empty(U.shape)
        for tindex, t in np.ndenumerate(time):
            vsoln[tindex] = self.veqns(
                zsoln[tindex],
                self.A_current[tindex],
                self.B_current[tindex],
                self.a_current[tindex],
                self.b_current[tindex],
                Ps[tindex],
                Rs[tindex],
                self.Rn,
                self.Qn,
            )
        return [zsoln, vsoln]

    def simulate(self, X0, U):
        time = self.time
        U_interp = interp1d(time, U.T)
        # Solve ODE
        soln = self.odeIntegrator(lambda t, y: self.fofx(t, y, U_interp), X0)
        # Convert the list to a numpy array.
        xsoln = np.array(soln).reshape(len(soln), 1)
        return xsoln

    def proj(self, t, X, K, mu, alpha):
        if type(X) is float:
            X = np.array(X)
        if t > self.time[-1] or t < self.time[0]:
            return 0
        uloc = mu(t) + matmult(K(t), (alpha(t).T - X.T))
        return uloc

    def projcontrol(self, X, K, mu, alpha):
        uloc = mu + matmult(K, (alpha.T - X.T))
        return uloc

    def project(self, X0, traj):
        time = self.time
        alpha = traj[0]
        mu = traj[1]

        # solve for riccatti gain
        Ks = self.Ksol(alpha, mu)
        K_interp = interp1d(time, Ks.T)
        mu_interp = interp1d(time, mu.T)
        alpha_interp = interp1d(time, alpha.T)
        # Solve ODE
        soln = self.odeIntegrator(
            lambda t, y: self.proj(t, y, K_interp, mu_interp, alpha_interp), X0
        )
        # Convert the list to a numpy array.
        xsoln = np.array(soln).reshape(len(soln), 1)
        usoln = np.empty(mu.shape)
        for tindex, _ in np.ndenumerate(time):
            usoln[tindex, :] = self.projcontrol(
                xsoln[tindex], Ks[tindex], mu[tindex], alpha[tindex]
            )
        return np.array([xsoln, usoln])

    def update_traj(self, X, U):
        self.X_current = X
        self.U_current = U
        self.dfdx()
        self.dfdu()
        self.dldx()
        self.dldu()
        self.A_interp = interp1d(self.time, self.A_current.T)
        self.B_interp = interp1d(self.time, self.B_current.T)
        self.a_interp = interp1d(self.time, self.a_current.T)
        self.b_interp = interp1d(self.time, self.b_current.T)


class ErgodicOpt(ProjectionBasedOpt):
    def __init__(self, nx, nu, ergParam, uinit):

        super().__init__(
            nx, nu, R=ergParam.wControl, time=ergParam.time, Quinit=ergParam.wInitCtrl
        )

        self.barrcost = ergParam.wBarrCost
        self.ergcost = ergParam.wErgCost
        self.Nfourier = ergParam.nFourier
        self.uinit = uinit
        self.dimw = 1  # workspace dimension
        self.wlimit = 1.0
        self.tRes = ergParam.tRes  # Time Resolution
        self.res = ergParam.res  # EID spatial resolution
        self.eidTime = ergParam.eidTime
        self.xlist = np.linspace(0.0, 1.0, self.tRes)
        # set up a grid over the frequency
        klist = np.arange(self.Nfourier)
        # do some ergodic stuff
        s = (float(self.dimw) + 1.0) / 2.0
        self.Lambdak = 1.0 / (1.0 + klist ** 2) ** s
        self.klist = klist / self.wlimit * np.pi
        self.hk = np.zeros(self.Nfourier).flatten()
        for index in range(self.Nfourier):
            integ = quad(lambda x: (np.cos(x * self.klist[index])) ** 2, 0.0, 1.0)
            self.hk[index] = np.sqrt(integ[0])

    def normalize_pdf(self):
        # function to normalize a pdf
        self.pdf /= np.sum(self.pdf) / np.product(self.pdf.shape)

    def set_pdf(self, pdf):
        # input pdf
        pdfInterp = interp1d(self.eidTime, pdf)
        self.pdf = pdfInterp(self.xlist)
        self.normalize_pdf()
        self.calculate_uk(self.pdf)
        pass

    def calculate_ergodicity(self):
        # evaluate the ergodic metric (ck, uk, need to be calculated already)
        self.erg = np.sum(self.Lambdak * (self.ck - self.uk) ** 2)
        return self.erg

    def barrier(self, xk):
        barr_cost = np.zeros(xk.shape[0])
        xk = xk.flatten()
        too_big = xk[np.where(xk > self.wlimit)]
        barr_cost[np.where(xk > self.wlimit)] = np.square(too_big - self.wlimit)
        too_small = xk[np.where(xk < 0)]
        barr_cost[np.where(xk < 0)] += np.square(too_small)
        barr_cost = trapz(barr_cost, self.time)
        return barr_cost

    def Dbarrier(self, xk):
        xk = xk.flatten()
        dbarr_cost = np.zeros(xk.shape).reshape(xk.size, 1)
        too_big = xk[np.where(xk > self.wlimit)]
        dbarr_cost[np.where(xk > self.wlimit), 0] = 2.0 * (too_big - self.wlimit)
        too_small = xk[np.where(xk < 0)]
        dbarr_cost[np.where(xk < 0), 0] = 2.0 * too_small

        return dbarr_cost

    def calculate_uk(self, pdf):
        # calculate Fourier coefficients of the distribution
        self.uk = np.zeros(self.Nfourier).flatten()
        for index in range(len(self.uk)):
            uk_interior = pdf / self.hk[index]
            basis_part = np.cos(self.klist[index] * self.xlist)
            uk_interior *= self.wlimit / self.res * basis_part
            self.uk[index] = np.sum(uk_interior)

    def ckeval(self):
        X = self.X_current
        time = self.time
        T = time[-1]
        # change coordinates from configuration to ergodic workspace
        W = X.flatten()
        self.ck = np.zeros(self.Nfourier).flatten()
        for index in range(len(self.ck)):
            ck_interior = 1.0 / (self.hk[index] * T)
            basis_part = np.cos(self.klist[index] * W)
            ck_interior = ck_interior * basis_part
            self.ck[index] = trapz(ck_interior, time)

    def akeval(self):
        X = self.X_current
        time = self.time
        T = time[-1]
        xlist = X.flatten()
        outerchain = 2.0 * self.Lambdak * (self.ck - self.uk) / (self.hk * T)
        ak = []
        for index in range(self.Nfourier):
            # these are chain rule terms, get added
            term = outerchain[index]
            basis_part = -self.klist[index] * np.sin(self.klist[index] * xlist)
            term *= basis_part
            ak.append(term)
        summed_ak = np.sum(np.array(ak), axis=0)
        self.ak = np.array(summed_ak).reshape(summed_ak.size, 1)
        return self.ak

    def evalcost(self):
        cost = self.cost(self.X_current, self.U_current)
        barr_cost = self.barrcost * self.barrier(self.X_current)
        erg_cost = self.ergcost * self.calculate_ergodicity()
        J = barr_cost + erg_cost + cost
        return J

    def dldx(self):
        X = self.X_current
        self.a_current = self.ergcost * self.ak + self.barrcost * self.Dbarrier(X)
        return self.a_current

    def update_traj(self, X, U):
        self.X_current = X
        self.U_current = U
        self.ckeval()
        self.akeval()
        self.dfdx()
        self.dfdu()
        self.dldx()
        self.dldu()
        self.A_interp = interp1d(self.time, self.A_current.T)
        self.B_interp = interp1d(self.time, self.B_current.T)
        self.a_interp = interp1d(self.time, self.a_current.T)
        self.b_interp = interp1d(self.time, self.b_current.T)
