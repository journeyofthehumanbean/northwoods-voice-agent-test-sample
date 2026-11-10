# Northwoods voice-agent test sample

A small, offline harness that replays scripted call fixtures against a
fictional Example Plumbing Co booking flow and checks booking-safety rules.

This is a public code sample for Nick Schmitz / Northwoods. It is not a
live call tester and it does not talk to any voice, calendar, or
automation product.

## What it checks

- The agent never confirms a booking unless the booking tool returned success.
- A repeated call with the same phone, service, and slot does not create a second booking.
- A caller who declines is not booked.
- SMS is sent only after the caller gives explicit consent.

## What's in here

- `flows/example_plumbing_co.json` — fictional sample flow (not a real client).
- `harness/` — mock booking tool plus fixture replay and policy checks.
- `fixtures/calls.json` — scripted calls, including cases that should be flagged.
- `examples/make_webhook_payload.json` — example payload a scenario tool might receive. Fake data only; no endpoint URL.
- `tests/` — unittest coverage of the rules above.

## How to run

From this directory, with Python 3.10+ (standard library only):

```bash
python3 -m unittest discover -s tests -v
```

or `python3 run_tests.py`.

## Honest limits

- Offline fixtures only. This does not place a real call, score live audio, or prove how a production agent will behave.
- The booking tool and webhook example are in-memory mocks with obviously fake data (555-01xx numbers, example.com).
- The flow is invented for this sample. It is not copied from a production agent.
- Passing tests means the harness enforces the rules on these scripts, not that a production integration is certified.

## Contact

Nick Schmitz, Northwoods, northwoodscallcompany.com
