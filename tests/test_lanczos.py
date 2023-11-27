import numpy as np 
from scipy.linalg import eigh_tridiagonal
from scipy.sparse.linalg import eigsh, aslinearoperator
from scipy.sparse import csc_array

import sys
sys.path.insert(0, '/Users/mpiekenbrock/primate/tests')

def gen_sym(n: int, ew: np.ndarray = None):
  ew = 0.2 + 1.5*np.linspace(0, 5, n) if ew is None else ew
  Q,R = np.linalg.qr(np.random.uniform(size=(n,n)))
  A = Q @ np.diag(ew) @ Q.T
  A = (A + A.T) / 2
  return A

def test_basic():
  from primate.diagonalize import lanczos
  np.random.seed(1234)
  n = 10
  A = np.random.uniform(size=(n, n)).astype(np.float32)
  A = A @ A.T
  A_sparse = csc_array(A)
  v0 = np.random.uniform(size=A.shape[1])
  (a,b), Q = lanczos(A_sparse, v0=v0, tol=1e-8, orth=n-1, return_basis = True)
  assert np.abs(max(eigh_tridiagonal(a,b, eigvals_only=True)) - max(eigsh(A_sparse)[0])) < 1e-4

def test_matvec():
  from primate.diagonalize import lanczos
  np.random.seed(1234)
  n = 10
  A = np.random.uniform(size=(n, n)).astype(np.float32)
  A = A @ A.T
  A_sparse = csc_array(A)
  v0 = np.random.uniform(size=A.shape[1])
  (a,b), Q = lanczos(A_sparse, v0=v0, tol=1e-8, orth=0, return_basis = True) 
  rw, V = eigh_tridiagonal(a,b, eigvals_only=False)
  y = np.linalg.norm(v0) * (Q @ V @ (V[0,:] * rw))
  z = A_sparse @ v0
  assert np.linalg.norm(y - z) < 1e-4

def test_accuracy():
  from primate.diagonalize import lanczos
  np.random.seed(1234)
  n = 30
  A = np.random.uniform(size=(n, n)).astype(np.float32)
  A = A @ A.T
  alpha, beta = np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32)
  
  ## In general not guaranteed, but with full re-orthogonalization it's likely (and deterministic w/ fixed seed)
  tol = np.zeros(30)
  for i in range(30):
    v0 = np.random.uniform(size=A.shape[1])
    alpha, beta = lanczos(A, v0=v0, tol=1e-8, orth=n-1)
    ew_true = np.sort(eigsh(A, k=n-1, return_eigenvectors=False))
    ew_test = np.sort(eigh_tridiagonal(alpha, beta, eigvals_only=True))
    tol[i] = np.mean(np.abs(ew_test[1:] - ew_true))
  assert np.all(tol < 1e-5)

def test_quadrature():
  from primate.diagonalize import lanczos, _lanczos
  from sanity import lanczos_quadrature
  np.random.seed(1234)
  n = 10
  A = np.random.uniform(size=(n, n)).astype(np.float32)
  A = A @ A.T
  A_sparse = csc_array(A)
  v0 = np.random.uniform(size=A.shape[1])

  ## Test the near-equivalence of the weights and nodes
  alpha, beta = lanczos(A, v0, max_steps=n, orth=n)  
  nw_test = _lanczos.quadrature(alpha, np.append(0, beta), n)
  nw_true = lanczos_quadrature(A, v=v0, k=n, orth=n)
  assert np.allclose(nw_true[0], nw_test[:,0], atol=1e-6)
  assert np.allclose(nw_true[1], nw_test[:,1], atol=1e-6)

## NOTE: trace estimation only works with isotropic vectors 
def test_slq_fixed():
  from sanity import girard_hutch
  np.random.seed(1234)
  n = 30
  ew = 0.2 + 1.5*np.linspace(0, 5, n)
  Q,R = np.linalg.qr(np.random.uniform(size=(n,n)))
  A = Q @ np.diag(ew) @ Q.T
  A = (A + A.T) / 2
  ew_true = np.linalg.eigvalsh(A)
  tr_est = girard_hutch(A, lambda x: x, nv = n, estimates=False)
  threshold = 0.05*(np.max(ew)*n - np.min(ew)*n)
  assert np.isclose(A.trace() - tr_est, 0.0, atol=threshold)

def test_slq_trace():
  np.random.seed(1234)
  A = gen_sym(30)
  from primate.diagonalize import _lanczos
  from scipy.sparse import csr_array, csc_array
  n = A.shape[1]
  A = csc_array(A, dtype=np.float32)
  kwargs = { "function" : "generic", "matrix_func" : lambda x: x }
  # args = dict(nv=10, dist=0, lanczos_degree=2, lanczos_rtol=0.0, orth=0, ncv=n, num_threads=5, seed=0)
  args = (10, 0, 2, 0.0, 0, n, 5, 0)
  _lanczos.stochastic_trace(A, *args, **kwargs)

def test_stochastic_quadrature():
  np.random.seed(1234)
  A = gen_sym(30)
  from primate.diagonalize import _lanczos
  from scipy.sparse import csr_array, csc_array
  _lanczos.stochastic_quadrature
  
  # nv, dist, lanczos_degree, lanczos_rtol, orth, ncv, num_threads, seed
  n = A.shape[1]
  A = csc_array(A, dtype=np.float32)
  _lanczos.stochastic_quadrature(A, 10, 0, 2, 0, 0, n, 5, 0)
  assert True
  # A.trace()
  # (np.linalg.norm(v0)**2) * np.sum(np.prod(nw_test, axis=1))

  # np.prod(nw_test, axis=1)
  # ew_true = np.linalg.eigvalsh(A)
  # assert np.allclose(ew_true, ew_test, atol=1e-5)

  # A.trace()
  # _lanczos.quadrature
  # assert np.abs(max(eigh_tridiagonal(a,b, eigvals_only=True)) - max(eigsh(A_sparse)[0])) < 1e-4


def test_lanczos_correctness():
  from primate.diagonalize import lanczos
  from sanity import lanczos_paige
  np.random.seed(1234)
  assert True
  ## TODO: recombine eigenvalues that are well-separated as a test matrix
  # n = 20
  # A = np.random.uniform(size=(n, n)).astype(np.float32)
  # A = A @ A.T
  # v = np.random.normal(size=n).astype(np.float32)
  # a1, b1 = lanczos_paige(A, v, k = n, tol = 0.0)
  # a2, b2 = lanczos(A, v, max_steps = n, orth=5, tol = 0.0)
  # ew1 = np.sort(eigh_tridiagonal(a1[:n], b1[1:n], eigvals_only=True))
  # ew2 = np.sort(eigh_tridiagonal(a2, b2, eigvals_only=True))
  # ew = np.sort(np.linalg.eigh(A)[0])
  # np.max(np.abs(ew - ew2))
  # np.max(np.abs(ew - ew2))
  # assert np.allclose(ew1, ew2, atol=0.1)

# def test_benchmark():
#   from primate.diagonalize import lanczos, _lanczos_base
#   from scipy.sparse import random, csc_array
#   A = random(1000, 1000, density=0.010)
#   A = csc_array(A @ A.T, dtype=np.float32)
#   assert (A.nnz / (1000**2)) <= 0.30
  
#   import timeit

#   timeit.timeit(lambda: _lanczos_base(A), number=30)
#   timeit.timeit(lambda: lanczos(A), number=30)
#   a, b = lanczos(A)


