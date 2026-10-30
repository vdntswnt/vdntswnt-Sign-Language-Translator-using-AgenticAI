export const NAMASTE = (ref) => {

    let animations = []

    // ── Phase 1: Both hands together in prayer at chest ───────────────────────
    animations.push(["mixamorigNeck",         "rotation", "x",  Math.PI/12,  "+"]);

    // Right arm — bring forearm inward toward center
    animations.push(["mixamorigRightArm",     "rotation", "z",  Math.PI/3,   "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "y", -Math.PI/2.2, "-"]);  // inverted
    animations.push(["mixamorigRightForeArm", "rotation", "z", -Math.PI/4,   "-"]);  // inverted
    animations.push(["mixamorigRightHand",    "rotation", "x", -Math.PI/8,   "-"]);  // inverted
    animations.push(["mixamorigRightHand",    "rotation", "y",  Math.PI/4,   "+"]);  // inverted

    // Left arm — mirror, bring forearm inward toward center
    animations.push(["mixamorigLeftArm",      "rotation", "z", -Math.PI/3,   "-"]);
    animations.push(["mixamorigLeftForeArm",  "rotation", "y",  Math.PI/2.2, "+"]);  // inverted
    animations.push(["mixamorigLeftForeArm",  "rotation", "z",  Math.PI/4,   "+"]);  // inverted
    animations.push(["mixamorigLeftHand",     "rotation", "x", -Math.PI/8,   "-"]);  // inverted
    animations.push(["mixamorigLeftHand",     "rotation", "y", -Math.PI/4,   "-"]);  // inverted

    // Both hands flat, fingers together pointing upward
    // Right fingers
    animations.push(["mixamorigRightHandIndex1",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z",  0, "+"]);
    animations.push(["mixamorigRightHandThumb1",  "rotation", "z",  Math.PI/6, "+"]);
    animations.push(["mixamorigRightHandThumb2",  "rotation", "z",  Math.PI/6, "+"]);

    // Left fingers
    animations.push(["mixamorigLeftHandIndex1",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandIndex2",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandIndex3",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandMiddle1", "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandMiddle2", "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandMiddle3", "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandRing1",   "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandRing2",   "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandRing3",   "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandPinky1",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandPinky2",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandPinky3",  "rotation", "z",  0, "-"]);
    animations.push(["mixamorigLeftHandThumb1",  "rotation", "z", -Math.PI/6, "-"]);
    animations.push(["mixamorigLeftHandThumb2",  "rotation", "z", -Math.PI/6, "-"]);

    ref.animations.push(animations);

    // ── Phase 3: Return to default ────────────────────────────────────────────
    animations = []

    animations.push(["mixamorigRightForeArm", "rotation", "y", -Math.PI/1.5, "+"]);  // inverted
    animations.push(["mixamorigRightForeArm", "rotation", "z",  0,           "+"]);  // inverted
    animations.push(["mixamorigRightHand",    "rotation", "x",  0,           "+"]);  // inverted
    animations.push(["mixamorigRightHand",    "rotation", "y",  0,           "-"]);  // inverted
    animations.push(["mixamorigRightHandThumb1", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandThumb2", "rotation", "z", 0, "-"]);

    animations.push(["mixamorigLeftForeArm",  "rotation", "y",  Math.PI/1.5, "-"]);  // inverted
    animations.push(["mixamorigLeftForeArm",  "rotation", "z",  0,           "-"]);  // inverted
    animations.push(["mixamorigLeftHand",     "rotation", "x",  0,           "+"]);  // inverted
    animations.push(["mixamorigLeftHand",     "rotation", "y",  0,           "+"]);  // inverted
    animations.push(["mixamorigLeftHandThumb1", "rotation", "z", 0, "+"]);
    animations.push(["mixamorigLeftHandThumb2", "rotation", "z", 0, "+"]);

    ref.animations.push(animations);

    if (ref.pending === false) {
        ref.pending = true;
        ref.animate();
    }

}