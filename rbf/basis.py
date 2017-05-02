''' 
This module contains the *RBF* class, which is used to symbolically 
define and numerically evaluate a radial basis function. *RBF* 
instances have been predefined in this module for some of the commonly 
used radial basis functions. The predefined radial basis functions are 
shown in the table below. For each expression in the table,
:math:`r = ||x - c||_2` and :math:`\epsilon` is a shape parameter. 
:math:`x` and :math:`c` are the evaluation points and radial basis 
function centers, respectively. The names of the predefined *RBF* 
instances are given in the abbreviation column. 

=================================  ============  =================  ======================================
Name                               Abbreviation  Positive Definite  Expression
=================================  ============  =================  ======================================
Eighth-order polyharmonic spline   phs8          No                 :math:`(\epsilon r)^8\log(\epsilon r)`
Seventh-order polyharmonic spline  phs7          No                 :math:`(\epsilon r)^7`
Sixth-order polyharmonic spline    phs6          No                 :math:`(\epsilon r)^6\log(\epsilon r)`
Fifth-order polyharmonic spline    phs5          No                 :math:`(\epsilon r)^5`
Fourth-order polyharmonic spline   phs4          No                 :math:`(\epsilon r)^4\log(\epsilon r)`
Third-order polyharmonic spline    phs3          No                 :math:`(\epsilon r)^3`
Second-order polyharmonic spline   phs2          No                 :math:`(\epsilon r)^2\log(\epsilon r)`
First-order polyharmonic spline    phs1          No                 :math:`\epsilon r`
Multiquadratic                     mq            No                 :math:`(1 + (\epsilon r)^2)^{1/2}`
Inverse multiquadratic             imq           Yes                :math:`(1 + (\epsilon r)^2)^{-1/2}`
Inverse quadratic                  iq            Yes                :math:`(1 + (\epsilon r)^2)^{-1}`
Gaussian                           ga            Yes                :math:`\exp(-(\epsilon r)^2)`
Exponential                        exp           Yes                :math:`\exp(-r/\epsilon)`
Squared Exponential                se            Yes                :math:`\exp(-r^2/(2\epsilon^2))`
Matern (v = 3/2)                   mat32         Yes                :math:`(1 + \sqrt{3} r/\epsilon)\exp(-\sqrt{3} r/\epsilon)`
Matern (v = 5/2)                   mat52         Yes                :math:`(1 + \sqrt{5} r/\epsilon + 5r^2/(3\epsilon^2))\exp(-\sqrt{5} r/\epsilon)`
=================================  ============  =================  ======================================

''' 
from __future__ import division 
from rbf.poly import powers
import sympy 
from sympy.utilities.autowrap import ufuncify
import numpy as np 
import logging
logger = logging.getLogger(__name__)


class _CallbackDict(dict):
  ''' 
  dictionary that calls a function after __setitem__ is called
  '''
  def __init__(self,value,callback):
    dict.__init__(self,value)
    self.callback = callback
  
  def __setitem__(self,key,value):  
    dict.__setitem__(self,key,value)
    self.callback()


def _assert_shape(a,shape,label):
  ''' 
  Raises an error if *a* does not have the specified shape. If an 
  element in *shape* is *None* then that axis can have any length.
  '''
  ashape = np.shape(a)
  if len(ashape) != len(shape):
    raise ValueError(
      '*%s* is a %s dimensional array but it should be a %s dimensional array' %
      (label,len(ashape),len(shape)))

  for axis,(i,j) in enumerate(zip(ashape,shape)):
    if j is None:
      continue

    if i != j:
      raise ValueError(
        'axis %s of *%s* has length %s but it should have length %s.' %
        (axis,label,i,j))

  return
  

def get_r():
  ''' 
  returns the symbolic variable for :math:`r` which is used to 
  instantiate an *RBF*
  '''
  return sympy.symbols('r')


def get_eps():
  ''' 
  returns the symbolic variable for :math:`\epsilon` which is used to 
  instantiate an *RBF*
  '''
  return sympy.symbols('eps')


# instantiate global symbolic variables _R and _EPS. Modifying these 
# variables will break this module
_R = get_r()    
_EPS = get_eps()


