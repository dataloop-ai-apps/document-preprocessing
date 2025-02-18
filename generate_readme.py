import os
import json


def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def find_readmes(base_path):
    readmes = {}
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower() == "readme.md" and root != base_path:
                if "env" not in root.lower():
                    readmes[root] = read_file(os.path.join(root, file))
    return readmes


def write_main_readme(main_readme_path, readmes, manifest_data, base_path):
    with open(main_readme_path, "w", encoding="utf-8") as file:
        file.write(
            "# Dataloop Documents Preprocessing Applications 📄✨\n\n"
            "Welcome to the Documents Preprocessing Applications repository for the [Dataloop platform](https://dataloop.ai/)! 🎉 Here, you'll find a suite of powerful tools designed to transform and manage your document files with ease. "
            "Whether you're extracting content, chunking text, or sanitizing presentations, our applications are here to streamline your workflow and enhance your data processing capabilities. "
            "Explore more in the [Dataloop Marketplace](https://dataloop.ai/platform/marketplace/) to find additional resources and tools. "
            "Let's dive in and explore the magic of document preprocessing! 🚀\n\n"
            "## Features 🌟\n\n"
            "- **Content Extraction**: Effortlessly extract text from various file formats.\n"
            "- **Text Chunking**: Break down text into manageable chunks with customizable settings.\n\n"
            "# Installations 🛠️\n\n"
            "All apps can be found in the `Marketplace` under the `Applications` tab. Get started today and unlock the full potential of your document data! 📈\n\n"
        )

        for root, content in readmes.items():
            # Determine the path relative to the base path
            relative_path = os.path.relpath(root, base_path)
            path_parts = relative_path.split(os.sep)

            # Construct the summary by using only the last part of the path
            summary = path_parts[-1].replace("_", " ").title()

            file.write("<details>\n")
            file.write(f"<summary>{summary} Documentation</summary>\n\n")
            file.write(content)
            file.write("\n</details>\n\n")

        # Add Dataloop Manifest (DPK) Explanation
        file.write(
            "## Dataloop Manifest (DPK) Explanation 📜\n\n"
            "This section provides an explanation of the [Word to Txt manifest](modules/doc/doc_extract/dataloop.json), which can be used as an example for a *pipeline node* application.\n\n"
            "### Dataloop Applications\n"
            "Dataloop Applications are extensions that integrate seamlessly into the Dataloop ecosystem, providing custom panels, SDK features, and components to enhance your workflow. "
            "For more information, visit the [Dataloop Applications Introduction](https://developers.dataloop.ai/tutorials/applications/introduction/chapter).\n\n"
            "### DPK (Dataloop Package Kit)\n"
            "The DPK is a comprehensive package that includes everything needed for your application to function within the Dataloop platform. "
            "It contains modules, panels, source code, tests, and the `dataloop.json` manifest, which acts as the application's blueprint.\n\n"
            "The Dataloop Manifest (DPK) provides metadata and configuration details for deploying and managing applications on the Dataloop platform. "
            "Here's an explanation of the key components in the manifest:\n\n"
            "- **Name**: The identifier for the application package.\n"
            "- **Display Name**: A user-friendly name for the application.\n"
            "- **Version**: The version of the application package.\n"
            "- **Scope**: Defines the visibility of the application (e.g., public or private).\n"
            "- **Description**: A brief description of the application and its purpose.\n"
            "- **Provider**: The entity or framework providing the application.\n"
            "- **Deployed By**: The organization or platform deploying the application.\n"
            "- **License**: The licensing terms under which the application is distributed.\n"
            "- **Category**: The category or type of application (e.g., Application, Dataset).\n"
            "- **Application Type**: The type of application (e.g., Pipeline Node).\n"
            "- **Media Type**: The type of media the application is designed to process (e.g., Text).\n\n"
            "### Codebase\n"
            "- **Type**: The type of code repository (e.g., git).\n"
            "- **Git Tag**: The specific tag or commit in the repository that corresponds to this version of the application.\n"
            "- **Git URL**: The URL of the git repository containing the application's code.\n\n"
            "All codebase information can be removed if you are publishing local code.\n\n"
            "### Components\n"
            "#### Compute Configurations\n"
            "Defines the computational resources and settings required to run the application, including pod type, concurrency, and autoscaling settings. "
            "Here is an example of one configuration, but more than one can be defined:\n\n"
        )

        # Example of one compute configuration
        compute_config = manifest_data["components"]["computeConfigs"][0]
        file.write(
            f"- **Name**: {compute_config['name']}\n"
            f"  - **Pod Type**: The type of pod used for deployment (e.g., regular-xs, gpu-t4).\n"
            f"  - **Concurrency**: The number of concurrent executions allowed.\n"
            f"  - **Runner Image**: The Docker image used to run the application.\n"
            f"  - **Autoscaler Type**: The type of autoscaler used (e.g., rabbitmq).\n"
            f"  - **Min Replicas**: The minimum number of pod replicas.\n"
            f"  - **Max Replicas**: The maximum number of pod replicas.\n"
            f"  - **Queue Length**: The length of the queue for processing tasks.\n\n"
        )

        file.write("#### Modules\n")
        for module in manifest_data["components"]["modules"]:
            file.write(
                f"- **Name**: {module['name']}\n"
                f"  - **Entry Point**: The main script or module to execute.\n"
                f"  - **Class Name**: The class within the entry point that implements the application logic.\n"
                f"  - **Compute Config**: The compute configuration associated with this module.\n"
                f"  - **Description**: A description of the module's functionality.\n\n"
            )

        file.write("#### Pipeline Nodes\n")
        for node in manifest_data["components"]["pipelineNodes"]:
            file.write(
                f"- **Name**: {node['name']}\n"
                f"  - **Display Name**: {node['displayName']}\n"
                f"  - **Description**: {node['description']}\n"
                f"  - **Scope**: {node['scope']}\n"
                f"  - **Categories**: {', '.join(node['categories'])}\n"
                f"  - **Configuration**:\n"
                f"    This section defines the inputs to the node. The 'Node Name' is always required for identification, while other fields are case-specific and can be edited as needed. "
                f"In this example, there are two additional fields:\n"
                f"    - **Node Name**: The name of the node, used for identification.\n"
                f"    - **Remote Path for Extractions**: The path where extracted files will be stored.\n"
                f"    - **Extract Tables**: A boolean indicating whether to extract tables from documents.\n\n"
            )

        file.write(
            "## Contributions 🤝\n\n"
            "Help us improve! We welcome any contributions and suggestions to this repository.\n"
            "Feel free to open an issue for bug reports or feature requests.\n"
        )


def main():
    base_path = "modules"
    main_readme_path = "README.md"
    readmes = find_readmes(base_path)

    # Load the manifest data
    manifest_path = "modules/doc/doc_extract/dataloop.json"
    with open(manifest_path, "r", encoding="utf-8") as manifest_file:
        manifest_data = json.load(manifest_file)

    write_main_readme(main_readme_path, readmes, manifest_data, base_path)


if __name__ == "__main__":
    main()
