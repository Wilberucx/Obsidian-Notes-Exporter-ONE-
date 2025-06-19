import sys, os, re, shutil, subprocess, json, logging
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import yaml
except ImportError:
    print("ERROR: La librería PyYAML es necesaria. Ejecuta: pip install PyYAML")
    sys.exit(1)

# --- CONFIGURACIÓN GENERAL Y LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
TEMPLATE_DIR = BASE_DIR / "templates"
ATTACHMENT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf'}
YAML_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
LINK_PATTERN = re.compile(r'(!?)\[\[([^|#\]]+)(?:\|([^\]]+))?\]\]')
LIST_LINE_PATTERN = re.compile(r"^(\s*)-\s*(.*?)\[\[([^|#\]]+)(?:\|([^\]]+))?\]\](.*)")
TAG_PATTERN = re.compile(r'(?<!#)#[\w-]+')
OUTPUT_SUBFOLDER_NAME = "_Converted"


class ONEExporter:
    def __init__(self, vault_path: Path, export_base_dir: Path, exclude_folders: list):
        self.vault_path = vault_path
        self.export_base_dir = export_base_dir
        self.exclude_folders = exclude_folders
        self.export_root = self._create_export_structure()
        self.notes_dir = self.export_root / "Notes"
        self.assets_dir = self.export_root / "Assets"
        self.vault_index = self._build_vault_index()
        self.processed_notes = set()
        self.copied_assets = set()
        self.notes_in_scope = set()
        self.structure_map = {}

    def _create_export_structure(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = self.export_base_dir / f"Export_{self.vault_path.name}_{timestamp}"
        (dest_dir / "Notes").mkdir(parents=True, exist_ok=True)
        (dest_dir / "Assets").mkdir(exist_ok=True)
        logging.info(f"Export folder created at: {dest_dir}")
        return dest_dir

    def _build_vault_index(self):
        logging.info(f"Building index for vault: {self.vault_path}...")
        index = {}
        for root, dirs, files in os.walk(self.vault_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_folders]
            for file in files:
                full_path = Path(root) / file
                if not any(excluded in full_path.parts for excluded in self.exclude_folders):
                    index[full_path.stem.lower()] = full_path
                    index[full_path.name.lower()] = full_path
        logging.info(f"Index built with {len(index)} entries.")
        return index

    def _clean_yaml(self, content: str) -> str:
        return YAML_PATTERN.sub('', content, count=1)

    def _flatten_and_copy_note_content(self, note_path: Path):
        if note_path in self.processed_notes: return
        self.processed_notes.add(note_path)
        content = self._clean_yaml(note_path.read_text(encoding='utf-8'))
        content = TAG_PATTERN.sub('', content)
        def link_flattener(match):
            is_embed, target, alias = match.groups()
            clean_target_name = unquote(target).lower()
            if is_embed:
                linked_file = self.vault_index.get(clean_target_name) or self.vault_index.get(Path(clean_target_name).stem)
                if linked_file and linked_file.suffix.lower() in ATTACHMENT_EXTENSIONS:
                    shutil.copy(linked_file, self.assets_dir / linked_file.name)
                    return f"![{alias or target}]({linked_file.name})"
                return f"(Contenido embebido de: {target})"
            return alias or target
        (self.notes_dir / note_path.name).write_text(LINK_PATTERN.sub(link_flattener, content), encoding='utf-8')

    def _create_yaml_header(self, metadata, export_config):
        title = metadata.get('title', 'Untitled')
        author = metadata.get('author', 'Unknown')
        date_val = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
        return f"---\ntitle: '{title}'\nauthor: '{author}'\ndate: {date_val}\nexport_style: {export_config.get('style', 'classic')}\ncover-image: '{export_config.get('cover-image', '')}'\n---\n\n"

    def build_package(self, start_note_path: Path, export_config: dict):
        mode = export_config.get('mode', 'manual')
        if mode == 'manual':
            logging.info("Starting build in Manual Mode...")
            moc_content = start_note_path.read_text(encoding='utf-8')
            moc_body = self._clean_yaml(moc_content)
            for match in LINK_PATTERN.finditer(moc_body):
                if not match.group(1):
                    clean_target_name = unquote(match.group(2)).lower()
                    note = self.vault_index.get(clean_target_name) or self.vault_index.get(Path(clean_target_name).stem)
                    if note and note.suffix.lower() == '.md':
                        self.notes_in_scope.add(note)
            for note in self.notes_in_scope:
                self._flatten_and_copy_note_content(note)
            self._generate_moc_from_blueprint(moc_body, export_config)
        else: # Automatic mode
            logging.info("Starting build in Automatic Mode...")
            depth = export_config.get('depth', 1)
            max_depth = -1 if str(depth).lower() == 'infinite' else int(depth)
            self._traverse_and_collect(start_note_path, 0, max_depth)
            for note in self.notes_in_scope:
                self._flatten_and_copy_note_content(note)
            self._generate_moc_from_structure(start_note_path, export_config)
        logging.info("--- ✅ Export package build process completed! ---")

    def _generate_moc_from_blueprint(self, moc_blueprint, export_config):
        final_moc_lines, pending_heading = [], None
        for line in moc_blueprint.splitlines():
            stripped_line = line.strip()
            if not stripped_line: continue
            if stripped_line.startswith('#'):
                pending_heading = stripped_line.lstrip('#').strip()
                continue
            match = LIST_LINE_PATTERN.match(line)
            if match:
                indent_str, _, target, alias, _ = match.groups()
                title = pending_heading or alias or target
                pending_heading = None
                clean_target_name = unquote(target).lower()
                note = self.vault_index.get(clean_target_name) or self.vault_index.get(Path(clean_target_name).stem)
                if note:
                    level = len(indent_str) // 4
                    if level == 0 and final_moc_lines: final_moc_lines.append('\n\\newpage\n')
                    final_moc_lines.append(f"{'#' * (level + 1)} {title}\n!include[\"{note.name}\"]")
        yaml_header = self._create_yaml_header(export_config.get('metadata', {}), export_config)
        (self.notes_dir / "_MOC_Guide.md").write_text(yaml_header + "\n".join(final_moc_lines), encoding='utf-8')

    def _traverse_and_collect(self, note_path, depth, max_depth):
        if (max_depth != -1 and depth > max_depth) or note_path in self.notes_in_scope: return
        self.notes_in_scope.add(note_path)
        children = []
        content = self._clean_yaml(note_path.read_text(encoding='utf-8'))
        for match in LINK_PATTERN.finditer(content):
            if not match.group(1):
                clean_target_name = unquote(match.group(2)).lower()
                child_path = self.vault_index.get(clean_target_name) or self.vault_index.get(Path(clean_target_name).stem)
                if child_path and child_path.suffix.lower() == '.md':
                    children.append(child_path)
        self.structure_map[note_path] = {'depth': depth, 'children': children}
        for child in children:
            self._traverse_and_collect(child, depth + 1, max_depth)

    def _generate_moc_from_structure(self, start_note, export_config):
        final_moc_lines, processed = [], set()
        def write_node(note):
            if note in processed or note not in self.structure_map: return
            processed.add(note)
            data = self.structure_map[note]
            if data['depth'] == 0 and final_moc_lines: final_moc_lines.append('\n\\newpage\n')
            final_moc_lines.append(f"\n{'#' * (data['depth'] + 1)} {note.stem}\n!include[\"{note.name}\"]")
            for child in data['children']: write_node(child)
        write_node(start_note)
        yaml_header = self._create_yaml_header(export_config.get('metadata', {}), export_config)
        (self.notes_dir / "_MOC_Guide.md").write_text(yaml_header + "\n".join(final_moc_lines), encoding='utf-8')

    def convert_package(self, formats: list):
        moc_path = self.notes_dir / "_MOC_Guide.md"
        if not moc_path.exists():
            logging.error("MOC Guide not found. Cannot run converter.")
            return
        final_markdown_content, metadata = self._assemble_full_markdown(moc_path)
        for fmt in formats:
            fmt = fmt.lower().strip()
            if not fmt or fmt == 'md': continue
            logging.info(f"--- Starting conversion to {fmt.upper()} ---")
            output_dir = self.export_root / OUTPUT_SUBFOLDER_NAME
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{self.export_root.name}.{fmt}"
            command = self._build_pandoc_command(fmt, output_file, metadata)
            if not command: continue
            if self._run_pandoc_command(command, final_markdown_content):
                logging.info(f"--- ✅ Conversion to {fmt.upper()} successful! ---")
            else:
                logging.error(f"--- ❌ Conversion to {fmt.upper()} failed. ---")

    def _assemble_full_markdown(self, moc_path):
        content = moc_path.read_text(encoding='utf-8')
        def replacer(match):
            name = match.group(1)
            path = self.notes_dir / name
            return path.read_text(encoding='utf-8') if path.exists() else f"<!-- INCLUDE FAILED: {name} -->"
        full_content = re.sub(r'!include\["([^"]+)"\]', replacer, content)
        yaml_data = yaml.safe_load(YAML_PATTERN.search(full_content).group(1)) or {}
        return full_content, yaml_data

    def _build_pandoc_command(self, fmt, output_file, metadata):
        resource_path = f"{self.notes_dir}{os.pathsep}{self.assets_dir}"
        command = ["pandoc", "--from=markdown+raw_tex", "-o", str(output_file), "--resource-path", resource_path, "--standalone", "--toc", "--number-sections"]
        if fmt == 'pdf':
            style_options = ['-V', 'documentclass=article']
            if metadata.get('export_style') == 'modern':
                style_options.extend(['-V', 'fontsize=11pt', '-V', 'mainfont=Arial'])
            else:
                style_options.extend(['-V', 'fontsize=12pt', '-V', 'mainfont=Times New Roman'])
            command.extend(style_options)
            header_path = TEMPLATE_DIR / "header_with_newpage.tex"
            if header_path.exists(): command.extend(["--include-in-header", str(header_path)])
            command.append("--pdf-engine=xelatex")
        elif fmt == 'docx':
            ref_path = TEMPLATE_DIR / "reference.docx"
            if ref_path.exists(): command.extend(["--reference-doc", str(ref_path)])
        elif fmt == 'epub':
            css_path = TEMPLATE_DIR / "stylesheet.css"
            if css_path.exists(): command.extend(["--css", str(css_path)])
            if metadata.get('cover-image'):
                cover_path = self.assets_dir / Path(metadata['cover-image']).name
                if cover_path.exists(): command.extend(["--epub-cover-image", str(cover_path)])
        return command

    def _run_pandoc_command(self, command, content):
        try:
            result = subprocess.run(command, input=content.encode('utf-8'), check=True, capture_output=True)
            if result.stderr: logging.info(f"Pandoc Messages:\n{result.stderr.decode('utf-8')}")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            logging.error(f"Pandoc execution failed: {e}")
            if hasattr(e, 'stderr'): logging.error(e.stderr.decode('utf-8'))
            return False

def read_export_config(note_path: Path) -> dict:
    config = {'mode': 'manual', 'depth': 1, 'formats': []}
    content = note_path.read_text(encoding='utf-8')
    match = YAML_PATTERN.search(content)
    if match:
        user_yaml = yaml.safe_load(match.group(1))
        if isinstance(user_yaml, dict):
            config['mode'] = user_yaml.get('export_mode', config['mode']).lower()
            config['depth'] = user_yaml.get('export_depth', config['depth'])
            formats = user_yaml.get('export_formats', config['formats'])
            config['formats'] = formats if isinstance(formats, list) else [formats]
            config['style'] = user_yaml.get('export_style', 'classic').lower()
            config['cover-image'] = user_yaml.get('cover-image', '')
            config['metadata'] = {
                'title': user_yaml.get('export_title', note_path.stem),
                'author': user_yaml.get('export_author', 'Unknown'),
                'date': user_yaml.get('export_date', datetime.now().strftime('%Y-%m-%d'))
            }
    return config

def find_vault_for_note(vault_paths, note_path):
    resolved_note = note_path.resolve()
    for vp in sorted([Path(p).resolve() for p in vault_paths], key=lambda p: len(str(p)), reverse=True):
        if vp in resolved_note.parents: return vp
    return None

def main():
    root = tk.Tk()
    root.withdraw()
    start_note_str = None
    if len(sys.argv) > 1:
        logging.info(f"File path provided via command line argument: {sys.argv[1]}")
        start_note_str = sys.argv[1]
    else:
        logging.info("No file path provided. Opening file selection dialog...")
        start_note_str = filedialog.askopenfilename(
            title="Selecciona la Nota de Inicio (MOC)", 
            filetypes=[("Markdown", "*.md")]
        )
    if not start_note_str:
        logging.warning("No start note selected. Exiting.")
        if len(sys.argv) <= 1:
             messagebox.showwarning("Cancelado", "No se seleccionó ninguna nota. El proceso ha sido cancelado.")
        return
    start_note_path = Path(start_note_str)
    try:
        with open(CONFIG_FILE, 'r') as f: config = json.load(f)
    except FileNotFoundError:
        messagebox.showerror("Error", f"'{CONFIG_FILE}' no encontrado. Ejecuta 'config_tool.py' primero.")
        return
    export_config = read_export_config(start_note_path)
    vault_path = find_vault_for_note(config["vault_paths"], start_note_path)
    if not vault_path:
        messagebox.showerror("Error", f"La nota '{start_note_path.name}' no está en ningún vault configurado.")
        return
    exporter = ONEExporter(vault_path, Path(config["export_dir"]), config.get("exclude_folders", []))
    exporter.build_package(start_note_path, export_config)
    output_formats = export_config.get('formats', [])
    if output_formats and 'md' not in [f.lower() for f in output_formats]:
        exporter.convert_package(output_formats)
        final_message = f"Proceso completado.\n\nPaquete de exportación en:\n{exporter.export_root}"
        if any(f in ['pdf', 'docx', 'epub'] for f in output_formats):
            final_message += f"\n\nDocumentos convertidos en:\n{exporter.export_root / OUTPUT_SUBFOLDER_NAME}"
        messagebox.showinfo("Éxito", final_message)
    else:
        messagebox.showinfo("Éxito", f"Paquete de exportación construido (sin conversión).\n\nUbicación:\n{exporter.export_root}")

if __name__ == "__main__":
    main()