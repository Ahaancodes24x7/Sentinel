"""Wraps sklearn CalibratedClassifierCV (Platt/sigmoid) around a base classifier. Exposes calibrate(base_model, X_train, y_train) -> calibrated_model."""

def calibrate(base_model, X_train, y_train):
    """Fit and return a calibrated classifier."""
    raise NotImplementedError