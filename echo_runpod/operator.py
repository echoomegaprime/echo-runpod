"""CLI / Nexus entry — observe by default, mutate only when policy allows."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from echo_runpod import __version__
from echo_runpod.client import RunPodClient, RunPodError, idempotency_digest
from echo_runpod.governor import check_cost, idle_paid_resources
from echo_runpod.isolation import isolate
from echo_runpod.manifests import ManifestError, landman_example, validate_manifest
from echo_runpod.policy import evaluate_action
from echo_runpod.redaction import redact
from echo_runpod.router import route_prompt
from echo_runpod.secrets import SecretBroker, SecretError

_IDEMPOTENCY: dict[str, Any] = {}


def _out(payload: Any, code: int = 0) -> int:
    print(json.dumps(redact(payload), indent=2, default=str))
    return code


def cmd_route(args: argparse.Namespace) -> int:
    route = route_prompt(args.prompt)
    return _out(
        {
            "lane": route.lane,
            "mutation": route.mutation,
            "requires_approval": route.requires_approval,
            "reason": route.reason,
            "references": list(route.references),
        }
    )


def cmd_policy(args: argparse.Namespace) -> int:
    request = json.loads(args.request) if args.request else {}
    lane = json.loads(args.full_lane) if args.full_lane else None
    manifest = json.loads(args.approved_manifest) if args.approved_manifest else None
    decision = evaluate_action(
        args.action,
        confirm=args.confirm,
        approved_manifest=manifest,
        full_lane=lane,
        request=request,
    )
    return _out(decision.to_dict(), 0 if decision.allowed else 2)


def cmd_prepare(args: argparse.Namespace) -> int:
    raw = json.loads(args.manifest)
    try:
        man = validate_manifest(raw)
    except ManifestError as exc:
        return _out({"ok": False, "error": str(exc)}, 2)
    return _out(
        {
            "ok": True,
            "status": "prepared",
            "execution": "waits_for_approval_unless_full_lane",
            "manifest": man.to_dict(),
        }
    )


def cmd_isolate(args: argparse.Namespace) -> int:
    target = json.loads(args.target) if args.target else None
    decision = isolate(
        request_workload_id=args.workload_id,
        request_project=args.project,
        request_dataset_sha=args.dataset_sha256,
        request_model=args.model,
        target=target,
    )
    return _out({"allowed": decision.allowed, "reason": decision.reason}, 0 if decision.allowed else 2)


def cmd_cost(args: argparse.Namespace) -> int:
    check = check_cost(
        live_hourly=args.live_hourly,
        estimated_runtime_hours=args.hours,
        max_hourly_rate=args.max_hourly,
        max_total_budget=args.max_budget,
        accumulated=args.accumulated or 0.0,
        approved_gpu_classes=args.allowed_gpu.split(",") if args.allowed_gpu else None,
        requested_gpu=args.gpu,
        approved_gpu_count=args.max_gpu_count,
        requested_gpu_count=args.gpu_count,
    )
    return _out(
        {
            "allowed": check.allowed,
            "reason": check.reason,
            "estimated_hourly": check.estimated_hourly,
            "estimated_total": check.estimated_total,
            "remaining_budget": check.remaining_budget,
        },
        0 if check.allowed else 2,
    )


def cmd_idempotent(args: argparse.Namespace) -> int:
    request = json.loads(args.request)
    digest = idempotency_digest(args.action, request)
    key = args.key or digest
    if key in _IDEMPOTENCY:
        return _out({"replay": True, "digest": digest, "result": _IDEMPOTENCY[key]})
    result = {"logical_operation": args.action, "digest": digest, "spent": False}
    _IDEMPOTENCY[key] = result
    return _out({"replay": False, "digest": digest, "result": result})


def _live_client() -> RunPodClient:
    return RunPodClient(SecretBroker())


def cmd_live(args: argparse.Namespace) -> int:
    action = args.action
    decision = evaluate_action(action, confirm=args.confirm)
    if not decision.allowed:
        return _out({"ok": False, "policy": decision.to_dict()}, 2)
    try:
        client = _live_client()
        if action == "runpod_list_pods":
            data = client.list_pods()
        elif action == "runpod_get_pod":
            data = client.get_pod(args.pod_id)
        elif action == "runpod_list_gpu_types":
            data = client.list_gpu_types()
        elif action == "runpod_billing":
            data = client.billing()
        elif action == "runpod_status":
            pods = client.list_pods()
            auth = client.broker.status()
            idle = idle_paid_resources(pods if isinstance(pods, list) else pods.get("pods") or [])
            data = {
                "auth": {"source": auth.source, "reference": auth.reference, "present": auth.present},
                "pod_count": len(pods) if isinstance(pods, list) else None,
                "idle_paid_resources": idle,
            }
        else:
            return _out({"ok": False, "error": "live action not implemented in observe client"}, 2)
        return _out({"ok": True, "action": action, "data": data})
    except SecretError as exc:
        return _out({"ok": False, "error": str(exc), "auth": "missing"}, 3)
    except RunPodError as exc:
        return _out({"ok": False, "error": str(exc), "status": exc.status, "payload": exc.payload}, 4)


def cmd_example(_args: argparse.Namespace) -> int:
    return _out(landman_example())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="echo-runpod")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("route")
    r.add_argument("prompt")
    r.set_defaults(func=cmd_route)

    pol = sub.add_parser("policy")
    pol.add_argument("action")
    pol.add_argument("--confirm")
    pol.add_argument("--request")
    pol.add_argument("--full-lane")
    pol.add_argument("--approved-manifest")
    pol.set_defaults(func=cmd_policy)

    prep = sub.add_parser("prepare")
    prep.add_argument("manifest")
    prep.set_defaults(func=cmd_prepare)

    iso = sub.add_parser("isolate")
    iso.add_argument("--workload-id", required=True)
    iso.add_argument("--project", required=True)
    iso.add_argument("--dataset-sha256")
    iso.add_argument("--model")
    iso.add_argument("--target")
    iso.set_defaults(func=cmd_isolate)

    cost = sub.add_parser("cost")
    cost.add_argument("--live-hourly", type=float)
    cost.add_argument("--hours", type=float)
    cost.add_argument("--max-hourly", type=float)
    cost.add_argument("--max-budget", type=float)
    cost.add_argument("--accumulated", type=float, default=0.0)
    cost.add_argument("--gpu")
    cost.add_argument("--allowed-gpu")
    cost.add_argument("--gpu-count", type=int)
    cost.add_argument("--max-gpu-count", type=int)
    cost.set_defaults(func=cmd_cost)

    idem = sub.add_parser("idempotent")
    idem.add_argument("action")
    idem.add_argument("request")
    idem.add_argument("--key")
    idem.set_defaults(func=cmd_idempotent)

    live = sub.add_parser("live")
    live.add_argument("action")
    live.add_argument("--confirm")
    live.add_argument("--pod-id")
    live.set_defaults(func=cmd_live)

    ex = sub.add_parser("landman-example")
    ex.set_defaults(func=cmd_example)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
