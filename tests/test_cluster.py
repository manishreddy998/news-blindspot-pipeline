import numpy as np

from blindspot.stories.cluster import cluster

HEADS = [
    "Trump cancels livestream of fort hood shooter execution",
    "Fort hood shooter execution livestream cancelled by trump",
    "Trump scraps fort hood execution livestream",
    "Meghan markle nottingham visit with prince harry",
    "Prince harry and meghan markle visit nottingham",
    "Oregon elementary school shooting leaves children dead",
]


def test_similar_headlines_share_a_story_and_others_dont():
    labels, centres = cluster(HEADS, np.zeros(len(HEADS)), sim_min=0.2)
    assert labels[0] == labels[1] == labels[2]
    assert labels[3] == labels[4]
    assert len({labels[0], labels[3], labels[5]}) == 3
    assert len(centres) == len(set(labels))


def test_time_window_splits_far_apart_headlines():
    hours = np.array([0, 0, 100, 0, 0, 0], dtype=float)
    labels, _ = cluster(HEADS, hours, sim_min=0.2, window_hours=36)
    assert labels[0] == labels[1] and labels[2] != labels[0]
