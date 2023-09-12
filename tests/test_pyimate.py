import numpy as np 
from scipy.sparse.linalg import LinearOperator, aslinearoperator

def test_randomness():
  pass

def test_blas():
  pass


def test_trace_estimator():
  import imate
  from pyimate.trace import slq
  T = imate.toeplitz(np.random.uniform(20), np.random.uniform(19))
  tr_est = slq(T, orthogonalize=20, confidence_level=0.99, error_atol=0.0, error_rtol=1e-2, min_num_samples=150, max_num_samples=200, num_threads=1)
  print(f"True: {np.sum(T.diagonal()):.8f}, Est: {np.mean(tr_est):.8f}")
  
  info['convergence']['samples'].mean(axis=1)
  n_samples = int(info['convergence']['num_samples_used'])
  np.cumsum(np.ravel(info['convergence']['samples']))/np.arange(1, n_samples+1)
  # imate.trace(T, method="slq")
  pass

def test_eigen():
  # %% test lanczos tridiagonalization
  import numpy as np 
  import pyimate
  from scipy.linalg import eigh_tridiagonal
  from scipy.sparse.linalg import eigsh
  from scipy.sparse import random
  n = 30 
  A = random(n,n,density=0.30**2)
  A = A @ A.T
  alpha, beta = np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32)
  v0 = np.random.uniform(size=A.shape[1])
  pyimate._sparse_eigen.lanczos_tridiagonalize(A, v0, 1e-9, n-1, alpha, beta)
  ew_lanczos = np.sort(eigh_tridiagonal(alpha, beta[:-1], eigvals_only=True))[1:]
  ew_true = np.sort(eigsh(A, k=n-1, return_eigenvectors=False))
  assert np.mean(np.abs(ew_lanczos - ew_true)) <= 1e-5

def test_lanczos():
  from scipy.sparse.linalg import eigsh
  from scipy.linalg import eigh_tridiagonal
  from pyimate import _diagonalize
  np.random.seed(1234)
  n = 30
  A = np.random.uniform(size=(n, n)).astype(np.float32)
  A = A @ A.T
  lo = aslinearoperator(A)
  alpha, beta = np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32)
  
  ## In general not guaranteed, but with full re-orthogonalization it seems likely!
  tol = np.zeros(30)
  for i in range(30):
    v0 = np.random.uniform(size=lo.shape[1])
    _diagonalize.lanczos_tridiagonalize(lo, v0, 1e-8, n-1, alpha, beta)
    ew = np.sort(eigh_tridiagonal(alpha, beta[:-1], eigvals_only=True))
    tol[i] = np.mean(np.abs(ew - np.sort(eigsh(A, k=n, return_eigenvectors=False))))
  assert np.all(tol < 1e-5)

