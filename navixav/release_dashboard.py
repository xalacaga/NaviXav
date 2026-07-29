"""Tableau de bord d'administration local des Releases GitHub."""

from __future__ import annotations

import argparse
import html
import re
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from navixav.paths import user_data_path
from navixav.updater import GITHUB_REPOSITORY, REQUEST_HEADERS

REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$"
)
RELEASES_PER_PAGE = 100
MAX_RELEASE_PAGES = 10


class ReleaseDashboardError(RuntimeError):
    """Erreur contrôlée pendant la lecture des statistiques publiques."""


@dataclass(frozen=True)
class AssetDownloads:
    name: str
    downloads: int
    kind: str
    url: str


@dataclass(frozen=True)
class ReleaseDownloads:
    tag: str
    name: str
    published_at: str
    prerelease: bool
    url: str
    assets: tuple[AssetDownloads, ...]

    @property
    def installer_downloads(self) -> int:
        return sum(asset.downloads for asset in self.assets if asset.kind == "installer")

    @property
    def portable_downloads(self) -> int:
        return sum(asset.downloads for asset in self.assets if asset.kind == "portable")

    @property
    def total_downloads(self) -> int:
        return sum(asset.downloads for asset in self.assets)


def _asset_kind(name: str) -> str | None:
    lowered = name.lower()
    if lowered.endswith(".sha256"):
        return None
    if lowered.endswith(".exe"):
        return "installer"
    if lowered.endswith(".zip"):
        return "portable"
    return None


