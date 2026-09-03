"""Mat / raft foundation analysis on Winkler springs (2D FEM).

The mat slab is discretised with 4-node Mindlin-Reissner plate elements
(Q4) with selective reduced integration (2x2 Gauss for bending, 1x1 for
shear) to avoid locking. The soil is modelled with distributed Winkler
springs `k_s` (kN/m^3) lumped at the nodes via the consistent matrix
`k_s · integral N^T N dA`.

Theory: docs/theory/01_introduction.md (mat foundations) +
        Hetenyi "Beams on Elastic Foundation" (1946) extended to 2D.

Element DOFs per node: (w, theta_x, theta_y) where
- w     is vertical deflection (positive downwards)
- theta_x is rotation about X axis (right-hand rule)
- theta_y is rotation about Y axis

Constitutive:
- Bending: D_b = E h^3 / (12 (1 - nu^2)) * [[1, nu, 0], [nu, 1, 0], [0, 0, (1-nu)/2]]
- Shear:   D_s = (5/6) G h I  with G = E / (2 (1 + nu))
- Winkler: k_s acts on w only.

The solver iteratively removes springs in tension (gap detection) so that
uplift is captured. The mat lifts off where w < 0 (upwards) — those nodes
are released and the system re-solved until convergence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
# scipy.sparse imports deferred to _assemble() and solve() to keep package import lightweight


# Gauss points for 2x2 quadrature on a [-1, 1]^2 square
_GP2 = np.array([
    [-1 / np.sqrt(3), -1 / np.sqrt(3)],
    [ 1 / np.sqrt(3), -1 / np.sqrt(3)],
    [ 1 / np.sqrt(3),  1 / np.sqrt(3)],
    [-1 / np.sqrt(3),  1 / np.sqrt(3)],
])
_GW2 = np.ones(4)


def _shape_q4(xi: float, eta: float) -> Tuple[np.ndarray, np.ndarray]:
    """Bilinear Q4 shape functions and their (xi, eta) derivatives.

    Returns (N, dN_dxi_eta) where N is (4,) and dN_dxi_eta is (2, 4).
    Node ordering: ccw from (-1, -1) -> (1, -1) -> (1, 1) -> (-1, 1).
    """
    xi_i = np.array([-1.0, 1.0, 1.0, -1.0])
    eta_i = np.array([-1.0, -1.0, 1.0, 1.0])
    N = 0.25 * (1 + xi_i * xi) * (1 + eta_i * eta)
    dN_dxi = 0.25 * xi_i * (1 + eta_i * eta)
    dN_deta = 0.25 * eta_i * (1 + xi_i * xi)
    return N, np.vstack([dN_dxi, dN_deta])


def _element_stiffness_plate(
    coords: np.ndarray,
    D_b: np.ndarray,
    D_s_scalar: float,
) -> np.ndarray:
    """Plate (bending + shear) stiffness of one Q4 Mindlin element.

    Winkler springs are NOT included here — they are added at the assembly
    level as lumped, per-node stiffness so we can switch them off cleanly
    for uplift detection.
    """
    K_e = np.zeros((12, 12))

    # --- Bending: 2x2 Gauss integration ---
    for (xi, eta), w_gp in zip(_GP2, _GW2):
        N, dN_local = _shape_q4(xi, eta)
        J = dN_local @ coords  # (2,2)
        detJ = np.linalg.det(J)
        dN_xy = np.linalg.solve(J, dN_local)  # (2,4)

        B_b = np.zeros((3, 12))
        for i in range(4):
            B_b[0, 3 * i + 2] =  dN_xy[0, i]
            B_b[1, 3 * i + 1] = -dN_xy[1, i]
            B_b[2, 3 * i + 1] = -dN_xy[0, i]
            B_b[2, 3 * i + 2] =  dN_xy[1, i]
        K_e += B_b.T @ D_b @ B_b * detJ * w_gp

    # --- Shear: 1x1 reduced integration ---
    N, dN_local = _shape_q4(0.0, 0.0)
    J = dN_local @ coords
    detJ = np.linalg.det(J)
    dN_xy = np.linalg.solve(J, dN_local)

    B_s = np.zeros((2, 12))
    for i in range(4):
        B_s[0, 3 * i + 0] = dN_xy[0, i]
        B_s[0, 3 * i + 2] = N[i]
        B_s[1, 3 * i + 0] = dN_xy[1, i]
        B_s[1, 3 * i + 1] = -N[i]
    K_e += B_s.T @ (D_s_scalar * np.eye(2)) @ B_s * detJ * 4.0  # weight = 4

    return K_e


def _element_winkler_lumped(coords: np.ndarray, k_s: float) -> np.ndarray:
    """Lumped Winkler stiffness contributions per node for one element.

    The lumped diagonal matrix uses k_w_i = k_s * integral N_i dA per element.
    For a 4-node bilinear over each element, integral N_i dA = Ae / 4.

    Returns:
        (4,) array of nodal lumped Winkler stiffnesses for this element
        in the same node order as `coords`.
    """
    # Element area: |J| at centre * 4 (since reference element area is 4)
    _, dN_local = _shape_q4(0.0, 0.0)
    J = dN_local @ coords
    Ae = abs(np.linalg.det(J)) * 4.0
    return np.full(4, k_s * Ae / 4.0)


def _element_load_uniform(coords: np.ndarray, q: float) -> np.ndarray:
    """Equivalent nodal forces for a uniform downwards pressure `q` (kN/m^2)."""
    F_e = np.zeros(12)
    for (xi, eta), w_gp in zip(_GP2, _GW2):
        N, dN_local = _shape_q4(xi, eta)
        J = dN_local @ coords
        detJ = np.linalg.det(J)
        for i in range(4):
            F_e[3 * i + 0] += q * N[i] * detJ * w_gp
    return F_e


@dataclass
class ColumnLoad:
    x: float        # m
    y: float        # m
    P: float        # kN (positive downwards)
    Mx: float = 0.0 # kN.m about X
    My: float = 0.0 # kN.m about Y
    name: str = ""


@dataclass
class MatResult:
    """Output of a mat-on-Winkler analysis."""

    nodes_xy: np.ndarray         # (nnodes, 2) global coordinates [m]
    elements: np.ndarray         # (nelems, 4) node indices
    w: np.ndarray                # (nnodes,) deflection [m, +down]
    theta_x: np.ndarray          # (nnodes,) rotation about X [rad]
    theta_y: np.ndarray          # (nnodes,) rotation about Y [rad]
    q_soil: np.ndarray           # (nnodes,) soil pressure [kN/m^2]
    M_xx: np.ndarray             # (nelems,) bending moment per unit width about Y [kN.m/m]
    M_yy: np.ndarray             # (nelems,) bending moment per unit width about X [kN.m/m]
    M_xy: np.ndarray             # (nelems,) twisting moment [kN.m/m]
    uplift_nodes: List[int] = field(default_factory=list)
    iterations: int = 0
    converged: bool = True

    @property
    def w_max(self) -> float:
        return float(self.w.max())

    @property
    def w_min(self) -> float:
        return float(self.w.min())

    @property
    def settlement_mm(self) -> np.ndarray:
        """Vertical settlement at every node [mm], +down."""
        return self.w * 1000.0

    @property
    def differential_settlement_mm(self) -> float:
        """Difference between max and min vertical deflection [mm]."""
        return float((self.w.max() - self.w.min()) * 1000.0)


class MatFoundationSolver:
    """Plate-on-Winkler analyser for rectangular mat foundations.

    Example:
        mat = MatFoundationSolver(
            length=12.0, width=10.0, thickness=0.6,
            nx=24, ny=20,
            E_concrete=30e6, nu_concrete=0.20,    # kN/m^2
            k_s=20000,                            # kN/m^3
        )
        mat.add_uniform_pressure(q=15.0)         # self-weight
        mat.add_column_load(x=3.0, y=2.0, P=600)
        mat.add_column_load(x=9.0, y=8.0, P=850)
        result = mat.solve(allow_uplift=True)
    """

    def __init__(
        self,
        length: float,
        width: float,
        thickness: float,
        nx: int,
        ny: int,
        E_concrete: float = 30e6,   # kN/m^2  (30 GPa for C30)
        nu_concrete: float = 0.20,
        k_s: float = 20000.0,        # kN/m^3
        shear_factor: float = 5.0 / 6.0,
    ):
        if length <= 0 or width <= 0 or thickness <= 0:
            raise ValueError("length, width, thickness must be > 0")
        if nx < 2 or ny < 2:
            raise ValueError("Need at least 2 divisions per direction")
        if k_s <= 0:
            raise ValueError("k_s must be > 0")

        self.length = length
        self.width = width
        self.thickness = thickness
        self.nx = nx
        self.ny = ny
        self.E = E_concrete
        self.nu = nu_concrete
        self.k_s = k_s
        self.shear_factor = shear_factor

        # Build mesh
        self._build_mesh()

        # Constitutive
        h = thickness
        E = E_concrete
        nu = nu_concrete
        coeff = E * h ** 3 / (12.0 * (1.0 - nu ** 2))
        self.D_b = coeff * np.array([
            [1.0, nu, 0.0],
            [nu, 1.0, 0.0],
            [0.0, 0.0, 0.5 * (1.0 - nu)],
        ])
        G = E / (2.0 * (1.0 + nu))
        self.D_s_scalar = shear_factor * G * h

        # Load storage
        self._column_loads: List[ColumnLoad] = []
        self._uniform_pressure: float = 0.0

    # ------------------------------------------------------------------ mesh
    def _build_mesh(self) -> None:
        xs = np.linspace(0.0, self.length, self.nx + 1)
        ys = np.linspace(0.0, self.width, self.ny + 1)
        coords = []
        for y in ys:
            for x in xs:
                coords.append((x, y))
        self.nodes_xy = np.array(coords)  # (Nn, 2)
        self.n_nodes = self.nodes_xy.shape[0]
        self.n_dofs = 3 * self.n_nodes

        # Connectivity: ccw quadrilaterals
        elems = []
        stride = self.nx + 1
        for j in range(self.ny):
            for i in range(self.nx):
                n0 = j * stride + i
                n1 = n0 + 1
                n2 = n1 + stride
                n3 = n0 + stride
                elems.append((n0, n1, n2, n3))
        self.elements = np.array(elems)  # (Ne, 4)
        self.n_elems = self.elements.shape[0]

    def node_at(self, x: float, y: float) -> int:
        """Closest mesh node to a global point (x, y)."""
        d2 = (self.nodes_xy[:, 0] - x) ** 2 + (self.nodes_xy[:, 1] - y) ** 2
        return int(np.argmin(d2))

    # ----------------------------------------------------------------- loads
    def add_column_load(
        self, x: float, y: float, P: float, Mx: float = 0.0, My: float = 0.0,
        name: str = "",
    ) -> None:
        if not (0 <= x <= self.length and 0 <= y <= self.width):
            raise ValueError(f"Column ({x}, {y}) outside mat")
        self._column_loads.append(ColumnLoad(x=x, y=y, P=P, Mx=Mx, My=My, name=name))

    def add_uniform_pressure(self, q: float) -> None:
        """Add a uniform downwards pressure [kN/m^2] (e.g. self-weight)."""
        self._uniform_pressure += q

    # --------------------------------------------------------------- solver
    def _assemble(self, active_winkler_nodes: Optional[np.ndarray] = None) -> Tuple[Any, np.ndarray, np.ndarray]:
        """Assemble global K and F. Returns (K, F, nodal_winkler_stiffness)."""
        from scipy.sparse import lil_matrix
        K = lil_matrix((self.n_dofs, self.n_dofs))
        F = np.zeros(self.n_dofs)
        kw_node = np.zeros(self.n_nodes)  # lumped Winkler stiffness per node

        if active_winkler_nodes is None:
            active_winkler_nodes = np.ones(self.n_nodes, dtype=bool)

        for e in range(self.n_elems):
            ids = self.elements[e]
            coords_e = self.nodes_xy[ids]
            K_e = _element_stiffness_plate(coords_e, self.D_b, self.D_s_scalar)
            F_e = _element_load_uniform(coords_e, self._uniform_pressure)
            # Accumulate plate stiffness
            dofs = []
            for nid in ids:
                dofs.extend([3 * nid, 3 * nid + 1, 3 * nid + 2])
            dofs = np.array(dofs)
            for a in range(12):
                for b in range(12):
                    K[dofs[a], dofs[b]] += K_e[a, b]
                F[dofs[a]] += F_e[a]
            # Lumped Winkler contributions per node, only if active
            kw_local = _element_winkler_lumped(coords_e, self.k_s)
            for k, nid in enumerate(ids):
                if active_winkler_nodes[nid]:
                    kw_node[nid] += kw_local[k]

        # Add lumped springs on the w-DOF diagonal
        for nid in range(self.n_nodes):
            if kw_node[nid] > 0:
                K[3 * nid, 3 * nid] += kw_node[nid]

        # Column point loads: applied at the nearest node
        for cl in self._column_loads:
            nid = self.node_at(cl.x, cl.y)
            F[3 * nid + 0] += cl.P
            F[3 * nid + 1] += cl.Mx
            F[3 * nid + 2] += cl.My

        return K.tocsr(), F, kw_node

    def solve(
        self,
        allow_uplift: bool = True,
        max_iter: int = 25,
    ) -> MatResult:
        """Solve the mat-on-Winkler-springs system.

        With `allow_uplift=True`, the springs at nodes with w < 0 (lifting
        off) are removed iteratively until convergence (Talbot-style).
        """
        active = np.ones(self.n_nodes, dtype=bool)
        iters = 0
        converged = True

        history_states = []
        history_w = []
        from scipy.sparse.linalg import spsolve

        while True:
            K, F, _ = self._assemble(active_winkler_nodes=active)
            if not active.any():
                # All springs released — degenerate. Pin the centre to keep K non-singular.
                centre = self.node_at(self.length / 2.0, self.width / 2.0)
                rows = [3 * centre, 3 * centre + 1, 3 * centre + 2]
                for r in rows:
                    K[r, :] = 0.0
                    K[:, r] = 0.0
                    K[r, r] = 1.0
                    F[r] = 0.0
                converged = False

            u = spsolve(K, F)
            w = u[0::3]
            iters += 1
            if not allow_uplift:
                break

            state_tuple = tuple(active.tolist())
            if state_tuple in history_states:
                # Cycle detected! Select the state from the cycle that minimizes tension in active nodes
                cycle_start = history_states.index(state_tuple)
                cycle_states = history_states[cycle_start:]
                cycle_ws = history_w[cycle_start:]

                best_idx = 0
                min_tension = float("inf")
                for idx, (s_tuple, w_arr) in enumerate(zip(cycle_states, cycle_ws)):
                    s_arr = np.array(s_tuple, dtype=bool)
                    tension_nodes = s_arr & (w_arr < 0)
                    tension_sum = np.sum(np.abs(w_arr[tension_nodes])) if np.any(tension_nodes) else 0.0
                    if tension_sum < min_tension:
                        min_tension = tension_sum
                        best_idx = idx

                active = np.array(cycle_states[best_idx], dtype=bool)
                # Resolve one final time with the optimal active state
                K, F, _ = self._assemble(active_winkler_nodes=active)
                u = spsolve(K, F)
                w = u[0::3]
                converged = True
                break

            history_states.append(state_tuple)
            history_w.append(w.copy())

            # w > 0 means settling down (spring in compression — keep active).
            new_active = w > 0
            if np.array_equal(new_active, active):
                break
            active = new_active
            if iters >= max_iter:
                converged = False
                break

        theta_x = u[1::3]
        theta_y = u[2::3]
        # Soil pressure: only active springs contribute; q_soil = k_s * w
        q_soil = np.where(active & (w > 0), self.k_s * w, 0.0)

        # Compute element-centroid moments
        M_xx = np.zeros(self.n_elems)
        M_yy = np.zeros(self.n_elems)
        M_xy = np.zeros(self.n_elems)
        for e in range(self.n_elems):
            ids = self.elements[e]
            coords_e = self.nodes_xy[ids]
            u_e = np.zeros(12)
            for k, nid in enumerate(ids):
                u_e[3 * k + 0] = w[nid]
                u_e[3 * k + 1] = theta_x[nid]
                u_e[3 * k + 2] = theta_y[nid]
            # Curvatures at element centre (xi=eta=0)
            _, dN_local = _shape_q4(0.0, 0.0)
            J = dN_local @ coords_e
            dN_xy = np.linalg.solve(J, dN_local)
            B_b = np.zeros((3, 12))
            for i in range(4):
                B_b[0, 3 * i + 2] =  dN_xy[0, i]
                B_b[1, 3 * i + 1] = -dN_xy[1, i]
                B_b[2, 3 * i + 1] = -dN_xy[0, i]
                B_b[2, 3 * i + 2] =  dN_xy[1, i]
            kappa = B_b @ u_e
            moments = self.D_b @ kappa
            M_xx[e] = moments[0]
            M_yy[e] = moments[1]
            M_xy[e] = moments[2]

        uplift_nodes = list(np.where(~active)[0])
        return MatResult(
            nodes_xy=self.nodes_xy.copy(),
            elements=self.elements.copy(),
            w=w,
            theta_x=theta_x,
            theta_y=theta_y,
            q_soil=q_soil,
            M_xx=M_xx,
            M_yy=M_yy,
            M_xy=M_xy,
            uplift_nodes=uplift_nodes,
            iterations=iters,
            converged=converged,
        )
