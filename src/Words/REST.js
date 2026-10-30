export const REST = (ref) => {

    let animations = []

    // ── Phase 1: Default pose arms + curl all fingers except index ────────────
    // Arms exactly as defaultPose.js
    animations.push(["mixamorigNeck",        "rotation", "x",  Math.PI/12,  "+"]);
    animations.push(["mixamorigLeftArm",     "rotation", "z", -Math.PI/3,   "-"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "y", -Math.PI/1.5, "-"]);
    animations.push(["mixamorigRightArm",    "rotation", "z",  Math.PI/3,   "+"]);
    animations.push(["mixamorigRightForeArm","rotation", "y",  Math.PI/1.5, "+"]);

    // Right hand — index finger straight up, rest curled
    animations.push(["mixamorigRightHandIndex1",  "rotation", "z",  0,          "+"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z",  0,          "+"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z",  0,          "+"]);
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z",  Math.PI/2,  "+"]);
    animations.push(["mixamorigRightHandThumb1",  "rotation", "z",  Math.PI/4,  "+"]);
    animations.push(["mixamorigRightHandThumb2",  "rotation", "z",  Math.PI/4,  "+"]);

    // Left hand — index finger straight up, rest curled (mirror z sign)
    animations.push(["mixamorigLeftHandIndex1",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigLeftHandIndex2",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigLeftHandIndex3",  "rotation", "z",  0,           "-"]);
    animations.push(["mixamorigLeftHandMiddle1", "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandMiddle2", "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandMiddle3", "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandRing1",   "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandRing2",   "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandRing3",   "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandPinky1",  "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandPinky2",  "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandPinky3",  "rotation", "z", -Math.PI/2,   "-"]);
    animations.push(["mixamorigLeftHandThumb1",  "rotation", "z", -Math.PI/4,   "-"]);
    animations.push(["mixamorigLeftHandThumb2",  "rotation", "z", -Math.PI/4,   "-"]);

    ref.animations.push(animations);

    // ── Phase 2: Return fingers to open (return to default) ───────────────────
    animations = []

    animations.push(["mixamorigRightHandIndex1",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandThumb1",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigRightHandThumb2",  "rotation", "z",  0,  "-"]);

    animations.push(["mixamorigLeftHandIndex1",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigLeftHandIndex2",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigLeftHandIndex3",  "rotation", "z",  0,  "-"]);
    animations.push(["mixamorigLeftHandMiddle1", "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandMiddle2", "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandMiddle3", "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandRing1",   "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandRing2",   "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandRing3",   "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandPinky1",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandPinky2",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandPinky3",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandThumb1",  "rotation", "z",  0,  "+"]);
    animations.push(["mixamorigLeftHandThumb2",  "rotation", "z",  0,  "+"]);

    ref.animations.push(animations);

    if (ref.pending === false) {
        ref.pending = true;
        ref.animate();
    }

}