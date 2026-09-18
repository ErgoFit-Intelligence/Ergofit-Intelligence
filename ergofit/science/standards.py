from __future__ import annotations

# These are screening/design references, not product-certification logic.
# Full EN/ISO conformity requires the official standards and their complete test methods.

CHAIR_FIT_ITEMS = [
    ("seat_height_adjustable", "Seat height is adjustable and can be set so feet are supported and thighs are comfortable."),
    ("seat_depth_fit", "Seat depth allows clearance behind the knees while supporting most of the thighs."),
    ("backrest_support", "Backrest supports the trunk and lumbar region without forcing a fixed posture."),
    ("backrest_adjustable", "Backrest/recline can be adjusted to the user and task."),
    ("armrests_fit", "Armrests support the forearms without elevating the shoulders or forcing the elbows away from the body."),
    ("armrests_clear_desk", "Armrests do not prevent the user from approaching the work surface."),
    ("seat_width_fit", "Seat width provides adequate hip clearance."),
    ("stable_base", "Chair is stable and appropriate for the floor/caster condition."),
    ("controls_usable", "Adjustment controls are understandable and reachable from the seated position."),
]

# Corrected published Type-A dimensions noted during the 2026 audit.
# Kept for reference display only; not used to award a compliance score.
EN1335_TYPE_A_REFERENCE = {
    "seat_height_mm": "400–520",
    "seat_depth_adjustable_mm": "425–450 (with ≥70 mm adjustment travel)",
    "seat_pad_width_mm": "≥400",
    "armrest_height_mm": "200–290 (with ≥100 mm adjustment range)",
    "hip_clearance_mm": "≥480",
}

MONITOR_DISTANCE_REFERENCE_CM = (50, 100)

POSTURE_REFERENCES = [
    # These are reference observations, not a validated aggregate score.
    ("trunk_inclination", "Trunk inclination from vertical", 0, 20, 10),
    ("hip_angle", "Trunk–thigh / hip angle", 90, 110, 100),
    ("knee_angle", "Thigh–shin / knee angle", 90, 120, 100),
    ("ankle_angle", "Shin–foot / ankle angle", 90, 110, 100),
    ("shoulder_abduction", "Shoulder abduction", 0, 30, 10),
    ("shoulder_flexion", "Shoulder flexion", 0, 35, 15),
    ("elbow_angle", "Elbow angle", 90, 120, 100),
    ("wrist_flex_ext", "Wrist flexion/extension", -15, 15, 0),
    ("wrist_deviation", "Wrist radial/ulnar deviation", -10, 15, 0),
]


# Greek display labels. Internal keys and numeric references remain language-neutral.
CHAIR_FIT_LABELS_EL = {
    "seat_height_adjustable": "Το ύψος της έδρας ρυθμίζεται ώστε τα πέλματα να στηρίζονται και οι μηροί να είναι άνετοι.",
    "seat_depth_fit": "Το βάθος της έδρας αφήνει επαρκές κενό πίσω από τα γόνατα και στηρίζει το μεγαλύτερο μέρος των μηρών.",
    "backrest_support": "Η πλάτη της καρέκλας στηρίζει τον κορμό και την οσφυϊκή περιοχή χωρίς να επιβάλλει στατική στάση.",
    "backrest_adjustable": "Η κλίση/θέση της πλάτης ρυθμίζεται ανάλογα με τον χρήστη και την εργασία.",
    "armrests_fit": "Τα μπράτσα στηρίζουν τα αντιβράχια χωρίς να ανυψώνουν τους ώμους ή να απομακρύνουν τους αγκώνες από το σώμα.",
    "armrests_clear_desk": "Τα μπράτσα δεν εμποδίζουν τον εργαζόμενο να πλησιάσει την επιφάνεια εργασίας.",
    "seat_width_fit": "Το πλάτος της έδρας παρέχει επαρκή χώρο για τη λεκάνη.",
    "stable_base": "Η καρέκλα είναι σταθερή και κατάλληλη για το δάπεδο και τους τροχούς της.",
    "controls_usable": "Οι μηχανισμοί ρύθμισης είναι κατανοητοί και προσβάσιμοι από καθιστή θέση.",
}

POSTURE_LABELS_EL = {
    "trunk_inclination": "Κλίση κορμού από την κατακόρυφο",
    "hip_angle": "Γωνία κορμού–μηρού / ισχίου",
    "knee_angle": "Γωνία μηρού–κνήμης / γόνατος",
    "ankle_angle": "Γωνία κνήμης–πέλματος / ποδοκνημικής",
    "shoulder_abduction": "Απαγωγή ώμου",
    "shoulder_flexion": "Κάμψη ώμου",
    "elbow_angle": "Γωνία αγκώνα",
    "wrist_flex_ext": "Κάμψη/έκταση καρπού",
    "wrist_deviation": "Κερκιδική/ωλένια απόκλιση καρπού",
}

EN1335_LABELS_EL = {
    "seat_height_mm": "Ύψος έδρας",
    "seat_depth_adjustable_mm": "Ρυθμιζόμενο βάθος έδρας",
    "seat_pad_width_mm": "Πλάτος έδρας",
    "armrest_height_mm": "Ύψος μπράτσων",
    "hip_clearance_mm": "Ελεύθερος χώρος λεκάνης",
}