class RBF(object):
  ''' 
  Stores a symbolic expression of a Radial Basis Function (RBF) and 
  evaluates the expression numerically when called. 
  
  Parameters
  ----------
  expr : sympy expression
    Sympy expression for the RBF. This must be a function of the
    symbolic variable *r*, which can be obtained by calling *get_r()*
    or *sympy.symbols('r')*. *r* is the radial distance to the RBF
    center.  The expression may optionally be a function of *eps*,
    which is a shape parameter obtained by calling *get_eps()* or
    *sympy.symbols('eps')*.  If *eps* is not provided then *r* is
    substituted with *r*eps*.
  
  tol : float or sympy expression, optional  
    If an evaluation point, *x*, is within *tol* of an RBF center,
    *c*, then *x* is considered equal to *c*. The returned value is
    the RBF at the symbolically evaluated limit as *x* -> *c*. This is
    useful when there is a removable singularity at *c*, such as for
    polyharmonic splines. If *tol* is not provided then there will be
    no special treatment for when *x* is close to *c*. Note that
    computing the limit as *x* -> *c* can be very time intensive.
    *tol* can be a float or a sympy expression containing *eps*.

  limits : dict, optional
    Contains the limiting value of the RBF or its derivatives as *x*
    -> *c*. For example, *{(0,1):2*eps}* indicates that the limit of
    the derivative along the second Cartesian direction is *2*eps*. If
    this dictionary is provided and *tol* is not *None*, then it will
    be searched before attempting to symbolically compute the limits.
    
  backend : str, optional
    Backend used to convert the symbolic expression into a numerical
    function. This can be any of the backends supported by sympy's
    *ufuncify*. Available backends are 'numpy', 'cython', and 'f2py'.
    
  Examples
  --------
  Instantiate an inverse quadratic RBF

  >>> from rbf.basis import *
  >>> r = get_r()
  >>> eps = get_eps()
  >>> iq_expr = 1/(1 + (eps*r)**2)
  >>> iq = RBF(iq_expr)
  
  Evaluate an inverse quadratic at 10 points ranging from -5 to 5. 
  Note that the evaluation points and centers are two dimensional 
  arrays

  >>> x = np.linspace(-5.0,5.0,10)[:,None]
  >>> center = np.array([[0.0]])
  >>> values = iq(x,center)
    
  Instantiate a sinc RBF. This has a singularity at the RBF center and 
  it must be handled separately by specifying a number for *tol*.
  
  >>> import sympy
  >>> sinc_expr = sympy.sin(r)/r
  >>> sinc = RBF(sinc_expr) # instantiate WITHOUT specifying *tol*
  >>> x = np.array([[-1.0],[0.0],[1.0]])
  >>> c = np.array([[0.0]])
  >>> sinc(x,c) # this incorrectly evaluates to nan at the center
  array([[ 0.84147098],
         [        nan],
         [ 0.84147098]])

  >>> sinc = RBF(sinc_expr,tol=1e-10) # instantiate specifying *tol*
  >>> sinc(x,c) # this now correctly evaluates to 1.0 at the center
  array([[ 0.84147098],
         [ 1.        ],
         [ 0.84147098]])
  

  Notes
  -----
  The attributes *tol*, *backend*, and *limits* can be safely replaced
  with new values. It is also safe to change the entries in *limits*
  through the *__setitem__* method. Such changes will cause the cache
  of numerical functions to be cleared.
  
  '''
  @property
  def expr(self):
    # *expr* is read-only. 
    return self._expr

  @property
  def backend(self):
    return self._backend

  @property
  def tol(self):
    return self._tol

  @property
  def limits(self):
    return self._limits

  @backend.setter
  def backend(self,value):
    # let *ufuncify* decide whether *value* is appropriate
    self._backend = value
    # reset *cache* now that we have a new *backend*
    self.clear_cache()

  @tol.setter
  def tol(self,value):
    if value is not None:
      # make sure *tol* is a scalar or a sympy expression of *eps*
      value = sympy.sympify(value)
      other_symbols = value.free_symbols.difference({_EPS})
      if len(other_symbols) != 0:
        raise ValueError(
          '*tol* cannot contain any symbols other than *eps*')
  
    self._tol = value
    # reset *cache* now that we have a new *tol*
    self.clear_cache()
  
  @limits.setter
  def limits(self,value):
    if value is None:
      value = {}
      
    # if *limits* is ever changed through *__setitem__* then
    # *clear_cache* is called
    self._limits = _CallbackDict(value,self.clear_cache)
    # reset *cache* now that we have a new *limits*
    self.clear_cache()

  def __init__(self,expr,tol=None,limits=None,backend='numpy'):
    # make sure that *expr* does not contain any symbols other than 
    # *_R* and *_EPS*
    other_symbols = expr.free_symbols.difference({_R,_EPS})
    if len(other_symbols) != 0:
      raise ValueError(
        '*expr* cannot contain any symbols other than *r* and *eps*')
        
    if not expr.has(_R):
      raise ValueError(
        '*expr* must be a sympy expression containing the symbolic '
        'variable returned by *rbf.basis.get_r()*')
    
    if not expr.has(_EPS):
      # if eps is not in the expression then substitute eps*r for r
      expr = expr.subs(_R,_EPS*_R)
      
    self._expr = expr
    self.tol = tol
    self.limits = limits
    self.backend = backend
    self.cache = {}

  def __call__(self,x,c,eps=1.0,diff=None):
    ''' 
    Numerically evaluates the RBF or its derivatives.
    
    Parameters                                       
    ----------                                         
    x : (N,D) float array 
      Evaluation points
                                                                       
    c : (M,D) float array 
      RBF centers 
        
    eps : float or (M,) float array, optional
      Shape parameters for each RBF. Defaults to 1.0
                                                                           
    diff : (D,) int array, optional
      Specifies the derivative order for each Cartesian direction. For
      example, if there are three spatial dimensions then providing
      (2,0,1) would cause this function to return the RBF after
      differentiating it twice along the first axis and once along the
      third axis.

    Returns
    -------
    out : (N,M) float array
      Returns the RBFs with centers *c* evaluated at *x*

    '''
    x = np.asarray(x,dtype=float)
    _assert_shape(x,(None,None),'x')
    c = np.asarray(c,dtype=float)
    _assert_shape(c,(None,x.shape[1]),'c')

    if np.isscalar(eps):
      # makes eps an array of constant values
      eps = np.full(c.shape[0],eps,dtype=float)

    else:  
      eps = np.asarray(eps,dtype=float)

    _assert_shape(eps,(c.shape[0],),'eps')

    if diff is None:
      diff = (0,)*x.shape[1]

    else:
      # make sure diff is immutable
      diff = tuple(diff)
    
    _assert_shape(diff,(x.shape[1],),'diff')

    # expand to allow for broadcasting
    x = x.T[:,:,None] 
    c = c.T[:,None,:]

    if self.backend.lower() in ['cython','f2py']:
      # broadcasting is not allowed for these backends and we must
      # expand and flatten *x*, *c*, and *eps*
      x = x.repeat(c.shape[2],axis=2)
      c = c.repeat(x.shape[1],axis=1)
      eps = eps[None,:].repeat(x.shape[1],axis=0)
      args = (tuple(i.ravel() for i in x) + 
              tuple(i.ravel() for i in c) + 
              (eps.ravel(),))

    else: 
      args = (tuple(x)+tuple(c)+(eps,))

    # add numerical function to cache if not already
    if diff not in self.cache:
      self._add_diff_to_cache(diff)
 
    out = self.cache[diff](*args)

    if self.backend.lower() in ['cython','f2py']:
      # fold the 1d array into a 2d array
      out = out.reshape((x.shape[1],c.shape[2]))
    
    return out

  def __repr__(self):
    out = '<RBF : %s>' % str(self.expr)
    return out
     
  def _add_diff_to_cache(self,diff):
    '''     
    Symbolically differentiates the RBF and then converts the
    expression to a function which can be evaluated numerically.
    '''   
    diff = tuple(diff)
    _assert_shape(diff,(None,),'diff')

    dim = len(diff)
    c_sym = sympy.symbols('c:%s' % dim)
    x_sym = sympy.symbols('x:%s' % dim)    
    r_sym = sympy.sqrt(sum((xi-ci)**2 for xi,ci in zip(x_sym,c_sym)))
    # differentiate the RBF 
    expr = self.expr.subs(_R,r_sym)            
    for xi,order in zip(x_sym,diff):
      if order == 0:
        continue

      expr = expr.diff(*(xi,)*order)

    if self.tol is not None:
      if diff in self.limits:
        # use a user-specified limit if available      
        lim = self.limits[diff]
      
      else:  
        # Symbolically find the limit of the differentiated expression
        # as x->c. NOTE: this finds the limit from only one direction
        # and the limit may change when using a different direction.
        logger.info(
          'Symbolically computing the limit as *x* -> *c*. This may '
          'take a while. Consider manually adding the limit to the '
          '*limits* dictionary.') 
        
        lim = expr
        for xi,ci in zip(x_sym,c_sym):
          lim = lim.limit(xi,ci)

      # create a piecewise symbolic function which is center_expr when 
      # _R<tol and expr otherwise
      expr = sympy.Piecewise((lim,r_sym<self.tol),(expr,True)) 
      
    func = ufuncify(x_sym+c_sym+(_EPS,),expr,backend=self.backend)
    self.cache[diff] = func
    
  def clear_cache(self):
    ''' 
    Clears the cache of numerical functions.
    '''
    self.cache = {}
    

