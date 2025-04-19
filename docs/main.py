from pathlib import Path


def define_env(env):
    @env.macro
    def include_readme():
        content = (Path(__file__).parent.parent / "README.md").read_text()
        return content

    @env.macro
    def include_changelog():
        content = (Path(__file__).parent.parent / "CHANGELOG.md").read_text()
        content = content.replace("./README.md", "./index.md")
        return content
