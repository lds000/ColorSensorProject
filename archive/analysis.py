def calculate_wetness_percent(b):
    b_dry_min = 14
    b_wet_max = 21
    return max(0.0, min((b - b_dry_min) / (b_wet_max - b_dry_min), 1.0))
