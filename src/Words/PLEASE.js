export const PLEASE = (ref) => {
    let animations = []

    animations.push(["mixamorigRightHandIndex1",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandIndex2",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandIndex3",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandMiddle1", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandMiddle2", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandMiddle3", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandRing1",   "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandRing2",   "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandRing3",   "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandPinky1",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandPinky2",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandPinky3",  "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHandThumb1",  "rotation", "y", 0, "-"]);
    animations.push(["mixamorigRightArm",         "rotation", "z", Math.PI/3,  "+"]);
    animations.push(["mixamorigRightArm",         "rotation", "y", -Math.PI/4, "-"]); // flipped inward
    animations.push(["mixamorigRightForeArm",     "rotation", "z", Math.PI/4,  "+"]);
    animations.push(["mixamorigRightHand",        "rotation", "x", Math.PI/6,  "+"]);
    animations.push(["mixamorigRightHand",        "rotation", "y", -Math.PI/4, "-"]); // flipped

    ref.animations.push(animations);

    animations = []
    animations.push(["mixamorigRightArm", "rotation", "z", Math.PI/2.5,  "+"]);
    animations.push(["mixamorigRightArm", "rotation", "y", -Math.PI/5,   "+"]);  // flipped
    ref.animations.push(animations);

    animations = []
    animations.push(["mixamorigRightArm", "rotation", "z", Math.PI/3,  "-"]);
    animations.push(["mixamorigRightArm", "rotation", "y", -Math.PI/3,  "-"]); // flipped
    ref.animations.push(animations);

    animations = []
    animations.push(["mixamorigRightArm", "rotation", "z", Math.PI/2.5, "+"]);
    animations.push(["mixamorigRightArm", "rotation", "y", -Math.PI/4,  "+"]);  // flipped
    ref.animations.push(animations);

    animations = []
    animations.push(["mixamorigRightArm",     "rotation", "z", Math.PI/3, "-"]);
    animations.push(["mixamorigRightArm",     "rotation", "y", 0, "+"]);  // flipped reset
    animations.push(["mixamorigRightForeArm", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightHand",    "rotation", "x", 0, "-"]);
    animations.push(["mixamorigRightHand",    "rotation", "y", 0, "+"]);  // flipped reset
    ref.animations.push(animations);

    if (ref.pending === false) { ref.pending = true; ref.animate(); }
}