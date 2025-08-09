import argparse
from . import youtube_module, arxiv_module
from .logger import get_logger

logger = get_logger()

def main():
    parser = argparse.ArgumentParser(description="Wizards Toolkit - Opportunity Brief Generator")
    parser.add_argument("--topic", required=True, help="Research topic")
    parser.add_argument(
        "--source",
        choices=["youtube", "arxiv", "both"],
        default="both",
        help="Data source to use",
    )
    args = parser.parse_args()

    logger.info(f"Starting research for topic: {args.topic}")

    if args.source in ("youtube", "both"):
        youtube_module.fetch_and_analyze_youtube(args.topic)

    if args.source in ("arxiv", "both"):
        arxiv_module.fetch_and_analyze_arxiv(args.topic)

if __name__ == "__main__":
    main()
