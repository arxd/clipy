from sphinx_markdown_builder.builder import MarkdownBuilder
from sphinx_markdown_builder.translator import MarkdownTranslator

class MyTranslator(MarkdownTranslator):
    def visit_mermaid(self, node):
        self.add("```mermaid\n" + node['code'] + "\n```\n\n")

def setup(app):
    MarkdownBuilder.default_translator_class = MyTranslator
