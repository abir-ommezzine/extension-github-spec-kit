#!/usr/bin/env python3
r"""
test_full_workflow.py — Test end-to-end du pipeline complet avec Document Writer.

USAGE:
    cd backend
    .venv\Scripts\activate

    # Test avec le document par defaut (sample inline)
    python test_full_workflow.py

    # Test avec un fichier markdown
    python test_full_workflow.py --file "../test_files/tasks.md"
    python test_full_workflow.py --file "C:/Users/MSI/Documents/spec.md"

    # Test avec un fichier et dossier de sortie parent personnalise
    python test_full_workflow.py --file "./test_files/input.md" --output-base "./results"

STRUCTURE DE SORTIE:
    outputs/
    └── {nom_du_fichier_sans_extension}/
        ├── {nom}_parsed.json
        ├── {nom}_parsing_eval.json
        ├── {nom}_summary.json
        ├── {nom}_summary_eval.json
        ├── {nom}_glossary.json
        ├── {nom}_glossary_eval.json
        ├── {nom}_diagrams.json
        ├── {nom}_diagram_eval.json
        ├── {nom}_diagrams.pdf          (si disponible)
        ├── {nom}_document.json
        ├── {nom}_document_eval.json
        └── {nom}_final_document.md

Pipeline: START -> Parsing -> Summary -> Glossary -> Diagram -> Document Writer -> END
"""

import sys
import os
import argparse
from pathlib import Path

# PATH SETUP
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# ENV
from dotenv import load_dotenv
load_dotenv(SCRIPT_DIR / ".env")

# No API key needed for Ollama (local)
print(f"🤖 Modele LLM: {os.getenv('LLM_MODEL', 'NON DEFINI')}")
print(f"🔑 Provider: Ollama (local - aucune cle API requise)")

# IMPORTS
from app.graph.workflow import create_pipeline_workflow


# =============================================================================
# SAMPLE MARKDOWN DOCUMENT (fallback)
# =============================================================================

SAMPLE_MARKDOWN = """
# CourseHub API — Technical Specification

## Overview
CourseHub is a learning management system API built with FastAPI and PostgreSQL.
It enables instructors to create courses and students to enroll and track progress.

## Authentication
The system uses JWT token-based authentication. Three roles exist:
- **student**: Can enroll in courses and track progress
- **instructor**: Can create and manage their own courses
- **admin**: Full system access

## Course Management
Instructors can perform CRUD operations on courses they own.
A course cannot be deleted if active enrollments exist.

## Enrollment System
Students enroll in courses. Each enrollment tracks progress from 0 to 100%.

## Technical Stack
- Python 3.11 with FastAPI
- SQLAlchemy 2.0 with async PostgreSQL
- Alembic for database migrations
- Pytest for testing (target: 80% coverage)
- JWT for authentication

## Constraints
- All database operations must be asynchronous
- Test coverage must be >= 80% for core behaviors
- Course deletion blocked if enrollments > 0
- Instructors can only manage their own courses

## API Endpoints (Partial)
- POST /auth/login — JWT token generation
- POST /courses — Create course (instructor only)
- GET /courses — List all courses
- POST /enrollments — Enroll in a course
- GET /enrollments/{id}/progress — Track progress

## Open Questions
- Should we support OAuth2 providers?
- What is the maximum file upload size?
"""


