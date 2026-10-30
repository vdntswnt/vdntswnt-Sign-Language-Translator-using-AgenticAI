export const ME = (ref) => {

    let animations = []

    // ── Phase 1: Right index up, ALL others closed including thumb ────────────
    // Index straight
    animations.push(["mixamorigRightHandIndex1",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z",  0,           "-"]);

    // All other fingers curled shut
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z",  Math.PI/2,   "+"]);

    // Thumb fully closed into fist
    animations.push(["mixamorigRightHandThumb1",  "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandThumb2",  "rotation", "z",  Math.PI/2,   "+"]);
    animations.push(["mixamorigRightHandThumb3",  "rotation", "z",  Math.PI/2,   "+"]);

    // Arm position — index points toward chest (negative y = inward)
    animations.push(["mixamorigRightArm",     "rotation", "z",  Math.PI/3.5,  "+"]);
    animations.push(["mixamorigRightArm",     "rotation", "y",  Math.PI/4,    "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "z",  Math.PI/12,   "+"]);

    // Hand rotated so index points at own chest
    animations.push(["mixamorigRightHand",    "rotation", "x",  Math.PI/6,    "+"]);
    animations.push(["mixamorigRightHand",    "rotation", "y",  Math.PI/6,    "+"]);

    ref.animations.push(animations);

    // ── Phase 2: Tap inward — arm moves toward chest ──────────────────────────
    animations = []

    animations.push(["mixamorigRightArm",     "rotation", "y",  Math.PI/3,   "+"]);

    ref.animations.push(animations);

    // ── Phase 3: Tap back out ─────────────────────────────────────────────────
    animations = []

    animations.push(["mixamorigRightArm",     "rotation", "y",  Math.PI/4,   "-"]);

    ref.animations.push(animations);

    // ── Phase 4: Return to default pose ──────────────────────────────────────
    animations = []

    animations.push(["mixamorigRightHandIndex1",  "rotation", "z",  0,           "+"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z",  0,           "+"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z",  0,           "+"]);
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandThumb1",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandThumb2",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigRightHandThumb3",  "rotation", "z",  0,           "-"]);

    animations.push(["mixamorigRightArm",     "rotation", "z",  Math.PI/3,    "-"]);
    animations.push(["mixamorigRightArm",     "rotation", "y",  0,            "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "z",  0,            "-"]);
    animations.push(["mixamorigRightHand",    "rotation", "x",  0,            "-"]);
    animations.push(["mixamorigRightHand",    "rotation", "y",  0,            "-"]);

    ref.animations.push(animations);

    if (ref.pending === false) {
        ref.pending = true;
        ref.animate();
    }

}