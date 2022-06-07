## Robot Frmework LibTOC

## What it does
This tool generates docs using Robot Framework [Libdoc](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#libdoc) for an entire folder with Robot Framework resources/libs and creates a TOC (Table of Content) file for them

## Why use it
The Robot Framework Libdoc tool normally generates a HTML file for a single keyword library or a resource file.
If you have several keyword libraries, you just get several separate HTML files.

This tool collects separate keyword documentation files in one place and creates a TOC (Table of content) page
with links to these files.   
The result is a folder with several static HTML pages which can be placed somewhere 
in the intranet or uploaded as CI artifact - so everybody can easily access the keywords docs.

### Here is the example screenshot
![](Screenshot.png)

## How it works
- The tool goes through the specified folder with RF resources and it's **direct** subfolders
- It looks for the **config files** named `.libtoc` which contain:
    1. Paths to resource files in [glob format](https://en.wikipedia.org/wiki/Glob_(programming)) which you would like to create docs for
    2. Installed RF libraries (names and necessary params like described in [libdoc user guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#general-usage))
- Then it gererates the docs using `libdoc` - both for files paths, resolved from the glob patterns, and for the installed libraries. The created HTML files are places in the **libtoc output_dir** - keeping the original subfolder structure of resources
- Finally it generates a **TOC (Table of Contents)** HTML page with links to all the generated HTML files.
 The navigation tree structure in the TOC repeats the folder tree structure.
## Example of a `.libtoc` config file
```
[paths]
# Use glob patterns
**/*.robot
**/*.resource
**/*.py

[libs]
# Use RF library names with params - like for libdoc
SeleniumLibrary
Remote::http://10.0.0.42:8270
```
## How to install it
### System requirements
- Python >=3.9
- Robot Framework
### Installation using pip
```shell
pip install robotframework-libtoc
```

## How to use it
- Create the `.libtoc` config files in subfolders where you need docs to be created.
    > A config file directly in the root of the resources folder is valid, but not mandatory.
- Run `libtoc`. The last `resources_dir` parameter is mandatory, others are optional:
    - `-d, --output_dir`
    - `-c, --config_file`
    - `-t, --toc_file`

    Examples:
    ```shell
    libtoc example_resources
    libtoc --output_dir docs example_resources
    libtoc --output_dir docs --toc_file my_special_docs.html example_resources
    ```

- Open the created file, e.g. `docs\keyword_docs.html`

## How to change the TOC and the homepage HTML
The HTML templates are located directly in the python source code - see functions `toc` and `homepage`.