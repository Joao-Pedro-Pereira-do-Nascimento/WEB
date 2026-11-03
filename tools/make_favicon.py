"""Gera assets/favicon.png (256x256) a partir de assets/favicon.svg.

Uso:  python tools/make_favicon.py
Precisa do ``cairosvg`` (pip install cairosvg) só para gerar o PNG; o app em
si usa apenas o PNG já gerado (nenhuma dependência extra em produção).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    import cairosvg

    svg = ROOT / "assets" / "favicon.svg"
    png = ROOT / "assets" / "favicon.png"
    cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=256, output_height=256)
    print(f"ok: {png}")


if __name__ == "__main__":
    main()
