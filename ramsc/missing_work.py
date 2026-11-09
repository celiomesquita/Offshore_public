"""Conditional box bounds for paired coverage of fixed priority selections."""
import numpy as np


def unbounded_paired_coverage(observed, missing_count, selection_difference):
    """Infimum/supremum for non-negative unknown work without a finite cap.

    The ratio is a weighted mean of the observed difference and selection
    differences of systems with missing events. Extreme limits need not be attained.
    """
    observed, count, d = [np.asarray(x, dtype=float) for x in
                          (observed, missing_count, selection_difference)]
    if observed.sum() <= 0 or (count < 0).any():
        raise ValueError('positive observed work and non-negative counts required')
    point = np.dot(d, observed)/observed.sum()
    possible = np.r_[point, d[count > 0]]
    return float(possible.min()), float(possible.max())


def paired_coverage_bounds(observed, upper, selection_difference):
    """Bound d.(observed+x)/sum(observed+x), 0<=x<=upper; not confidence limits."""
    observed, upper, d = [np.asarray(x, dtype=float) for x in
                          (observed, upper, selection_difference)]
    if not (observed.shape == upper.shape == d.shape) or observed.ndim != 1:
        raise ValueError('inputs must have the same one-dimensional shape')
    if not all(np.isfinite(x).all() for x in (observed, upper, d)):
        raise ValueError('inputs must be finite')
    if (observed < 0).any() or (upper < 0).any() or observed.sum() <= 0:
        raise ValueError('non-negative work and a positive observed denominator required')
    numerator, denominator = np.dot(d, observed), observed.sum()
    bounds = []
    for minimise in (True, False):
        lo, hi = float(d.min()), float(d.max())
        for _ in range(70):
            mid = (lo+hi)/2
            terms = (d-mid)*upper
            residual = numerator-mid*denominator + (
                np.minimum(terms, 0).sum() if minimise else np.maximum(terms, 0).sum())
            if residual > 0:
                lo = mid
            else:
                hi = mid
        bounds.append((lo+hi)/2)
    return tuple(bounds)
