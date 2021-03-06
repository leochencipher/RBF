#!/usr/bin/env python
#
# Demonstrates how to efficiently use the RBF-FD method for solving a 
# PDE. This script solves the
#
#  (d^2/dx^2 + d^2/dy^2)u(x,y) = 0.0     in D 
#    (nx*d/dx + ny*d/dy)u(x,y) = 0.0     on dD
#                       u(x,y) = 1.0     on C1
#                       u(x,y) = -1.0    on C2
#
# where D is an annulus with inner radius 1, outer radius 2, and a 
# slit along the positive x-axis. dD are the edges of the annulus, C1 
# and C2 are the top and bottom edges of the slit, nx and ny are the x 
# and y components of the outward normal vectors to dD. The second 
# equation is a free surface boundary condition. For improved 
# accuracy, ghost nodes should be added along free surfaces.  We 
# demonstrate how to add ghost nodes in ghosts.py.
import numpy as np
import rbf.basis
from rbf.nodes import menodes
from rbf.geometry import simplex_outward_normals
from rbf.fd import weight_matrix
import matplotlib.pyplot as plt
import scipy.sparse
from matplotlib import cm
import logging
# set default cmap to viridis if you have it
if 'viridis' in vars(cm):
  plt.rcParams['image.cmap'] = 'viridis'



logging.basicConfig(level=logging.DEBUG)

gap = 5.0*np.pi/180.0

def solution(x):
  angle = np.arctan2(x[:,1],x[:,0]) 
  angle[angle > 0.0] -= 2*np.pi 
  u = angle/((2*np.pi - gap)/(2*np.pi))
  u /= np.pi
  u += 1
  return u
  
# number of nodes
N = 200

# define the vertices and simplices for cut annulus
t = np.linspace(gap,2*np.pi,100)
vert_outer = np.array([2*np.cos(t),2*np.sin(t)]).T
vert_inner = np.array([np.cos(t[::-1]),np.sin(t[::-1])]).T
vert = np.vstack((vert_outer,vert_inner))
smp = np.array([np.arange(200),np.roll(np.arange(200),-1)]).T

# setting bound_force=True ensures that the edges where the annulus is 
# cut will have an appropriate number of boundary nodes. This also 
# makes the function considerably slower
nodes,smpid = menodes(N,vert,smp,bound_force=True)

# identify nodes associated with the different boundary types
slit_top, = (smpid==199).nonzero()
slit_bot, = (smpid==99).nonzero()
# edges of the annulus minus the cut
boundary, = ((smpid>=0) & (smpid!=199) & (smpid!=99)).nonzero()
interior, = (smpid==-1).nonzero()

# do not build stencils which cross this line
bnd_vert = np.array([[0.0,0.0],[10*np.cos(gap/2.0),10*np.sin(gap/2.0)]])
bnd_smp = np.array([[0,1]])
weight_kwargs = {'vert':bnd_vert,'smp':bnd_smp,'n':20}
# build lhs
# enforce laplacian on interior nodes
A_interior = weight_matrix(nodes[interior],nodes,[[2,0],[0,2]],
                           **weight_kwargs)

# find boundary normal vectors
normals = simplex_outward_normals(vert,smp)[smpid[boundary]]
n1 = scipy.sparse.diags(normals[:,0],0)
n2 = scipy.sparse.diags(normals[:,1],0)
# enforce free surface boundary conditions
A_boundary = (n1*weight_matrix(nodes[boundary],nodes,[1,0],**weight_kwargs) +
              n2*weight_matrix(nodes[boundary],nodes,[0,1],**weight_kwargs))

# These next two matrices are really just identity matrices padded with zeros
A_slit_top = weight_matrix(nodes[slit_top],nodes,[0,0],**weight_kwargs)
A_slit_bot = weight_matrix(nodes[slit_bot],nodes,[0,0],**weight_kwargs)

# stack all the matrices
A = scipy.sparse.vstack((A_interior,A_boundary,
                         A_slit_top,A_slit_bot))

# build the rhs 
d_interior = np.zeros(interior.shape[0])
d_boundary = np.zeros(boundary.shape[0])
d_slit_top = -np.ones(slit_top.shape[0])
d_slit_bot = np.ones(slit_bot.shape[0])
d = np.concatenate((d_interior,d_boundary,d_slit_top,d_slit_bot))

# solve for u
soln = scipy.sparse.linalg.spsolve(A,d)

# interpolate the estimated solution
itp,dummy = menodes(10000,vert,smp,bound_force=False,itr=10)
soln_itp = weight_matrix(itp,nodes,[0,0],**weight_kwargs).dot(soln)

# calculate the true solution
true_soln = solution(itp)

fig,ax  = plt.subplots(1,2,figsize=(10,4))
p = ax[0].scatter(itp[:,0],itp[:,1],s=10,c=soln_itp,edgecolor='none')
fig.colorbar(p,ax=ax[0])
ax[0].plot(nodes[:,0],nodes[:,1],'ko',markersize=5)
for s in smp:
  ax[0].plot(vert[s,0],vert[s,1],'k-',lw=2)

p = ax[1].scatter(itp[:,0],itp[:,1],s=10,c=soln_itp - true_soln,edgecolor='none')
fig.colorbar(p,ax=ax[1])
for s in smp:
  ax[1].plot(vert[s,0],vert[s,1],'k-',lw=2)

ax[0].set_aspect('equal')
ax[1].set_aspect('equal')
ax[0].set_title('RBF-FD solution')
ax[1].set_title('error')
ax[0].set_xlim((-2.1,2.1))
ax[0].set_ylim((-2.1,2.1))
ax[1].set_xlim((-2.1,2.1))
ax[1].set_ylim((-2.1,2.1))
fig.tight_layout()
plt.savefig('figures/annulus.png')
plt.show()
quit()

