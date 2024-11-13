from typing import Any, Callable, Optional, Union

import numpy as np
from scipy.sparse.linalg import LinearOperator, aslinearoperator, eigsh
from scipy.sparse.linalg._interface import IdentityOperator

from .lanczos import _lanczos, _validate_lanczos
from .quadrature import lanczos_quadrature
from .tridiag import eigh_tridiag


def _is_linear_op(A: Any) -> bool:
	attr_checks = [hasattr(A, "__matmul__"), hasattr(A, "matmul"), hasattr(A, "dot"), hasattr(A, "matvec")]
	is_valid_op = True
	is_valid_op &= any(attr_checks)  # , "Invalid operator; must have an overloaded 'matvec' or 'matmul' method"
	is_valid_op &= hasattr(A, "shape") and len(A.shape) >= 2  # , "Operator must be at least two dimensional."
	is_valid_op &= A.shape[0] == A.shape[1]  # , "This function only works with square, symmetric matrices!"
	return is_valid_op


class MatrixFunction(LinearOperator):
	"""Linear operator class for matrix functions."""

	def __init__(
		self, A: np.ndarray, fun: np.ufunc = None, deg: int = 20, dtype: np.dtype = np.float64, **kwargs: dict
	) -> None:
		assert _is_linear_op(A), "Invalid operator `A`; must be dim=2 symmetric operator with defined matvec"
		assert deg >= 2, "Degree must be >= 2"
		if fun is not None:
			assert isinstance(fun, Callable), "Function must be numpy ufunc"
		self._fun = fun if fun is not None else lambda x: x
		self._deg = min(deg, A.shape[0])
		self._alpha = np.zeros(self._deg + 1, dtype=dtype)
		self._beta = np.zeros(self._deg + 1, dtype=dtype)
		self._nodes = np.zeros(self._deg, dtype=dtype)
		self._weights = np.zeros(self._deg, dtype=dtype)

		# ncv = kwargs.get("ncv", 3)
		## NOTE: ncv is fixed to deg for matrix function to work
		## NOTE: todo, change this to not allocate in-case quad is used
		self._Q = np.zeros((A.shape[0], self._deg), dtype=dtype, order="F")
		assert self._Q.flags["F_CONTIGUOUS"] and self._Q.flags["WRITEABLE"] and self._Q.flags["OWNDATA"]
		self._rtol = 1e-8
		orth = kwargs.get("orth", 3)
		self._orth = self._deg if orth < 0 or orth > self._deg else orth
		self._A = A
		self.shape = A.shape
		self.dtype = np.dtype(dtype)

	@property
	def degree(self) -> int:
		return self._deg

	def _adjoint(self):
		return self

	def _matvec(self, x: np.ndarray):
		if self._Q.shape[1] < self._deg:
			self._Q = np.zeros((self.shape[0], self._deg), dtype=self.dtype, order="F")
		# self.Q.fill(0)  # this is necessary to prevent orthogonalization
		self._Q[:, -self._deg :].fill(0)  # this is necessary to prevent NaN's during re-orthogonalization
		x = x.astype(self.dtype).reshape(-1)
		x_norm = np.linalg.norm(x)
		_lanczos.lanczos(self._A, x, self._deg, self._rtol, self._orth, self._alpha, self._beta, self._Q)

		## TODO: call the lapack function with pre-allocated memory for extra speed
		rw, Y = eigh_tridiag(self._alpha[: self._deg], self._beta[1 : self._deg])  # O(d^2) space
		return x_norm * self._Q @ Y @ (self._fun(rw) * Y[0, :])[:, np.newaxis]

	def quad(self, x: np.ndarray):
		r"""Estimates the quadratic form of the matrix function using Lanczos quadrature.

		This function uses the Lanczos method to estimate the quadratic form:
		$$ x \mapsto x^T f(A) x $$
		The error of the approximation depends on both the degree of the Krylov expansion and the conditioning of $f(A)$.

		Note this method is mathematically equivalent though computationally distinct from the operation `x @ (A @ x)`, i.e. the operation
		which first applies $x \mapsto f(A)x$ and then performs a dot product. In particular, the
		"""
		assert self._Q.shape[1] >= self._orth, "Auxiliary memory `Q` is not large enough for reorthogonalization."
		x = x.astype(self.dtype).reshape(-1)
		x_norm_sq = np.linalg.norm(x) ** 2
		_lanczos.lanczos(self._A, x, self._deg, self._rtol, self._orth, self._alpha, self._beta, self._Q)
		lanczos_quadrature(self._alpha, self._beta, deg=self._deg, quad="gw", nodes=self._nodes, weights=self._weights)
		return np.sum(self._fun(self._nodes) * self._weights, axis=-1) * x_norm_sq


## NOTE: this could act as a nice way of handling keyword argumetns in kwargs to generate a MF
def matrix_function(A: LinearOperator, fun: Optional[Callable] = None, v: np.ndarray = None, deg: int = 20):
	# (a, b), Q = lanczos(A, v0=v, deg=deg, return_basis=True)  # O(nd)  space
	# rw, Y = eigh_tridiag(a, b)  # O(d^2) space
	# ## Equivalent to |x| * Q @ Y @ diag(rw) @ Y.T @ e_1
	# y = np.linalg.norm(v) * Q @ Y @ (rw * Y[0, :])[:, np.newaxis]
	M = MatrixFunction(A, deg)
	return M if v is None else M._matvec(v)


## From: https://www.mathworks.com/matlabcentral/fileexchange/8548-toeplitzmult
class Toeplitz(LinearOperator):
	"""Matrix-free operator for representing Toeplitz or circulant matrices."""

	def __init__(self, c: np.ndarray, r: np.ndarray = None, dtype=None):
		self.c = np.array(c)
		self.r = np.array(c if r is None else r)
		self._d = np.concatenate((self.c, [0], np.flip(self.r[1:])))
		self._dfft = np.real(np.fft.fft(self._d))
		self._z = np.zeros(len(c) * 2)  # workspace
		self.shape = (len(c), len(c))
		self.dtype = np.dtype(np.float64) if dtype is None else dtype

	## NOTE: We return a copy because the output cannot be a view
	def _matvec(self, x: np.ndarray) -> np.ndarray:
		assert len(x) == len(self.c), f"Invalid shape of input vector 'x'; must have length {len(self.c)}"
		self._z[: self.shape[0]] = x.ravel().astype(self.dtype, copy=False)
		x_fft = np.fft.fft(self._z)
		y = np.real(np.fft.ifft(self._dfft * x_fft))
		return y[: self.shape[0]].astype(self.dtype)


def normalize_unit(A: LinearOperator, interval: tuple = (-1, 1)) -> LinearOperator:
	"""Normalizes a linear operator to have its spectra contained in the interval [-1,1]."""
	A = aslinearoperator(A) if not isinstance(A, LinearOperator) else A
	assert isinstance(A, LinearOperator), "A must be a linear operator"
	alpha = eigsh(A, k=1, which="LM", return_eigenvectors=False).item()
	I_op = IdentityOperator(A.shape)
	# np.diff(interval)
	return (A + alpha * I_op) / (2 * alpha)
