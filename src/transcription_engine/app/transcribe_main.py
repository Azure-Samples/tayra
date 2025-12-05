"""CLI entry point to execute the blob transcription pipeline without FastAPI."""

import argparse
import asyncio
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.append(str(PACKAGE_ROOT))

from app.schemas import TranscriptionJobParams
from app.transcribe import BlobTranscriptionProcessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the BlobTranscriptionProcessor against an Azure Storage container."
    )
    parser.add_argument(
        "--origin-container",
        default="audio-files",
        help="Source container that holds audio blobs (default: audio-files).",
    )
    parser.add_argument(
        "--destination-container",
        default="transcripts",
        help="Container where processed outputs/cached transcriptions live (default: transcripts).",
    )
    parser.add_argument(
        "--manager-name",
        default=None,
        help="Filter by manager folder inside the blob path.",
    )
    parser.add_argument(
        "--specialist-name",
        default=None,
        help="Filter by specialist folder inside the manager path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=-1,
        help="Max number of blobs to process before stopping (-1 = all).",
    )
    parser.add_argument(
        "--semaphores",
        type=int,
        default=10,
        help="Max concurrent speech requests (controls HTTP client semaphore).",
    )
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=50,
        help="Number of blobs to fetch per listing page (default: 50).",
    )
    parser.add_argument(
        "--only-failed",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Process only blobs flagged as failed in Cosmos (default: true).",
    )
    parser.add_argument(
        "--use-cache",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip blobs that already have a transcription in the destination container.",
    )
    parser.add_argument(
        "--run-evaluation-flow",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reserved flag to align with API schema; kept for parity.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    params = TranscriptionJobParams(
        origin_container=args.origin_container,
        destination_container=args.destination_container,
        manager_name=args.manager_name,
        specialist_name=args.specialist_name,
        limit=args.limit,
        only_failed=args.only_failed,
        use_cache=args.use_cache,
        run_evaluation_flow=args.run_evaluation_flow,
        semaphores=args.semaphores,
        results_per_page=args.results_per_page,
    )

    processor = BlobTranscriptionProcessor()
    asyncio.run(processor(params))


if __name__ == "__main__":
    main()
