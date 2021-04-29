import numpy as np
import operator
from copy import deepcopy

def num_of_nonzero_elements(my_vector):
    '''Returns the number of non-zero elements in a vector
    '''
    counter = 0
    for element in my_vector:
        if element != 0:
            counter += 1
    return counter


def normalize_markov_matrix(transition_matrix, reversible=False):
    '''Transform a matrix of positive elements to a markov-like
    matrix by divding each row by the sum of the elements of the
    row.
    '''
    t_matrix = np.array(transition_matrix, dtype=np.float64)
    if reversible:
        t_matrix = t_matrix.T + t_matrix

    n_states = len(t_matrix)
    assert(n_states == len(t_matrix[0]))

    for i in range(n_states):
        if (t_matrix[i, :] < 0).any():
            raise ValueError('All the elements in the input \
            matrix must be non-negative')
        t_matrix[i, :] = normalize(t_matrix[i, :])
        # sum_ = sum(t_matrix[i,:])

        # if sum_ != 0.0:
        #     for j in range(n_states):
        #         t_matrix[i,j] = t_matrix[i,j]/sum_

    return t_matrix


def normalize(my_vector):
    '''Normalize a vector dividing each element by the total sum
    of all its elements
    '''
    my_vector = np.array(my_vector)
    size = len(my_vector)

    sum_ = sum(my_vector)
    if sum_ != 0.0:
        for i in range(size):
            my_vector[i] = my_vector[i] / sum_
    return my_vector


def random_markov_matrix(n_states=5, seed=None):
    '''Returns a random transition markov matrix
    '''
    if seed is not None:
        np.random.seed(seed)
    t_matrix = np.random.random((n_states, n_states))
    return normalize_markov_matrix(t_matrix)


def check_tmatrix(t_matrix, accept_null_rows=True):
    '''Check if the given matrix is actually a row-stockastic
    transition matrix, i.e, all the elements are non-negative and
    the rows add to one.
    If the keyword argunment accept_null_rows is True, is going
    to accept rows where all the elements are zero. Those "problematic"
    states are going to be removed later if necessary by clean_tmatrix.
    '''
    def value_error():
        raise ValueError("The object given is not a transition matrix")

    n_states = len(t_matrix)
    if not (n_states == len(t_matrix[0])):
        value_error()

    for index, row in enumerate(t_matrix):
        sum_ = 0.0
        for element in row:
            if element < 0.0:
                value_error()
            sum_ += element

        if accept_null_rows:
            if not (np.isclose(sum_, 1.0, atol=1e-6) or sum_ == 0.0):
                value_error()
        else:
            if not np.isclose(sum_, 1.0, atol=1e-6):
                value_error()

    return False


def clean_tmatrix(transition_matrix, rm_absorbing=True):
    '''Removes the states/indexes with no transitions and
    the states that are absorbing if the the keyword argument
    rm_absorbing is true

    Returns the "clean" transition matrix and a list with the
    removed states/indexes (clean_tmatrix, removed_states)
    '''
    t_matrix = deepcopy(transition_matrix)
    n_states = len(transition_matrix)

    # -------------------------------
    # Removing the non-visited states and absorbing states
    removed_states = []
    for index in range(n_states - 1, -1, -1):
        if not any(t_matrix[index]):  # non-visited
            t_matrix = np.delete(t_matrix, index, axis=1)
            t_matrix = np.delete(t_matrix, index, axis=0)
            removed_states.append(index)
        elif t_matrix[index, index] == 1.:  # absorbing state
            if not all([t_matrix[index, j] == 0.0 for j in range(n_states) if j != index]):
                raise ValueError(
                    'The sum of the elements in a row of the \
                    transition matrix must be one')
            t_matrix = np.delete(t_matrix, index, axis=1)
            t_matrix = np.delete(t_matrix, index, axis=0)
            removed_states.append(index)

    # Renormalizing just in case
    t_matrix = normalize_markov_matrix(t_matrix)

    return t_matrix, removed_states


def pops_from_tmatrix(transition_matrix):
    '''Returns the eigen values and eigen vectors of the transposed
    transition matrix

    input: ndarray with shape = (n_states, n_states)

    output: the solution, p, of K.T p = p where K.T is the transposed
    transition matrix
    '''

    check_tmatrix(transition_matrix)

    n_states = len(transition_matrix)

    # Cleanning the transition matrix
    cleaned_matrix, removed_states = clean_tmatrix(transition_matrix)

    # Computing
    eig_vals, eig_vecs = np.linalg.eig(cleaned_matrix.T)
    eig_vecs = eig_vecs.T  # for convinience, now every row is an eig_vector

    eig_vals_close_to_one = np.isclose(eig_vals, 1.0, atol=1e-6)
    real_eig_vecs = [not np.iscomplex(row).any() for row in eig_vecs]

    new_n_states = n_states - len(removed_states)

    ss_solution = np.zeros(new_n_states)  # steady-state solution
    for is_close_to_one, is_real, eigv in zip(eig_vals_close_to_one,
                                              real_eig_vecs, eig_vecs):
        if is_close_to_one and is_real and \
                num_of_nonzero_elements(eigv) > \
                num_of_nonzero_elements(ss_solution) and\
                ((eigv <= 0).all() or (eigv >= 0).all()):
            ss_solution = eigv

    if (ss_solution == 0.0).all():
        raise Exception('No steady-state solution found for \
        the given transition matrix')

    ss_solution = normalize(ss_solution).real

    # Now we have to insert back in the solution, the missing
    # elements with zero probabilities
    for index in sorted(removed_states):
        ss_solution = np.insert(ss_solution, index, 0.0)

    return ss_solution


def pops_from_nm_tmatrix(transition_matrix):
    '''Computes the populations of the real/physical states from a
    non-Markovian transtion matrix with shape (2*n_states, 2*n_states)
    '''
    check_tmatrix(transition_matrix, accept_null_rows=True)

    size = len(transition_matrix)

    if size % 2 != 0:
        raise ValueError("The non-Markovian transition matrix has to "
                         "have an even number of columns/rows")

    n_states = size // 2  # Real/physical microstates

    pops_nm = pops_from_tmatrix(transition_matrix)

    pops = np.zeros(n_states)

    for i in range(n_states):
        pops[i] = pops_nm[2 * i] + pops_nm[2 * i + 1]

    return pops


def pseudo_nm_tmatrix(markovian_tmatrix, stateA, stateB):
    '''Obtain a pseudo non-Markovian transition matrix from a Markovian
    transiton matrix. The pseudo Markovian matrix has a shape of
    (2 n_states, 2 n_states)
    '''

    check_tmatrix(markovian_tmatrix)
    n_states = len(markovian_tmatrix)

    # pseudo non-Markovian transition matrix
    p_nm_tmatrix = np.zeros((2 * n_states, 2 * n_states))

    for i in range(2 * n_states):
        for j in range(2 * n_states):
            p_nm_tmatrix[i, j] = markovian_tmatrix[i // 2, j // 2]

    for i in range(n_states):
        for j in range(n_states):
            if (i in stateB) or (j in stateB):
                p_nm_tmatrix[2 * i, 2 * j] = 0.0
            if (i in stateA) or (j in stateA):
                p_nm_tmatrix[2 * i + 1, 2 * j + 1] = 0.0
            if (not (j in stateA)) or (i in stateA):
                p_nm_tmatrix[2 * i + 1, 2 * j] = 0.0
            if (not (j in stateB)) or (i in stateB):
                p_nm_tmatrix[2 * i, 2 * j + 1] = 0.0

    check_tmatrix(p_nm_tmatrix)  # just in case
    return p_nm_tmatrix