def test_operators():
  # %% Test diagonal operator 
  from pyimate import _operators
  y = np.random.uniform(size=10).astype(np.float32)
  op = _operators.PyDiagonalOperator(y)
  assert np.allclose(op.matvec(y), y * y)
  assert op.dtype == np.dtype(np.float32)
  assert op.shape == (10,10)
  assert isinstance(aslinearoperator(op), LinearOperator)

  # %% Test dense operator 
  A = np.random.uniform(size=(10, 10)).astype(np.float32)
  op = _operators.PyDenseMatrix(A)
  assert np.allclose(op.matvec(y), A @ y)
  assert op.dtype == np.dtype(np.float32)
  assert op.shape == (10,10)
  assert isinstance(aslinearoperator(op), LinearOperator)

  # %% Test linear operator 
  # TODO: Implement matmat and rmatmat and maybe adjoint! Should fix the svd issue
  from pyimate import _operators
  y = np.random.uniform(size=10).astype(np.float32)
  A = np.random.uniform(size=(10, 10)).astype(np.float32)
  A = A @ A.T
  lo = aslinearoperator(A)
  op = aslinearoperator(_operators.PyLinearOperator(lo))
  for _ in range(100):
    y = np.random.uniform(size=10).astype(np.float32)
    assert np.allclose(op.matvec(y), A @ y)
  assert op.dtype == np.dtype(np.float32)
  assert op.shape == (10,10)
  assert isinstance(aslinearoperator(op), LinearOperator)
  from scipy.sparse.linalg import eigsh
  np.allclose(np.abs(eigsh(op, k = 9)[0]), np.abs(eigsh(A, k = 9)[0]), atol=1e-6)

  # %% Test adjoint operator 
  # TODO: Implement matmat and rmatmat and maybe adjoint! Should fix the svd issue
  from pyimate import _operators
  y = np.random.uniform(size=10).astype(np.float32)
  A = np.random.uniform(size=(10, 10)).astype(np.float32)
  lo = aslinearoperator(A)
  op = _operators.PyAdjointOperator(lo)
  for _ in range(100):
    y = np.random.uniform(size=10).astype(np.float32)
    assert np.allclose(op.matvec(y), A @ y)
    assert np.allclose(op.rmatvec(y), A.T @ y)
  y = np.array([-0.61796093, 0.0286501, -0.1391555, -0.11632636, 0.15005986, -0.17718734, 0.21373063, -0.38565466, 0.3330924, 0.16717383])
  op.matvec(y), A @ y
  assert op.dtype == np.dtype(np.float32)
  assert op.shape == (10,10)
  assert isinstance(aslinearoperator(op), LinearOperator) ## todo: why isn't this true generically? gues SciPy doesn't use abc's 
  from scipy.sparse.linalg import svds
  np.abs(svds(op, k=9, tol=0)[1]) 
  np.abs(svds(lo, k=9, tol=0)[1])
  np.abs(svds(A, k=9, tol=0)[1])
  ## How are these not identical???

  ## See: https://github.com/scipy/scipy/issues/16928
  class MyLinearOp:
    def __init__(self, op):
      self.op = op
      self.dtype = A.dtype
      self.shape = A.shape
    
    def matvec(self, v: np.ndarray) -> np.ndarray: 
      v = np.ravel(v) 
      assert len(v) == self.shape[1]
      x = self.op.matvec(v)
      if not np.allclose(x, A @ v):
        print(np.linalg.norm(x-v))
      #assert np.allclose(x, A @ v)
      return x
    
    def rmatvec(self, v: np.ndarray) -> np.ndarray: 
      v = np.ravel(v) 
      assert len(v) == self.shape[0]
      x = self.op.rmatvec(v)
      if not np.allclose(x, A @ v):
        # print(np.linalg.norm(x-v))
        print(v)
      #assert np.allclose(x, A.T @ v)
      return x
    
    def _matmat(self, X):
      return np.column_stack([self.matvec(col) for col in X.T])

    def _rmatmat(self, X):
      return np.column_stack([self.rmatvec(col) for col in X.T])  

    my_op = MyLinearOp(op)
    np.abs(svds(my_op, k=9, tol=0)[1])
    np.abs(svds(MyLinearOp(aslinearoperator(A)), k=9, tol=0)[1])



  # %% test bidiagonalization
  from pyimate import _diagonalize
  v0 = np.random.uniform(size=op.shape[1])
  lanczos_tol = 0.01 
  orthogonalize = 3
  alpha, beta = np.zeros(10, dtype=np.float32), np.zeros(10, dtype=np.float32)
  _diagonalize.golub_kahan_bidiagonalize(op, v0, lanczos_tol, orthogonalize, alpha, beta)

  # %% Test Lanczos via Diagonal operator C++ 
  from pyimate import _diagonalize
  d = np.random.uniform(size=10, low=0, high=1).astype(np.float32)
  v0 = np.random.uniform(size=10, low=-1, high=1).astype(np.float32)
  alpha, beta = np.zeros(10, dtype=np.float32), np.zeros(10, dtype=np.float32)
  _diagonalize.test_lanczos(d, v0, 1e-8, 0, alpha, beta)
  V = np.zeros(shape=(10,10), dtype=np.float32)
  _diagonalize.eigh_tridiagonal(alpha, beta, V) # note this replaces alphas
  np.allclose(np.sort(d), np.sort(alpha), atol=1e-6) 

# def test_
# %%
