import os
import sys
import shutil
import glob
import argparse
from datetime import datetime
import robot.libdoc

def toc(links, timestamp, home_page_path):
    """
    Returns a HTML source code for TOC (Table of Content) page, based on the template and including
    the provided `links`, generation `timestamp` and the `home_page_path` HTML file as a landing page.
    """
    html_template = """
    <html>
    <head>
    <style>
    body { font-family: "Lato", sans-serif;}
    .collapsible { background: none; color: #818181; cursor: pointer; padding: 6px 6px 6px 32px; width: 100%; text-align:
    left; font-size: 16px; border: none;}
    .collapsible:hover { color: white;}
    .collapsible_expanded { color: #818181; }
    .collapsible_content { padding-left: 15px; display: none; overflow: hidden;}
    .sidenav { height: 100%; width: 20%; position: fixed; z-index: 1; top: 0; left: 0; text-align: left;
     background-color: #111; overflow: auto; resize: none;  font-size: 16px;}
    .sidenav a:hover { color: #f1f1f1;}
    .link_not_selected { padding: 6px 6px 6px 32px; text-decoration: none; color: #818181; display: block;}
    .link_selected {padding: 6px 6px 6px 32px; text-decoration: none; color: white; display: block;}    
    .sidenav p { padding: 0px 0px 0px 12px; color: #818181; position: relative; bottom: 0}
    .sidenav_open_button {background: none; cursor: pointer; border:none; font-size: 24px;}
    .sidenav_close_button {background: none; color: white; cursor: pointer; width: 100%; text-align:
    left; border:none; font-size: 30px; padding-top: 5px; padding-left: 15px}
    .main { margin-left: 20%;, height: 100%}
    </style>
    </head>
    <body>
    
    <div id="main" class="main">
    <div>
    <button id="openNav" class="sidenav_open_button" onclick="sidenav_open()" style="display:none">&#9776;</button>
    </div>
    <iframe name="targetFrame" src="{}" allowTransparency="true" frameborder="0" width="100%" height="98%">
    </iframe>
    </div>
    
    <div id="sidenav" class="sidenav">
    <button class="sidenav_close_button" onclick="sidenav_close()">&times;</button>
    <a class="link_not_selected" href="http://robotframework.org/robotframework/" target="targetFrame">Robot Framework Documentation
    </a>
    <a class="link_not_selected" href="http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html" target="targetFrame">SeleniumLibrary</a>
    <hr>
    {}
    <hr>
    <p>
    Created: {}
    </p>
    </div>
    <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;
        for (i = 0; i < coll.length; i++)
        {
            coll[i].addEventListener("click", function()
            {
                this.classList.toggle("collapsible_expanded");
                var content = this.nextElementSibling;
                if (content.style.display === "block")
                {
                    content.style.display = "none";
                }
                else
                {
                    content.style.display = "block";
                }
            });
        }
        
        var leaf_links = document.getElementsByClassName("link_not_selected");
        var i;
        for (i = 0; i < leaf_links.length; i++)
        {
            leaf_links[i].addEventListener("click", function()
            {                
                var active_leaf_links = document.getElementsByClassName("link_selected");
                var j;
                for (j=0; j < active_leaf_links.length; j++)
                {
                    active_leaf_links[j].className = "link_not_selected";
                }                
                this.className = "link_selected";                             
            });
        }
        
        function sidenav_open()
        {
            document.getElementById("main").style.marginLeft = "20%";
            document.getElementById("sidenav").style.width = "20%";
            document.getElementById("sidenav").style.display = "block";
            document.getElementById("openNav").style.display = 'none';
        }
        function sidenav_close()
        {
            document.getElementById("main").style.marginLeft = "0%";
            document.getElementById("sidenav").style.display = "none";
            document.getElementById("openNav").style.display = "inline";
        }
    </script>
    </body>
    </html>
    """

    # double all brackets to make the further formatting work
    html_with_escaped_braces = html_template.replace('{', '{{')
    html_with_escaped_braces = html_with_escaped_braces.replace('}', '}}')

    # and convert the formatting brackets back
    html_with_escaped_braces = html_with_escaped_braces.replace('{{}}', '{}')

    return html_with_escaped_braces.format(home_page_path, links, timestamp)

def homepage(timestamp):
    """
    Returns a HTML source code for a landing page, based on the template and includig the provided `timestamp`.
    """
    html_template = """
    <html>
    <meta charset="utf-8">
    <body style="font-family: 'Lato', sans-serif;">
    <h1>
    Docs for Robot Framework keywords.
    </h1>
    <p>
    Please select a library in the navigation sidebar
    </p>
    <p>
    Created: 
    <b>
    {0}
    </b>
    </p>
    </body>
    </html>
    """
    return html_template.format(timestamp)

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
        "paths": {"markers":["[paths]"], "values":[]},
        "libs":  {"markers": ["[libs]", "[libraries]"], "values":[]}
    }
    
    with open(config_file, encoding="utf8") as f:
        section_to_add = ""
        lines = f.readlines()        
        for line in lines:
            stripped_line = line.strip()
            if len(stripped_line) > 0:
                if not stripped_line.startswith('#'):  # comments
                    skip_line = False
                    for section_name, section_content in sections.items():
                        if stripped_line.lower() in section_content["markers"]:
                            section_to_add = section_name
                            skip_line = True
                            break
                    if not skip_line and section_to_add:
                        sections[section_to_add]["values"].append(stripped_line)
    
    return {"paths": sections["paths"]["values"], "libs": sections["libs"]["values"]}