def read_markdown_file(file_path: str) -> tuple[str, str]:
    """
    Lit un fichier markdown et retourne (nom_fichier, contenu).
    Supporte les chemins relatifs et absolus.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        path = SCRIPT_DIR / file_path
        if not path.exists():
            raise FileNotFoundError(f"Fichier non trouve: {file_path}")

    if not path.is_file():
        raise ValueError(f"Le chemin n est pas un fichier: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"   📄 Fichier lu: {path}")
    print(f"   📊 Taille: {len(content)} caracteres, {len(content.splitlines())} lignes")

    return path.name, content


def setup_output_directory(file_name: str, output_base: str) -> Path:
    """
    Cree le dossier de sortie: {output_base}/{nom_fichier_sans_extension}/
    Retourne le Path du dossier cree.
    """
    base_stem = Path(file_name).stem
    output_dir = SCRIPT_DIR / output_base / base_stem
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"   📁 Dossier de sortie: {output_dir}")
    return output_dir


def list_generated_files(output_dir: Path, base_stem: str) -> None:
    """
    Affiche tous les fichiers generes dans le dossier de sortie.
    """
    if not output_dir.exists():
        print("   ⚠️ Dossier de sortie inexistant")
        return

    files = sorted(output_dir.glob(f"{base_stem}*"))
    if not files:
        print("   ⚠️ Aucun fichier genere trouve")
        return

    print(f"\n   📁 Fichiers generes dans {output_dir}:")
    total_size = 0
    for f in files:
        size = f.stat().st_size
        total_size += size
        size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
        print(f"      • {f.name:<50} {size_str:>12}")

    print(f"      {'─'*65}")
    print(f"      {'TOTAL':<50} {total_size/1024:.1f} KB")


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test du pipeline Spec Kit Extension avec Document Writer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python test_full_workflow.py
  python test_full_workflow.py --file "../test_files/tasks.md"
  python test_full_workflow.py --file "./input.md" --output-base "./results"
        """
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Chemin vers un fichier markdown a analyser (relatif ou absolu)"
    )
    parser.add_argument(
        "--output-base", "-o",
        type=str,
        default="test_files/outputs",
        help="Dossier parent pour les sorties (defaut: test_files/outputs)"
    )
    args = parser.parse_args()

    # Header
    print("\n" + "=" * 70)
    print("🧪 TEST COMPLET DU WORKFLOW — SPEC KIT EXTENSION")
    print("=" * 70)
    print(f"\n🤖 Modele LLM: {os.getenv('LLM_MODEL', 'NON DEFINI')}")
    print(f"🔑 Provider: Ollama (local - aucune cle API requise)")
    print("\nPipeline: START -> Parsing -> Summary -> Glossary -> Diagram -> Document Writer -> END")
    print("-" * 70)

    # 1. Load input document
    print("\n[1/5] Chargement du document...")

    if args.file:
        try:
            file_name, file_content = read_markdown_file(args.file)
        except Exception as e:
            print(f"   ❌ ERREUR: {e}")
            return 1
    else:
        file_name = "sample_spec.md"
        file_content = SAMPLE_MARKDOWN
        print("   ℹ️ Aucun fichier fourni, utilisation du document par defaut")
        print(f"   📄 Fichier: {file_name} (inline)")
        print(f"   📊 Taille: {len(file_content)} caracteres")

    # 2. Setup output directory
    print("\n[2/5] Preparation du dossier de sortie...")
    base_stem = Path(file_name).stem
    run_output_dir = setup_output_directory(file_name, args.output_base)

    # Override global OUTPUTS_DIR for this run by monkey-patching in nodes
    import app.graph.nodes as nodes_module
    nodes_module.OUTPUTS_DIR = run_output_dir
    print(f"   ✅ Dossier pret: {run_output_dir}")

    # 3. Build workflow
    print("\n[3/5] Compilation du workflow LangGraph...")
    try:
        workflow = create_pipeline_workflow()
        print("   ✅ Workflow compile avec succes")
        print(f"   📊 Noeuds: {list(workflow.nodes.keys())}")
    except Exception as e:
        print(f"   ❌ ERREUR de compilation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. Prepare input state
    print("\n[4/5] Preparation de l etat initial...")
    inputs = {
        "file_name": file_name,
        "file_content": file_content,
        "parsed_json_dict": None,
        "parsed_doc": None,
        "parsing_metrics": None,
        "summary_doc": None,
        "summary_metrics": None,
        "glossary_doc": None,
        "glossary_metrics": None,
        "diagram_doc": None,
        "diagram_metrics": None,
        "diagram_pdf_path": None,
        "document_writer_doc": None,
        "document_writer_metrics": None,
    }
    print("   ✅ Etat initial pret")

    # 5. Execute workflow
    print("\n[5/5] Execution du pipeline...")
    print("   ⏳ Cela peut prendre plusieurs minutes sur CPU (Ollama)...")
    print("   ⏳ Parsing Agent en cours...\n")

    try:
        result = workflow.invoke(inputs)
        print("\n   ✅ PIPELINE TERMINE AVEC SUCCES!")
    except Exception as e:
        print(f"\n   ❌ ERREUR pendant l execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 6. Display results
    print("\n" + "=" * 70)
    print("📊 RESULTATS DU PIPELINE")
    print("=" * 70)

    # Parsing results
    if result.get("parsed_doc"):
        parsed = result["parsed_doc"]
        print(f"\n📄 PARSING AGENT")
        print(f"   • Sections: {len(parsed.sections)}")
        print(f"   • Elements: {len(parsed.elements)}")
        print(f"   • Relations: {len(parsed.relationships)}")
        print(f"   • Gaps: {len(parsed.structural_gaps)}")
        print(f"   • Questions ouvertes: {len(parsed.open_questions)}")
    else:
        print("\n❌ Parsing Agent: ECHEC")

    # Summary results
    if result.get("summary_doc"):
        summary = result["summary_doc"]
        print(f"\n📝 SUMMARY AGENT")
        print(f"   • Executive Brief: {len(summary.executive_brief.split())} mots")
        print(f"   • Technologies: {len(summary.technical_stack.languages_and_frameworks)}")
        print(f"   • Contraintes: {len(summary.technical_stack.architectural_constraints)}")
        print(f"   • Dependances: {len(summary.critical_dependencies)}")
        print(f"   • Maturite: {summary.maturity_assessment[:60]}...")
    else:
        print("\n❌ Summary Agent: ECHEC")

    # Glossary results
    if result.get("glossary_doc"):
        glossary = result["glossary_doc"]
        print(f"\n📚 GLOSSARY AGENT")
        print(f"   • Termes: {len(glossary.items)}")
        tech_terms = sum(1 for i in glossary.items if i.category.value == "TECHNICAL_STACK")
        biz_terms = sum(1 for i in glossary.items if i.category.value == "BUSINESS_DOMAIN")
        print(f"   •   Technique: {tech_terms}")
        print(f"   •   Metier: {biz_terms}")
    else:
        print("\n❌ Glossary Agent: ECHEC")

    # Diagram results
    if result.get("diagram_doc"):
        diagram = result["diagram_doc"]
        diag_count = len(diagram.diagrams) if hasattr(diagram, "diagrams") else 0
        print(f"\n📐 DIAGRAM AGENT")
        print(f"   • Diagrammes: {diag_count}")
        if result.get("diagram_pdf_path"):
            print(f"   • PDF: {result['diagram_pdf_path']}")
    else:
        print("\n⚠️ Diagram Agent: Non disponible (gracieusement ignore)")

    # Document Writer results
    if result.get("document_writer_doc"):
        doc = result["document_writer_doc"]
        print(f"\n📖 DOCUMENT WRITER")
        print(f"   • Titre: {doc.title}")
        print(f"   • Mots: {doc.word_count}")
        print(f"   • Sections: {len(doc.sections_included)}")
        print(f"   • Diagrammes integres: {doc.diagram_count}")
        print(f"   • Termes glossaire: {doc.glossary_term_count}")
        print(f"   • Sources: {doc.sources_used}")

        # Save final markdown in the run folder
        final_md = run_output_dir / f"{base_stem}_final_document.md"
        with open(final_md, "w", encoding="utf-8") as f:
            f.write(doc.markdown_content)
        print(f"   • 💾 Markdown final: {final_md}")

        # Preview
        print(f"\n👁️  APERCU (1500 premiers caracteres):")
        print("-" * 70)
        preview = doc.markdown_content[:1500]
        print(preview)
        if len(doc.markdown_content) > 1500:
            print(f"\n... ({len(doc.markdown_content) - 1500} caracteres restants)")
    else:
        print("\n❌ Document Writer: ECHEC")

    # Metrics summary
    print("\n" + "=" * 70)
    print("📈 METRIQUES D EVALUATION")
    print("=" * 70)

    for agent in ["parsing", "summary", "glossary", "diagram", "document_writer"]:
        metrics = result.get(f"{agent}_metrics")
        if metrics:
            print(f"\n{agent.upper()}:")
            if isinstance(metrics, dict):
                for k, v in metrics.items():
                    if isinstance(v, (int, float, str, bool)):
                        print(f"   • {k}: {v}")

    # List all generated files
    print("\n" + "=" * 70)
    print("📁 FICHIERS GENERES")
    print("=" * 70)
    list_generated_files(run_output_dir, base_stem)

    print("\n" + "=" * 70)
    print("✅ TEST COMPLET DU WORKFLOW TERMINE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())