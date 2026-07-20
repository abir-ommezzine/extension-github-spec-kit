import os
import platform
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

import httpx
from PIL import Image, ImageDraw, ImageFont

PDF_STORAGE_DIR = Path(os.getenv("PDF_STORAGE_DIR", "./storage/pdfs"))
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _get_npm_prefix() -> str | None:
    try:
        result = subprocess.run(
            ["npm", "config", "get", "prefix"],
            capture_output=True, text=True, timeout=10, shell=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _find_mmdc() -> list[str]:
    for cmd in [["mmdc"], ["mmdc.cmd"]]:
        try:
            subprocess.run([*cmd, "--version"], check=True, capture_output=True, timeout=10)
            return cmd
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue

    prefix = _get_npm_prefix()
    if prefix:
        candidates = []
        if platform.system() == "Windows":
            candidates = [
                os.path.join(prefix, "mmdc.cmd"),
                os.path.join(prefix, "node_modules", ".bin", "mmdc.cmd"),
                os.path.join(prefix, "node_modules", "@mermaid-js", "mermaid-cli", "node_modules", ".bin", "mmdc.cmd"),
            ]
        else:
            candidates = [
                os.path.join(prefix, "bin", "mmdc"),
                os.path.join(prefix, "node_modules", ".bin", "mmdc"),
            ]
        for path in candidates:
            if os.path.isfile(path):
                return [path]

    if platform.system() == "Windows":
        hardcoded = [
            os.path.expandvars(r"%APPDATA%\npm\mmdc.cmd"),
            os.path.expandvars(r"%LOCALAPPDATA%\npm\mmdc.cmd"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Roaming\npm\mmdc.cmd"),
            r"C:\Program Files\nodejs\mmdc.cmd",
            r"C:\Program Files (x86)\nodejs\mmdc.cmd",
        ]
        for path in hardcoded:
            if os.path.isfile(path):
                return [path]

    raise RuntimeError("mermaid-cli not found")


def _render_mermaid_mmdc(mermaid_code: str, output_path: Path) -> bool:
    mmdc_cmd = _find_mmdc()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as f:
        f.write(mermaid_code)
        mmd_path = f.name

    try:
        result = subprocess.run(
            [
                *mmdc_cmd,
                "-i", mmd_path,
                "-o", str(output_path),
                "-b", "white",
                "-t", "default",
                "-s", "3",
                "--width", "2400",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            shell=(platform.system() == "Windows"),
        )
        if result.returncode != 0:
            print(f"mmdc stderr: {result.stderr[:500]}")
            return False
        return True
    finally:
        os.unlink(mmd_path)


async def _render_mermaid_kroki(mermaid_code: str, output_path: Path) -> bool:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://kroki.io",
                json={
                    "diagram_source": mermaid_code,
                    "diagram_type": "mermaid",
                    "output_format": "png",
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            output_path.write_bytes(response.content)
            return True
    except Exception as exc:
        print(f"Kroki fallback failed: {exc}")
        return False


async def _render_mermaid_to_png(mermaid_code: str, output_path: Path) -> bool:
    try:
        return _render_mermaid_mmdc(mermaid_code, output_path)
    except RuntimeError:
        return await _render_mermaid_kroki(mermaid_code, output_path)


def _render_page(
    index: int,
    title: str,
    description: str,
    diagram_png: Path | None,
    tmpdir: Path,
    error_text: str | None = None,
    raw_code: str | None = None,
) -> Path:
    page_width, page_height = 1240, 1754
    page = Image.new("RGB", (page_width, page_height), "white")
    draw = ImageDraw.Draw(page)

    try:
        title_font = ImageFont.truetype("arial.ttf", 40)
        desc_font = ImageFont.truetype("arial.ttf", 22)
        code_font = ImageFont.truetype("arial.ttf", 16)
        error_font = ImageFont.truetype("arial.ttf", 20)
        footer_font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        title_font = desc_font = code_font = error_font = footer_font = ImageFont.load_default()

    margin = 60
    y = margin

    # Title
    draw.text((margin, y), f"{index}. {title}", fill="#1a1a1a", font=title_font)
    y += 65

    # Description
    draw.text((margin, y), description, fill="#555555", font=desc_font)
    y += 50

    if error_text:
        # Render error placeholder
        draw.rectangle([margin, y, page_width - margin, y + 40], fill="#ffebee", outline="#f44336")
        draw.text((margin + 10, y + 8), f"⚠ {error_text}", fill="#c62828", font=error_font)
        y += 60

        if raw_code:
            draw.text((margin, y), "Raw Mermaid code:", fill="#333333", font=desc_font)
            y += 35
            # Wrap code text
            lines = []
            for line in raw_code.split("\n"):
                while line:
                    if len(line) > 90:
                        lines.append(line[:90])
                        line = line[90:]
                    else:
                        lines.append(line)
                        break
            for line in lines[:40]:  # max 40 lines
                draw.text((margin + 10, y), line, fill="#666666", font=code_font)
                y += 22
    else:
        # Render diagram image
        footer_space = 50
        available_height = page_height - y - margin - footer_space
        available_width = page_width - (margin * 2)

        if diagram_png and diagram_png.exists():
            try:
                diagram = Image.open(diagram_png).convert("RGBA")
                white_bg = Image.new("RGBA", diagram.size, (255, 255, 255, 255))
                diagram = Image.alpha_composite(white_bg, diagram).convert("RGB")

                img_w, img_h = diagram.size
                scale_w = available_width / img_w
                scale_h = available_height / img_h
                scale = min(scale_w, scale_h)

                new_w = int(img_w * scale)
                new_h = int(img_h * scale)
                diagram = diagram.resize((new_w, new_h), Image.Resampling.LANCZOS)

                x = (page_width - new_w) // 2
                page.paste(diagram, (x, y))
            except Exception as e:
                draw.text((margin, y), f"[Image paste error: {e}]", fill="red", font=error_font)

    # Footer
    draw.text(
        (margin, page_height - 30),
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        fill="#999999",
        font=footer_font,
    )

    page_path = tmpdir / f"page_{index:03d}.png"
    page.save(page_path, "PNG")
    return page_path


async def generate_diagram_pdf(artifact_id: str, diagrams_data: dict) -> str:
    diagrams = diagrams_data.get("diagrams", []) if isinstance(diagrams_data, dict) else []
    if not diagrams:
        raise ValueError("No diagrams to render")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        page_paths = []

        for i, diag in enumerate(diagrams, start=1):
            title = diag.get("title", f"Diagram {i}") if isinstance(diag, dict) else f"Diagram {i}"
            description = diag.get("description", "") if isinstance(diag, dict) else ""
            mermaid_code = diag.get("mermaid_code", "") if isinstance(diag, dict) else ""

            if not str(mermaid_code).strip():
                continue

            png_path = tmpdir / f"diag_{i:03d}.png"
            success = await _render_mermaid_to_png(str(mermaid_code), png_path)

            if not success:
                # FALLBACK: create a placeholder page with the raw code
                page_path = _render_page(
                    i, title, description, None, tmpdir,
                    error_text="Could not render diagram — invalid Mermaid syntax",
                    raw_code=str(mermaid_code),
                )
            else:
                page_path = _render_page(i, title, description, png_path, tmpdir)

            page_paths.append(page_path)

        if not page_paths:
            raise RuntimeError("No pages to render")

        import img2pdf
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diagrams_{artifact_id}_{timestamp}.pdf"
        pdf_path = PDF_STORAGE_DIR / filename

        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in page_paths]))

    return str(pdf_path)