def add_files_from_folder(folder, base_dir_path, root=True):
    """
    Creates a HTML source code with links to all HTML files in the `folder` and all it's subfolders.    
    The links contain file paths relative to the `base_dir_path`.
    
    The `root` parameter is needed for internal usage only - it's set to False during deeper recursive calls.
    """
    result_str = ""
    if not root:  # means we're in the root - no collapsible need in this case
        result_str += """<button class="collapsible">{}</button>
        """.format(os.path.basename(folder))

        result_str += """<div class="collapsible_content">
        """

    for item in os.listdir(folder):
        item_path = os.path.abspath(os.path.join(folder, item))
        if item.endswith(".html"):
            name_without_ext = item.split('.')[0]            
            result_str += """<a class="link_not_selected" href="{}" target="targetFrame">{}</a>
            """.format(os.path.relpath(item_path, base_dir_path), name_without_ext)
        else:
            if os.path.isdir(item_path):
                result_str += add_files_from_folder(item_path, base_dir_path, root=False)

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
    target_dir = os.path.join(os.path.abspath(output_dir), os.path.basename(resource_dir))
    doc_config = read_config(config_file)
    
    resource_path_patterns = doc_config["paths"]
    for path_pattern in resource_path_patterns:
        for real_path in glob.glob(os.path.join(resource_dir, path_pattern), recursive=True):
            relative_path = os.path.relpath(real_path, resource_dir)
            target_path = os.path.join(target_dir, relative_path.rpartition('.')[0] + ".html")
            print(f">> Generating docs for resource: {relative_path}")
            robot.libdoc.libdoc(real_path, target_path)
            print("")

    libs = doc_config["libs"]
    for lib in libs:
        target_path = os.path.join(target_dir, lib.partition("::")[0] + ".html")
        print(f">> Generating docs for library: {lib}")  
        robot.libdoc.libdoc(lib, target_path)
        print("")

def create_toc(html_docs_dir, toc_file="keyword_docs.html", homepage_file="homepage.html"):
    """
    Generates a `toc_file` (Table of Contents) HTML page with links to all HTML files inside the `html_docs_dir` and all it's subfolders.

    The navigation tree structure in the TOC repeats the folder tree structure.
    It also creates a `homepage_file` shown as a landing page when opening the TOC.

    All the content of the `html_docs_dir` will be moved in the new `src` subfolder, leaving only the `toc_file` directly inside.
    """
    print(f">>> Creating TOC in: {os.path.abspath(html_docs_dir)}")    
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
    current_date_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    doc_files_links = add_files_from_folder(src_subdir, os.path.abspath(html_docs_dir))
    with open(homepage_path, 'w', encoding="utf8") as f:
        f.write(homepage(current_date_time))

    # create TOC
    toc_file_path = os.path.join(html_docs_dir, toc_file)
    with open(toc_file_path, 'w', encoding="utf8") as f:
        f.write(toc(doc_files_links, current_date_time, os.path.relpath(homepage_path, os.path.abspath(html_docs_dir))))
    
    print("Finished. Output file: {}".format(os.path.abspath(toc_file_path)))

def main():
    parser = argparse.ArgumentParser(description="Generates keyword docs using libdoc based on config files in direct subfolders of the resources dir and creates a TOC")
    parser.add_argument("resources_dir", help="Folder with resources and keywords files")
    parser.add_argument("-d", "--output_dir", default="docs", help="Folder to create the docs in")
    parser.add_argument("-c", "--config_file", default=".libtoc", help="File in each folder with docs generation configs")
    parser.add_argument("-t", "--toc_file", default="keyword_docs.html", help="Name of the TOC file generated")

    args = parser.parse_args()

    print(f"Creating docs for: {args.resources_dir}")

    if os.path.isdir(args.output_dir):
        print(f"Output dir already exists, deleting it: {args.output_dir}")
        shutil.rmtree(args.output_dir)

    for child_element in os.listdir(args.resources_dir):                
        if os.path.isdir(child_element):
            subfolder = os.path.join(args.resources_dir, child_element)
            config_file = os.path.join(subfolder, args.config_file)
            if os.path.isfile(config_file):
                create_docs_for_dir(subfolder, args.output_dir, os.path.abspath(config_file))
        elif child_element == args.config_file:
            create_docs_for_dir(args.resources_dir, args.output_dir, os.path.abspath(os.path.join(args.resources_dir, args.config_file)))            
    
    if os.path.isdir(args.output_dir):
        create_toc(args.output_dir, args.toc_file)
    else:
        print("No docs were created!")

if __name__ == "__main__":
    main()