# Instantiate some common RBFs
phs8 = RBF((_EPS*_R)**8*sympy.log(_EPS*_R))
phs6 = RBF((_EPS*_R)**6*sympy.log(_EPS*_R))
phs4 = RBF((_EPS*_R)**4*sympy.log(_EPS*_R))
phs2 = RBF((_EPS*_R)**2*sympy.log(_EPS*_R))
phs7 = RBF((_EPS*_R)**7)
phs5 = RBF((_EPS*_R)**5)
phs3 = RBF((_EPS*_R)**3)
phs1 = RBF(_EPS*_R)
imq = RBF(1/sympy.sqrt(1+(_EPS*_R)**2))
iq = RBF(1/(1+(_EPS*_R)**2))
ga = RBF(sympy.exp(-(_EPS*_R)**2))
mq = RBF(sympy.sqrt(1 + (_EPS*_R)**2))
exp = RBF(sympy.exp(-_R/_EPS))
se = RBF(sympy.exp(-_R**2/(2*_EPS**2)))
mat32 = RBF((1 + sympy.sqrt(3)*_R/_EPS)*sympy.exp(-sympy.sqrt(3)*_R/_EPS))
mat52 = RBF((1 + sympy.sqrt(5)*_R/_EPS + 5*_R**2/(3*_EPS**2))*sympy.exp(-sympy.sqrt(5)*_R/_EPS))

