import argparse
import glob
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import importlib_resources
import robot.libdoc


class LibdocException(Exception):
    def __init__(self, broken_file):
        self.broken_file = broken_file


def toc(links, timestamp, home_page_path, template_file="", search_index=None):
    """
    Returns a HTML source code for TOC (table of contents) page, based on the template and including
    the provided `links`, generation `timestamp` and the `home_page_path` HTML file as a landing page.
    """
    if template_file == "":
        template_file = os.path.join(os.path.dirname(__file__), "toc_template.html")
    with open(template_file, encoding="utf8") as f:
        html_template = f.read()

    result = html_template.replace("{}", home_page_path, 1)
    result = result.replace("{}", links, 1)
    result = result.replace("{}", timestamp, 1)

    # inject search index data (done after format() to avoid brace escaping issues)
    if search_index is not None:
        search_json = json.dumps(search_index, ensure_ascii=False)
        search_json = search_json.replace("</script>", r"<\/script>")
        result = result.replace("SEARCH_INDEX_DATA", search_json)
    else:
        result = result.replace("SEARCH_INDEX_DATA", "[]")

    return result


def homepage(template_file=""):
    """
    Returns a HTML source code for a landing page, based on the template.
    """
    if template_file == "":
        template_file = os.path.join(
            os.path.dirname(__file__), "homepage_template.html"
        )
    with open(template_file, encoding="utf_8") as f:
        return f.read()


def read_config(config_file):
    """
    Parses the content of the `config_file` and returns a dictionary `{"paths":[values], "libs":[values]}`.

    The `paths` values are glob patterns, which can be resolved in real paths and used for generating docs using `libdoc`.
    The `libs`  values are names of Robot Framework libraries with necessary import params - in the way to be also used for docs generation using `libdoc`.

    The config file must be formatted like this:
    ```
    # Comments starting with # are ignored
    [Paths]
    *.resource
    **/my_subfolder/*.py

    [Libs]
    SeleniumLibrary
    SomeLibrary::some_import_param
    ```
    """
    sections = {
        "paths": {"markers": ["[paths]"], "values": []},
        "packages": {"markers": ["[packages]"], "values": []},
        "libs": {"markers": ["[libs]", "[libraries]"], "values": []},
    }

    with open(config_file, encoding="utf8") as f:
        section_to_add = ""
        lines = f.readlines()
        for line in lines:
            stripped_line = line.strip()
            if len(stripped_line) > 0:
                if not stripped_line.startswith("#"):  # comments
                    skip_line = False
                    for section_name, section_content in sections.items():
                        if stripped_line.lower() in section_content["markers"]:
                            section_to_add = section_name
                            skip_line = True
                            break
                    if not skip_line and section_to_add:
                        sections[section_to_add]["values"].append(stripped_line)

    return {
        "paths": sections["paths"]["values"],
        "packages": sections["packages"]["values"],
        "libs": sections["libs"]["values"],
    }


