from numpy import *


def sliding_window_apply(fun, xs, ys, window_size, mesh=None, n_points=None):
    ''' Apply `fun` to the values in `ys`, by sliding a window_size
        of size `window_size` over the points in mesh, collecting
        up those entries in `xs` that are within `window_size` of
        each point in `mesh`, and passing their corresponding `ys`
        values to `fun`.
    '''

    if mesh is None and n_points is None:
        raise ValueError('Either mesh or n_points must be specified')

    # figure out dimensionality of xs
    if getattr(xs[0], '__iter__', False):
        ndims = len(xs[0])  # woe to you if the dimensionality is not regular
    else:
        ndims = 1

    # Do the actual real work
    if ndims == 1:
        return sliding_window_apply_1D(fun, xs, ys, window_size, mesh, n_points)

    if ndims == 2:
        return sliding_window_apply_2D(fun, xs, ys, window_size, mesh, n_points)

    raise ValueError('Meshes of more than 2 dimensions are not yet supported')


def sliding_window_apply_1D(fun, xs, ys, window_size, mesh=None, n_points=None):

    if mesh is None and n_points is None:
        raise ValueError('Either mesh or n_points must be specified')

    if mesh is None:
        mesh = linspace(min(xs), max(xs), n_points)

    output = []

    for m in mesh:
        vals = []
        for (x, y) in zip(xs, ys):
            if abs(m - x) < (window_size / 2.):
                vals.append(y)

        output.append(fun(vals))

    return output


def sliding_window_apply_2D(fun, xs, ys, window_size, mesh=None, n_points=None):

    if mesh is None and n_points is None:
        raise ValueError('Either mesh or n_points must be specified')

    if mesh is None:
        arr_xs = array(xs)
        mesh = meshgrid(linspace(min(arr_xs[:, 0]), max(arr_xs[:, 0]), n_points[0]),
                        linspace(min(arr_xs[:, 1]), max(arr_xs[:, 1]), n_points[1]))

    M1, M2 = mesh

    def apply_window_fun_at_pt(m1, m2):
        ' Return a list of y-vals within window_size of m1,m2'

        y_vals = []

        for pt, y in zip(xs, ys):
            if linalg.norm(array([m1, m2] - array(pt))) < (window_size / 2.):
                y_vals.append(y)

        return fun(y_vals)

    v_apply = vectorize(apply_window_fun_at_pt)

    return v_apply(M1, M2)


def test_sliding_window():

    from nose.tools import assert_equal
    from numpy.testing import assert_almost_equal

    xs = [1, 2, 5, 6, 10]
    ys = [1, 1, 1, 1, 1]

    res = sliding_window_apply(sum, xs, ys, 1.0, n_points=10)

    assert_equal(res, [1, 1, 0, 0, 1, 1, 0, 0, 0, 1])

    xs = [1, 1.25, 3, 5, 5.25]
    ys = [1, 2, 1, 1, 1]

    res = sliding_window_apply(sum, xs, ys, 1.0, n_points=5)

    assert_equal(res, [3, 0, 1, 0, 2])

    xs = [(1, 1), (2, 2), (3, 3)]
    ys = [1, 1, 1]

    res = sliding_window_apply(sum, xs, ys, 1.0, n_points=(3, 3))

    assert_almost_equal(array(res), array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))

    # more tests than this are needed!