# set some known limits so that sympy does not need to compute them
phs1.tol = 1e-10
for i in powers(0,1): phs1.limits[tuple(i)] = 0
for i in powers(0,2): phs1.limits[tuple(i)] = 0
for i in powers(0,3): phs1.limits[tuple(i)] = 0

phs2.tol = 1e-10
for i in powers(1,1): phs2.limits[tuple(i)] = 0
for i in powers(1,2): phs2.limits[tuple(i)] = 0
for i in powers(1,3): phs2.limits[tuple(i)] = 0

phs3.tol = 1e-10
for i in powers(2,1): phs3.limits[tuple(i)] = 0
for i in powers(2,2): phs3.limits[tuple(i)] = 0
for i in powers(2,3): phs3.limits[tuple(i)] = 0

phs4.tol = 1e-10
for i in powers(3,1): phs4.limits[tuple(i)] = 0
for i in powers(3,2): phs4.limits[tuple(i)] = 0
for i in powers(3,3): phs4.limits[tuple(i)] = 0

phs5.tol = 1e-10
for i in powers(4,1): phs5.limits[tuple(i)] = 0
for i in powers(4,2): phs5.limits[tuple(i)] = 0
for i in powers(4,3): phs5.limits[tuple(i)] = 0

phs6.tol = 1e-10
for i in powers(5,1): phs6.limits[tuple(i)] = 0
for i in powers(5,2): phs6.limits[tuple(i)] = 0
for i in powers(5,3): phs6.limits[tuple(i)] = 0

phs7.tol = 1e-10
for i in powers(6,1): phs7.limits[tuple(i)] = 0
for i in powers(6,2): phs7.limits[tuple(i)] = 0
for i in powers(6,3): phs7.limits[tuple(i)] = 0

phs8.tol = 1e-10
for i in powers(7,1): phs8.limits[tuple(i)] = 0
for i in powers(7,2): phs8.limits[tuple(i)] = 0
for i in powers(7,3): phs8.limits[tuple(i)] = 0

mat32.tol = 1e-10*_EPS
mat32.limits = {(0,):1, (1,):0, (2,):-3/_EPS**2,
                (0,0):1, (1,0):0, (0,1):0, (2,0):-3/_EPS**2, (0,2):-3/_EPS**2, (1,1):0}

mat52.tol = 1e-10*_EPS
mat52.limits = {(0,):1, (1,):0, (2,):-5/(3*_EPS**2), (3,):0, (4,):25/_EPS**4,
                (0,0):1, (1,0):0, (0,1):0, (2,0):-5/(3*_EPS**2), (0,2):-5/(3*_EPS**2), (1,1):0}
                     
