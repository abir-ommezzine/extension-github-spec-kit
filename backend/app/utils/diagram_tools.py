# app/utils/diagram_tools.py
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

import httpx
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PDF_STORAGE_DIR = BASE_DIR.parent / "test_files" / "outputs" / "pdfs"


class DiagramExporterTool:
    """
    Boîte d'outils d'exportation graphique pour le Diagram Agent.
    Gère la conversion du code Mermaid.js en images PNG (via mmdc ou Kroki),
    la mise en page esthétique des planches et la compilation finale en PDF.
    """

    @staticmethod
    def _get_npm_prefix() -> str | None:
        """Récupère le préfixe npm global pour localiser l'exécutable mmdc."""
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

    @classmethod
    def _find_mmdc(cls) -> List[str]:
        """Localise l'exécutable mmdc (Mermaid CLI) sur la machine hôte."""
        for cmd in [["mmdc"], ["mmdc.cmd"]]:
            try:
                subprocess.run([*cmd, "--version"], check=True, capture_output=True, timeout=10)
                return cmd
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue

        prefix = cls._get_npm_prefix()
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

    @classmethod
    def _render_mermaid_mmdc(cls, mermaid_code: str, output_path: Path) -> bool:
        """Rendu local déterministe via l'exécutable Mermaid CLI."""
        mmdc_cmd = cls._find_mmdc()

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
            return result.returncode == 0
        except Exception:
            return False
        finally:
            if os.path.exists(mmd_path):
                os.unlink(mmd_path)

    @staticmethod
    async def _render_mermaid_kroki(mermaid_code: str, output_path: Path) -> bool:
        """Fallback de rendu distant via l'API Web Kroki.io."""
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
            print(f"[⚠️ KROKI FALLBACK FAILED] {exc}")
            return False

    @classmethod
    async def render_mermaid_to_png(cls, mermaid_code: str, output_path: Path) -> bool:
        """Tente un rendu local mmdc, puis bascule sur Kroki.io en cas d'échec."""
        try:
            if cls._render_mermaid_mmdc(mermaid_code, output_path):
                return True
        except RuntimeError:
            pass
        return await cls._render_mermaid_kroki(mermaid_code, output_path)

    @classmethod
    def validate_mermaid_syntax(cls, mermaid_code: str) -> bool:
        """Quick validation: try mmdc with a throwaway temp file, return True if syntax is valid."""
        if not str(mermaid_code).strip():
            return False
        try:
            mmdc_cmd = cls._find_mmdc()
        except RuntimeError:
            return True  # Can't validate without mmdc, assume valid
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as f:
            f.write(mermaid_code)
            mmd_path = f.name
        try:
            result = subprocess.run(
                [*mmdc_cmd, "-i", mmd_path, "-o", os.devnull, "-b", "white"],
                capture_output=True, text=True, timeout=30,
                shell=(platform.system() == "Windows"),
            )
            return result.returncode == 0
        except Exception:
            return True  # If validation itself fails, assume valid
        finally:
            if os.path.exists(mmd_path):
                os.unlink(mmd_path)

    @staticmethod
    def _render_page(
        index: int,
        title: str,
        description: str,
        diagram_png: Path | None,
        tmpdir: Path,
        error_text: str | None = None,
        raw_code: str | None = None,
    ) -> Path:
        """Génère la mise en page de la planche (Titre, Description, Schéma/Erreur et Pied de page) via Pillow."""
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

        # En-tête : Titre & Description
        draw.text((margin, y), f"{index}. {title}", fill="#1a1a1a", font=title_font)
        y += 65
        draw.text((margin, y), description, fill="#555555", font=desc_font)
        y += 50

        if error_text:
            # Planche de repli en cas d'erreur de rendu
            draw.rectangle([margin, y, page_width - margin, y + 40], fill="#ffebee", outline="#f44336")
            draw.text((margin + 10, y + 8), f"⚠ {error_text}", fill="#c62828", font=error_font)
            y += 60

            if raw_code:
                draw.text((margin, y), "Raw Mermaid code:", fill="#333333", font=desc_font)
                y += 35
                lines = raw_code.split("\n")
                for line in lines[:40]:
                    draw.text((margin + 10, y), line[:90], fill="#666666", font=code_font)
                    y += 22
        else:
            # Insertion du schéma PNG centré et redimensionné
            available_height = page_height - y - margin - 50
            available_width = page_width - (margin * 2)

            if diagram_png and diagram_png.exists():
                try:
                    diagram = Image.open(diagram_png).convert("RGBA")
                    white_bg = Image.new("RGBA", diagram.size, (255, 255, 255, 255))
                    diagram = Image.alpha_composite(white_bg, diagram).convert("RGB")

                    img_w, img_h = diagram.size
                    scale = min(available_width / img_w, available_height / img_h)

                    new_w, new_h = int(img_w * scale), int(img_h * scale)
                    diagram = diagram.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    x = (page_width - new_w) // 2
                    page.paste(diagram, (x, y))
                except Exception as e:
                    draw.text((margin, y), f"[Image paste error: {e}]", fill="red", font=error_font)

        # Pied de page
        draw.text(
            (margin, page_height - 30),
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            fill="#999999",
            font=footer_font,
        )

        page_path = tmpdir / f"page_{index:03d}.png"
        page.save(page_path, "PNG")
        return page_path

    @classmethod
    async def render_diagrams_to_pdf(cls, file_stem: str, diagrams_data: Dict[str, Any]) -> str:
        """
        Génère les planches d'images PNG pour l'ensemble des diagrammes
        et compile le tout dans un fichier PDF unique sous test_files/outputs/pdfs/.
        """
        diagrams = diagrams_data.get("diagrams", []) if isinstance(diagrams_data, dict) else []
        if not diagrams:
            raise ValueError("No diagrams to render")

        PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            page_paths = []

            for i, diag in enumerate(diagrams, start=1):
                title = diag.get("title", f"Diagram {i}")
                description = diag.get("description", "")
                mermaid_code = diag.get("mermaid_code", "")

                if not str(mermaid_code).strip():
                    continue

                png_path = tmpdir / f"diag_{i:03d}.png"
                success = await cls.render_mermaid_to_png(str(mermaid_code), png_path)

                if not success:
                    page_path = cls._render_page(
                        i, title, description, None, tmpdir,
                        error_text="Could not render diagram — invalid Mermaid syntax",
                        raw_code=str(mermaid_code),
                    )
                else:
                    page_path = cls._render_page(i, title, description, png_path, tmpdir)

                page_paths.append(page_path)

            if not page_paths:
                raise RuntimeError("No pages were rendered")

            import img2pdf
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{file_stem}_diagrams_{timestamp}.pdf"
            pdf_path = PDF_STORAGE_DIR / filename

            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert([str(p) for p in page_paths]))

        return str(pdf_path)