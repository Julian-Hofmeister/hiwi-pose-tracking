import threading
import time

from rtmpose_ros.frame_slot import LatestFrameSlot


def test_latest_frame_wins_drops_unread_items() -> None:
    slot: LatestFrameSlot[int] = LatestFrameSlot()
    slot.put(1)
    slot.put(2)
    slot.put(3)

    assert slot.dropped == 2
    assert slot.take(timeout=0.1) == 3
    assert slot.take(timeout=0.05) is None
    assert slot.dropped == 2


def test_take_waits_until_put() -> None:
    slot: LatestFrameSlot[str] = LatestFrameSlot()
    result: list[str] = []

    def consume() -> None:
        item = slot.take(timeout=1.0)
        if item is not None:
            result.append(item)

    worker = threading.Thread(target=consume)
    worker.start()
    time.sleep(0.05)
    slot.put('latest')
    worker.join(timeout=1.0)

    assert result == ['latest']
    assert slot.dropped == 0
