from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from string import Template
from textwrap import dedent


@dataclass
class LabPrimerService:
    template_dir: Path
    output_root: Path | None = None
    auto_write: bool = False

    def generate(
        self,
        concept_name: str,
        goal: str,
        slug: str | None = None,
    ) -> dict[str, str]:
        slug = slug or self._slugify(concept_name)
        variables = {
            "concept_name": concept_name,
            "goal": goal,
            "slug": slug,
            "title": f"{concept_name} Lab",
            "http_port": os.environ.get("LAB_HTTP_PORT", "19200"),
            "kibana_port": os.environ.get("LAB_KIBANA_PORT", "15601"),
        }

        output_path = None
        if self.output_root:
            output_path = self.output_root / slug
            variables["output_path"] = str(output_path)
        else:
            variables["output_path"] = "<set LAB_OUTPUT_ROOT to auto-write>"

        files = {
            "README.md": self._render_template("README.md.tpl", variables),
            "docker-compose.yml": self._render_template("docker-compose.yml.tpl", variables),
            "Makefile": self._render_template("Makefile.tpl", variables),
            "notes.md": self._render_template("notes.md.tpl", variables),
        }

        if self.auto_write and self.output_root:
            self._write_files(output_path, files)

        summary = dedent(
            f"""
            ### Lab Primer: {concept_name}

            Files to create (copy each block):
            - `docker-compose.yml`
            - `Makefile`
            - `README.md`
            - `notes.md`

            Auto-write directory: {variables['output_path']}
            """
        ).strip()

        files_with_summary = {"summary": summary}
        files_with_summary.update(files)
        return files_with_summary

    def _render_template(self, name: str, variables: dict[str, str]) -> str:
        template_path = self.template_dir / name
        if not template_path.exists():
            raise FileNotFoundError(f"Lab template {name} missing at {template_path}")
        content = template_path.read_text(encoding="utf-8")
        return Template(content).safe_substitute(variables)

    def _write_files(self, directory: Path, files: dict[str, str]) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            target = directory / filename
            if not target.exists():
                target.write_text(content, encoding="utf-8")

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.strip().lower()
        return "-".join(
            filter(None, [segment for segment in value.replace("/", " ").split()])
        )