def extract_libdoc_data(html_file_path):
    """
    Extracts the libdoc JSON data from a generated libdoc HTML file.
    The libdoc variable is embedded as a JSON object in a script tag.
    """
    with open(html_file_path, encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("libdoc") and '"specversion"' in stripped:
            json_start = stripped.index("{")
            json_str = stripped[json_start:]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse libdoc JSON (for global searches) in file {html_file_path}")
    return None


def build_search_index(src_dir, base_dir):
    """
    Builds a search index from all libdoc HTML files in src_dir.
    Returns a list of library/resource entries with their keywords.
    """
    index = []
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames.sort()
        for file_name in sorted(filenames):
            if file_name.endswith(".html") and file_name != "homepage.html":
                file_path = os.path.join(dirpath, file_name)
                data = extract_libdoc_data(file_path)
                if data:
                    rel_path = os.path.relpath(file_path, base_dir)
                    rel_path = rel_path.replace("\\", "/")
                    keywords = []
                    for kw in data.get("keywords", []):
                        args_list = []
                        for a in kw.get("args", []):
                            if isinstance(a, str):
                                args_list.append(a)
                            elif isinstance(a, dict):
                                args_list.append(
                                    a.get("repr", a.get("name", ""))
                                )
                        keywords.append(
                            {
                                "name": kw.get("name", ""),
                                "args": ", ".join(args_list),
                                "shortdoc": kw.get("shortdoc", ""),
                                "tags": kw.get("tags", []),
                            }
                        )
                    doc_text = re.sub(r"<[^>]+>", "", data.get("doc", ""))
                    # file_name without .html extension for file searching
                    name_without_ext = os.path.splitext(file_name)[0]
                    index.append(
                        {
                            "name": data.get("name", ""),
                            "fileName": name_without_ext,
                            "path": rel_path,
                            "doc": doc_text,
                            "type": data.get("type", ""),
                            "keywords": keywords,
                        }
                    )
    return index


def inject_libtoc_script(src_dir):
    """
    Injects a small <script> into each libdoc HTML file in src_dir that:
    - Reads the theme from localStorage and applies data-theme on <html> so the
      page respects the libtoc theme choice even when file:// cross-origin prevents
      parent frame DOM access.
    - Opens all external links (http/https/ftp/protocol-relative) in a new tab via
      a click event listener, so dynamically-rendered links are handled correctly.
    - Forwards Ctrl+K / Cmd+K keypresses to the parent frame to open the libtoc search.
    """
    libtoc_script = (
        '\n<script>!function(){var t=localStorage.getItem("libtoc-theme")'
        '||(window.matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");'
        'document.documentElement.setAttribute("data-theme",t);'
        'document.addEventListener("DOMContentLoaded",function(){'
        'document.documentElement.setAttribute("data-theme",t)});'
        'document.addEventListener("click",function(e){'
        'var el=e.target.closest("a");'
        'if(el){var h=el.getAttribute("href");'
        'if(h&&/^(https?:|ftp:\\/\\/|\\/\\/)/i.test(h)){'
        'e.preventDefault();'
        'window.open(h,"_blank","noopener,noreferrer")}}});'
        'document.addEventListener("keydown",function(e){'
        'if((e.ctrlKey||e.metaKey)&&e.key==="k"){'
        'e.preventDefault();'
        'window.parent.postMessage("libtoc-open-search","*")}})'
        '}()</script>\n'
    )
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames.sort()
        for file_name in sorted(filenames):
            if file_name.endswith(".html") and file_name != "homepage.html":
                file_path = os.path.join(dirpath, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Insert before </head> - uses DOMContentLoaded + setTimeout
                # to override libdoc's own theme initialization
                if "libtoc-theme" not in content:
                    content = content.replace("</head>", libtoc_script + "</head>", 1)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)


def add_files_from_folder(folder, base_dir_path, root=True):
    """
    Creates a HTML source code with links to all HTML files in the `folder` and all it's subfolders.
    The links contain file paths relative to the `base_dir_path`.

    The `root` parameter is needed for internal usage only - it's set to False during deeper recursive calls.
    """
    result_str = ""
    if not root:  # means we're in the root - no collapsible need in this case
        result_str += """<button class="collapsible">{}</button>
        """.format(
            os.path.basename(folder)
        )

        result_str += """<div class="collapsible_content">
        """

    for item in sorted(os.listdir(folder)):
        item_path = os.path.abspath(os.path.join(folder, item))
        if item.endswith(".html"):
            name_without_ext = os.path.splitext(item)[0]
            result_str += """<a class="link_not_selected" href="{}" target="targetFrame">{}</a>
            """.format(
                os.path.relpath(item_path, base_dir_path), name_without_ext
            )
        else:
            if os.path.isdir(item_path):
                result_str += add_files_from_folder(
                    item_path, base_dir_path, root=False
                )

    if not root:
        # end of the "collapsible_content"
        result_str += """</div>
    """
    return result_str


def create_docs_for_dir(resource_dir, output_dir, config_file):
    """
    Creates HTML docs using Robot Framework module `libdoc` for all resources and libraries in the `resource_dir`.
    Generated files are placed inside the `output_dir`, keeping the original subfolder tree structure.

    Paths of resource/python files and libraries, which the docs should be generated for, are configured using the `config_file`.

    The `config_file` must be formatted like this:
    ```
    # Comments starting with # are ignored
    [Paths]
    *.resource
    **/my_subfolder/*.py

    [Libs]
    SeleniumLibrary
    SomeLibrary::some_import_param
    ```
    """
    target_dir = os.path.join(
        os.path.abspath(output_dir), os.path.basename(resource_dir)
    )
    doc_config = read_config(config_file)

    resource_path_patterns = doc_config["paths"]
    if resource_path_patterns:
        print(">> Processing paths")
    broken_files = []
    for path_pattern in resource_path_patterns:
        for real_path in glob.glob(
            os.path.join(resource_dir, path_pattern), recursive=True
        ):
            relative_path = os.path.relpath(real_path, resource_dir)
            target_path = os.path.join(
                target_dir, relative_path.rpartition(".")[0] + ".html"
            )
            print(f">>> Processing file: {relative_path}")
            return_code = robot.libdoc.libdoc(real_path, target_path, quiet=True)
            if return_code > 0:
                broken_files.append(relative_path)

    package_definitions = doc_config["packages"]
    if package_definitions:
        print("---")
    packages = {}
    broken_packages = []
    for package_definition in package_definitions:
        package_name, path_pattern = package_definition.split(":", 1)
        if package_name not in packages:
            packages[package_name] = []
        packages[package_name].append(path_pattern)

    for package_name, paths_patterns in packages.items():
        print(f">> Processing package: {package_name}")
        try:
            package_anchor = importlib_resources.files(package_name)
        except ModuleNotFoundError as e:
            print(f"Importing package '{package_name}' failed: {e}")
            broken_packages.append(package_name)
        else:
            with importlib_resources.as_file(package_anchor) as package_path:
                for path_pattern in paths_patterns:
                    package_resource_files = package_path.glob(path_pattern)
                    for real_path in package_resource_files:
                        relative_path = Path(package_name) / real_path.relative_to(
                            package_path
                        )
                        target_path = os.path.join(
                            target_dir, relative_path.with_suffix(".html")
                        )
                        print(f">>> Processing file: {relative_path}")
                        return_code = robot.libdoc.libdoc(
                            real_path, target_path, quiet=True
                        )
                        if return_code > 0:
                            broken_packages.append(relative_path)

    libs = doc_config["libs"]
    if libs:
        print("---")
        print(">> Processing libraries")
    broken_libs = []
    for lib in libs:
        lib_str_with_resolved_vars = os.path.expandvars(lib)
        target_path = os.path.join(
            target_dir, lib_str_with_resolved_vars.partition("::")[0] + ".html"
        )
        print(f">>> Processing lib: {lib_str_with_resolved_vars}")
        return_code = robot.libdoc.libdoc(
            lib_str_with_resolved_vars, target_path, quiet=True
        )
        if return_code > 0:
            broken_libs.append(lib_str_with_resolved_vars)
    return broken_files, broken_packages, broken_libs


def create_toc(
    html_docs_dir,
    toc_file="keyword_docs.html",
    homepage_file="homepage.html",
    toc_template="",
    homepage_template="",
):
    """
    Generates a `toc_file` (Table of Contents) HTML page with links to all HTML files inside the `html_docs_dir` and all it's subfolders.

    The navigation tree structure in the TOC repeats the folder tree structure.
    It also creates a `homepage_file` shown as a landing page when opening the TOC.

    All the content of the `html_docs_dir` will be moved in the new `src` subfolder, leaving only the `toc_file` directly inside.
    """
    print(f"> Creating TOC in: {os.path.abspath(html_docs_dir)}")
    # move all subfolders and files into "src"
    src_subdir = os.path.join(html_docs_dir, "src")
    os.makedirs(src_subdir, exist_ok=True)
    all_docs = os.listdir(html_docs_dir)
    for doc_element in all_docs:
        if doc_element == "src":
            continue
        src = os.path.join(html_docs_dir, doc_element)
        target = os.path.join(src_subdir, doc_element)
        shutil.move(src, target)

    # create homepage in "src"
    homepage_path = os.path.join(src_subdir, homepage_file)
    current_date_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    doc_files_links = add_files_from_folder(src_subdir, os.path.abspath(html_docs_dir))
    with open(homepage_path, "w", encoding="utf8") as f:
        f.write(homepage(homepage_template))

    # build search index from generated docs
    search_index = build_search_index(src_subdir, os.path.abspath(html_docs_dir))

    # inject libtoc script into all libdoc HTML files
    inject_libtoc_script(src_subdir)

    # create TOC
    toc_file_path = os.path.join(html_docs_dir, toc_file)
    with open(toc_file_path, "w", encoding="utf8") as f:
        f.write(
            toc(
                doc_files_links,
                current_date_time,
                os.path.relpath(homepage_path, os.path.abspath(html_docs_dir)),
                toc_template,
                search_index,
            )
        )

    print("---")
    print("TOC finished. Output file: {}".format(os.path.abspath(toc_file_path)))


def main():
    parser = argparse.ArgumentParser(
        description="Generates keyword docs using libdoc based on config files in direct subfolders of the resources dir and creates a TOC"
    )
    parser.add_argument(
        "resources_dirs", nargs="+", help="Folders with resources and keywords files"
    )
    parser.add_argument(
        "-d", "--output_dir", default="docs", help="Folder to create the docs in"
    )
    parser.add_argument(
        "--config_file",
        default=".libtoc",
        help="File in each folder with docs generation configs",
    )
    parser.add_argument(
        "--toc_file", default="keyword_docs.html", help="Name of the TOC file generated"
    )
    parser.add_argument(
        "--toc_template", default="", help="Custom HTML template for the TOC file"
    )
    parser.add_argument(
        "--homepage_template",
        default="",
        help="Custom HTML template for the homepage file",
    )
    parser.add_argument(
        "-P",
        "--pythonpath",
        default="",
        help="Additional locations where to search for libraries and resources similarly as when running tests",
    )

    args = parser.parse_args()

    if args.pythonpath:
        sys.path.insert(0, args.pythonpath)

    if os.path.isdir(args.output_dir):
        print(f"Output dir already exists, deleting it: {args.output_dir}")
        shutil.rmtree(args.output_dir)
    total_broken_files = []
    total_broken_packages = []
    total_broken_libs = []

    for resources_dir in args.resources_dirs:
        print("")
        print(f"> Creating docs for dir: {os.path.abspath(resources_dir)}")
        for child_element in os.listdir(resources_dir):
            child_element_path = os.path.join(resources_dir, child_element)
            current_broken_files = []
            current_broken_packages = []
            current_broken_libs = []
            if os.path.isdir(child_element_path):
                config_file = os.path.join(child_element_path, args.config_file)
                if os.path.isfile(config_file):
                    (
                        current_broken_files,
                        current_broken_packages,
                        current_broken_libs,
                    ) = create_docs_for_dir(
                        child_element_path,
                        args.output_dir,
                        os.path.abspath(config_file),
                    )
            elif child_element == args.config_file:
                current_broken_files, current_broken_packages, current_broken_libs = (
                    create_docs_for_dir(
                        resources_dir,
                        args.output_dir,
                        os.path.abspath(os.path.join(resources_dir, args.config_file)),
                    )
                )

            total_broken_files += current_broken_files
            total_broken_packages += current_broken_packages
            total_broken_libs += current_broken_libs

    if total_broken_files:
        print("")
        print(
            f"---> !!! Errors occurred while generating docs for {len(total_broken_files)} files (see details above):"
        )
        for f in total_broken_files:
            print(f"         - {f}")

    if total_broken_packages:
        print("")
        print(
            f"---> !!! Errors occurred while generating docs for {len(total_broken_packages)} packages (see details above):"
        )
        for f in total_broken_packages:
            print(f"         - {f}")

    if total_broken_libs:
        print("")
        print(
            f"---> !!! Errors occurred while generating docs for {len(total_broken_libs)} libs (see details above):"
        )
        for l in total_broken_libs:
            print(f"         - {l}")

    if os.path.isdir(args.output_dir):
        print("")
        create_toc(
            args.output_dir,
            args.toc_file,
            toc_template=args.toc_template,
            homepage_template=args.homepage_template,
        )
    else:
        print("No docs were created!")

    print("")


if __name__ == "__main__":
    main()