def _downloads(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _parse_release(payload: dict[str, Any]) -> ReleaseDownloads:
    assets: list[AssetDownloads] = []
    for raw in payload.get("assets") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        kind = _asset_kind(name)
        if not name or kind is None:
            continue
        assets.append(
            AssetDownloads(
                name=name,
                downloads=_downloads(raw.get("download_count")),
                kind=kind,
                url=str(raw.get("browser_download_url") or ""),
            )
        )
    return ReleaseDownloads(
        tag=str(payload.get("tag_name") or "sans version"),
        name=str(payload.get("name") or payload.get("tag_name") or "Release"),
        published_at=str(payload.get("published_at") or ""),
        prerelease=bool(payload.get("prerelease")),
        url=str(payload.get("html_url") or ""),
        assets=tuple(assets),
    )


def fetch_release_downloads(
    repository: str = GITHUB_REPOSITORY,
    *,
    session: requests.Session | None = None,
) -> list[ReleaseDownloads]:
    """Lit les compteurs publics GitHub, sans cookie ni identifiant utilisateur."""
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ReleaseDashboardError("Nom de dépôt GitHub invalide.")
    client = session or requests.Session()
    headers = {**REQUEST_HEADERS, "User-Agent": "NaviXav-Release-Dashboard"}
    releases: list[ReleaseDownloads] = []
    url = f"https://api.github.com/repos/{repository}/releases"

    for page in range(1, MAX_RELEASE_PAGES + 1):
        try:
            response = client.get(
                url,
                headers=headers,
                params={"per_page": RELEASES_PER_PAGE, "page": page},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ReleaseDashboardError(
                "Impossible de lire les Releases GitHub."
            ) from exc
        if not isinstance(payload, list):
            raise ReleaseDashboardError("Réponse GitHub invalide.")
        releases.extend(
            _parse_release(item) for item in payload if isinstance(item, dict)
        )
        if len(payload) < RELEASES_PER_PAGE:
            break
    return releases


def _format_date(value: str) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.astimezone().strftime("%d/%m/%Y")


def _metric(label: str, value: int, note: str) -> str:
    formatted = f"{value:,}".replace(",", " ")
    return "".join(
        (
            '<article class="metric">',
            f"<span>{html.escape(label)}</span>",
            f"<strong>{formatted}</strong>",
            f"<small>{html.escape(note)}</small>",
            "</article>",
        )
    )


def render_dashboard(
    releases: list[ReleaseDownloads],
    repository: str = GITHUB_REPOSITORY,
    *,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    installer_total = sum(release.installer_downloads for release in releases)
    portable_total = sum(release.portable_downloads for release in releases)
    grand_total = installer_total + portable_total
    latest_total = releases[0].total_downloads if releases else 0
    maximum = max((release.total_downloads for release in releases), default=1)

    rows: list[str] = []
    for release in releases:
        width = round(release.total_downloads / maximum * 100, 1) if maximum else 0
        badge = '<span class="badge">préversion</span>' if release.prerelease else ""
        tag = html.escape(release.tag)
        title = html.escape(release.name)
        link = html.escape(release.url, quote=True)
        release_title = f'<a href="{link}" target="_blank" rel="noopener">{tag}</a>'
        asset_rows = []
        for asset in release.assets:
            asset_count = f"{asset.downloads:,}".replace(",", " ")
            asset_rows.append(
                "".join(
                    (
                        "<li>",
                        f'<a href="{html.escape(asset.url, quote=True)}" '
                        'target="_blank" rel="noopener">',
                        f"{html.escape(asset.name)}</a>",
                        f"<b>{asset_count}</b>",
                        "</li>",
                    )
                )
            )
        asset_lines = "".join(asset_rows) or (
            "<li><span>Aucun paquet comptabilisé</span><b>0</b></li>"
        )
        release_count = f"{release.total_downloads:,}".replace(",", " ")
        rows.append(
            "".join(
                (
                    '<article class="release">',
                    "<header>",
                    f"<div><strong>{release_title}</strong>{badge}<span>{title}</span></div>",
                    f"<time>{html.escape(_format_date(release.published_at))}</time>",
                    "</header>",
                    '<div class="release-total">',
                    f"<strong>{release_count}</strong>",
                    "<span>téléchargements</span>",
                    "</div>",
                    f'<div class="bar"><i style="width:{width}%"></i></div>',
                    "<ul>",
                    asset_lines,
                    "</ul>",
                    "</article>",
                )
            )
        )

    empty = (
        '<div class="empty">Aucune Release publiée ou aucun paquet disponible.</div>'
        if not rows
        else ""
    )
    metrics = "".join(
        (
            _metric("Total", grand_total, "installateurs + versions portables"),
            _metric("Installateurs", installer_total, "fichiers Windows .exe"),
            _metric("Portables", portable_total, "archives Windows .zip"),
            _metric("Dernière version", latest_total, "paquets de la Release la plus récente"),
        )
    )
    repository_url = f"https://github.com/{repository}/releases"
    generated_label = generated_at.astimezone().strftime("%d/%m/%Y à %H:%M")
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NaviXav · Téléchargements GitHub</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f; --surface: #0d1b2d; --raised: #13243a;
      --border: #29405d; --text: #edf6ff; --muted: #91a8c2;
      --accent: #22d3ee; --accent-soft: rgba(34, 211, 238, .14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; color: var(--text); background:
      radial-gradient(circle at 85% 0, rgba(34,211,238,.12), transparent 34%),
      var(--bg); font: 15px/1.5 system-ui, sans-serif;
    }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 42px 0; }}
    .eyebrow {{ color: var(--accent); font-size: .75rem; font-weight: 750;
      letter-spacing: .16em; text-transform: uppercase; }}
    h1 {{ margin: 5px 0 8px; font-size: clamp(1.8rem, 4vw, 3rem); }}
    .intro {{ max-width: 720px; margin: 0; color: var(--muted); }}
    .meta {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 18px; }}
    .meta a {{ color: var(--accent); }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr);
      gap: 12px; margin: 28px 0; }}
    .metric {{ padding: 18px; border: 1px solid var(--border);
      border-radius: 14px; background: var(--surface); }}
    .metric span, .metric small {{ display: block; color: var(--muted); }}
    .metric strong {{ display: block; margin: 5px 0; font-size: 1.65rem; }}
    .releases {{ display: grid; gap: 12px; }}
    .release {{ padding: 18px; border: 1px solid var(--border);
      border-radius: 14px; background: var(--surface); }}
    .release header {{ display: flex; justify-content: space-between; gap: 16px; }}
    .release header div {{ display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap; }}
    .release a {{ color: var(--text); text-decoration: none; }}
    .release a:hover {{ color: var(--accent); }}
    .release header span, time {{ color: var(--muted); font-size: .78rem; }}
    .badge {{ padding: 2px 7px; border-radius: 999px; color: var(--accent) !important;
      background: var(--accent-soft); }}
    .release-total {{ display: flex; align-items: baseline; gap: 7px; margin-top: 14px; }}
    .release-total strong {{ font-size: 1.35rem; }}
    .release-total span {{ color: var(--muted); font-size: .78rem; }}
    .bar {{ height: 6px; margin: 10px 0 14px; overflow: hidden;
      border-radius: 999px; background: var(--raised); }}
    .bar i {{ display: block; height: 100%; border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #38efb1); }}
    ul {{ display: grid; gap: 5px; margin: 0; padding: 0; list-style: none; }}
    li {{ display: flex; justify-content: space-between; gap: 12px;
      color: var(--muted); font-size: .82rem; }}
    li b {{ color: var(--text); font-variant-numeric: tabular-nums; }}
    .empty {{ padding: 28px; text-align: center; color: var(--muted);
      border: 1px dashed var(--border); border-radius: 14px; }}
    .privacy {{ margin-top: 24px; padding: 14px 16px; color: var(--muted);
      border-left: 3px solid var(--accent); background: var(--accent-soft); }}
    @media (max-width: 760px) {{
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
      .release header {{ flex-direction: column; }}
    }}
    @media (max-width: 440px) {{ .metrics {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">NaviXav · statistiques publiques</div>
    <h1>Téléchargements GitHub Releases</h1>
    <p class="intro">Un instantané des compteurs publics GitHub. Les téléchargements
      répétés sont comptés et ces chiffres ne représentent pas des utilisateurs uniques.</p>
    <div class="meta">
      <span>Actualisé le {html.escape(generated_label)}</span>
      <a href="{html.escape(repository_url, quote=True)}" target="_blank" rel="noopener">
        Voir les Releases GitHub
      </a>
    </div>
    <section class="metrics">{metrics}</section>
    <section class="releases">{''.join(rows)}{empty}</section>
    <p class="privacy">Aucune télémétrie NaviXav : ce tableau lit uniquement les
      compteurs publics associés aux fichiers de Release GitHub.</p>
  </main>
</body>
</html>
"""


def write_dashboard(
    releases: list[ReleaseDownloads],
    destination: Path,
    repository: str = GITHUB_REPOSITORY,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_dashboard(releases, repository),
        encoding="utf-8",
    )
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Génère le tableau de bord d'administration local des "
            "téléchargements GitHub."
        )
    )
    parser.add_argument("--repository", default=GITHUB_REPOSITORY)
    parser.add_argument(
        "--output",
        type=Path,
        default=user_data_path("private_admin", "release-downloads.html"),
    )
    parser.add_argument("--no-open", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        releases = fetch_release_downloads(args.repository)
        destination = write_dashboard(releases, args.output, args.repository)
    except (OSError, ReleaseDashboardError) as exc:
        print(f"Tableau de bord impossible : {exc}")
        return 1
    print(f"Tableau de bord privé créé sur ce poste : {destination.resolve()}")
    if not args.no_open:
        webbrowser.open(destination.resolve().as_uri(), new=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
