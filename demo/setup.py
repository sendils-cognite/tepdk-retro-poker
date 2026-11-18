#!/usr/bin/env python3
"""Open a TEPDK retro room, submit five random responses, and finish polling."""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

NAMES: list[str] = ["Amina", "Lars", "Priya", "Chen", "Sofia"]
STATEMENT_COUNT = 10
ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_ID_LENGTH = 6
IMPROVEMENTS: list[str] = [
    "- Clearer ownership on blocked work\n- Weekly demo of pipeline status",
    "- Faster answers from Cognite SMEs\n- Written definition of done",
    "- More reusable templates\n- Less rework between milestones",
    "- Shared runbooks for Toolkit deploy\n- Earlier technical review",
    "- Better handoff notes\n- Room to fix quality before go-live",
]


def make_room_id(length: int = ROOM_ID_LENGTH) -> str:
    return "".join(ROOM_ALPHABET[byte % len(ROOM_ALPHABET)] for byte in os.urandom(length))


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://sendils-cognite.github.io/tepdk-retro-poker").rstrip("/")
    room = make_room_id()
    host_id = str(uuid.uuid4())
    clock = time.time()

    def stamp(op: dict[str, object]) -> dict[str, object]:
        nonlocal clock
        clock += 0.01
        op["at"] = clock
        return op

    def publish(op: dict[str, object]) -> None:
        request = urllib.request.Request(
            f"https://ntfy.sh/{room}",
            data=json.dumps(op).encode(),
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        for attempt in range(6):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 5:
                    raise
                retry_after = error.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2 * (attempt + 1))
        time.sleep(0.35)

    used: set[str] = set()

    def random_answers() -> str:
        while True:
            pattern = "".join(random.choice("TF") for _ in range(STATEMENT_COUNT))
            if pattern not in used:
                used.add(pattern)
                return pattern

    people = [
        (str(uuid.uuid4()), name, random_answers(), IMPROVEMENTS[index % len(IMPROVEMENTS)])
        for index, name in enumerate(NAMES)
    ]
    setup_ops = [stamp({"t": "create", "id": host_id, "name": "Survey Admin", "template": "tepdk-retro"})]
    setup_ops += [stamp({"t": "join", "id": user_id, "name": name}) for user_id, name, _pattern, _note in people]
    setup_ops.append(stamp({"t": "phase", "phase": "open", "id": host_id}))
    publish(stamp({"t": "batch", "ops": setup_ops}))
    print("Room created and polling started")

    for user_id, name, pattern, note in people:
        answer_ops: list[dict[str, object]] = []
        upvote_indexes = set(random.sample(range(STATEMENT_COUNT), k=random.randint(1, 3)))
        for index, mark in enumerate(pattern):
            answer_ops.append(
                stamp({"t": "vote", "id": user_id, "i": index, "value": "True" if mark == "T" else "False"})
            )
            if index in upvote_indexes:
                answer_ops.append(stamp({"t": "upvote", "id": user_id, "i": index, "value": True}))
        answer_ops.append(stamp({"t": "improve", "id": user_id, "text": note}))
        answer_ops.append(stamp({"t": "submit", "id": user_id}))
        publish(stamp({"t": "batch", "ops": answer_ops}))
        print(f"{name} submitted")

    publish(stamp({"t": "phase", "phase": "closed", "id": host_id}))
    print("Polling finished")

    invite = f"{base}/?room={room}"
    host = f"{invite}&host={host_id}"
    print(f"Room {room}")
    print("Five participants submitted random answers, upvotes, and improvement notes:")
    for _user_id, name, pattern, _note in people:
        print(f"  {name}: {pattern.count('T')} true, {pattern.count('F')} false")
    print(f"Host dashboard: {host}")
    print(f"Invite link: {invite}")


if __name__ == "__main__":
    main()
