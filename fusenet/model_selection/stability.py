import warnings
from collections import defaultdict

import numpy as np
from scipy import misc


class Stability():
    """Model selection via stability selection.

    Parameters
    ----------
    beta : float
        Value (0.05 by default) that controls the average variance over the
        edges of the sub-sampled graphs.

    thres : float
        Minimum value (0.001 by default) of dependence between variables for
        which an edge is drawn.

    verbose : boolean
        An indicator of verbosity.

    Attributes
    ----------
    beta : float
        Value (0.05 by default) that controls the average variance over the
        edges of the sub-sampled graphs.

    thres : float
        Minimum value (0.001 by default) of dependence between variables for
        which an edge is drawn.
    """
    def __init__(self, beta=0.05, thres=1e-3, verbose=True):
        self.beta = beta
        self.thres = thres
        self.verbose = verbose

    def _dep2adj(self, dep_matrix):
        """Convert matrix of dependencies between features as determined by the
        network inference algorithm into an adjacency matrix.

        Parameters
        ----------
        dep_matrix : ndarray (n_features, n_features)
            Matrix of dependencies between features generated by network inference
            algorithm.
        """
        assert dep_matrix.shape[0] == dep_matrix.shape[1], 'Dependency matrix is not quadratic'
        if np.allclose(dep_matrix, dep_matrix.T):
            # Factorized models generate symmetric matrix of dependencies
            adj = np.array(np.abs(dep_matrix) > self.thres, dtype=np.int)
        else:
            adj = np.maximum(np.abs(dep_matrix) > self.thres, np.abs(dep_matrix.T) > self.thres)
            adj = np.array(adj, dtype=np.int)
        return adj

    def _adj_var(self, mean_adj):
        p = mean_adj.shape[0]
        x_idx, y_idx = np.triu_indices(p, k=1)
        nck = misc.comb(p, 2)
        var = np.sum(np.multiply(2. * mean_adj[x_idx, y_idx], 1. - mean_adj[x_idx, y_idx])) / nck
        return var

    def optimal_reg(self, rhos, sample2deps):
        """Determine the optimal value of the regularization parameter that controls
        the sparsity of the graph structure.

        Parameters
        ----------
        rhos : {ndarray-like}
            Vector of values used for regularization.

        sample2deps : dict (sample identifier, list of ndarray (n_features, n_features))
            For every data subsample, a vector of dependency matrices estimated with different degrees of
            regularization. Dependency matrix encodes dependencies between features.
        """
        assert np.all([len(rhos) == len(deps) for deps in sample2deps.values()]), 'Dependency matrices for same values ' \
                                                                                  'of regularization are missing.'
        sample2adjs = defaultdict(list)
        for sample, deps in sample2deps.iteritems():
            sample2adjs[sample] = [self._dep2adj(dep) for dep in deps]
        rho2adjs = {}
        for i, rho in enumerate(rhos):
            rho2adjs[rho] = reduce(np.add, [vals[i] for vals in sample2adjs.values()])
        n_adj = float(len(sample2adjs))
        rho2mean_adj = {rho: adj / n_adj for rho, adj in rho2adjs.iteritems()}
        rho2var = {rho: self._adj_var(mean_adj) for rho, mean_adj in rho2mean_adj.iteritems()}
        # See Liu, Roeder and Wasserman: Stability approach to regularization selection (StaRS)
        # for high dimensional graphical models
        rhos = sorted(rhos)
        rho_opt = None
        for rho in rhos:
            min_var = np.min([var for lambd, var in rho2var.iteritems() if lambd <= rho])
            if min_var <= self.beta:
                rho_opt = rho
                break
        if rho_opt is None:
            rho_opt = rhos[-2]
            warnings.warn('The optimal value of regularization can not be determined with '
                          'stability selection. Value %4.7f is set.' % rho_opt, stacklevel=2)
        if self.verbose:
            print 'Selected regularization: %4.7f' % rho_opt
        return rho_opt
