from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.contrib.table_block.blocks import TableBlock


class StyledTableBlock(TableBlock):
    template = "exo/blocks/styled_table.html"


class ExoContentBlock(blocks.StreamBlock):
    """Blocs de contenu pour les exercices"""
    rich_text = blocks.RichTextBlock(
        features=['h2', 'h3', 'h4', 'bold', 'italic', 'link', 'ol', 'ul', 'code', 'blockquote'],
        label="Texte riche"
    )
    image = blocks.StructBlock([
        ('image', ImageChooserBlock(label="Image")),
        ('caption', blocks.CharBlock(required=False, label="Légende")),
    ], label="Image")
    code = blocks.StructBlock([
        ('language', blocks.ChoiceBlock(choices=[
            ('python', 'Python'), ('javascript', 'JavaScript'),
            ('html', 'HTML'), ('css', 'CSS'), ('sql', 'SQL'),
            ('bash', 'Bash'), ('json', 'JSON'), ('xml', 'XML'),
        ], default='python', label="Langage")),
        ('source', blocks.TextBlock(label="Code")),
    ], label="Code")
    table = StyledTableBlock(label="Tableau")
    # Sections disponibles dans les questions et solutions
    section_50_50 = blocks.StructBlock([
        ('left', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne gauche")),
        ('right', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne droite")),
    ], template="exo/blocks/section_content_50_50.html", label="Section 50/50")
    section_70_30 = blocks.StructBlock([
        ('left', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne gauche (70%)")),
        ('right', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne droite (30%)")),
    ], template="exo/blocks/section_content_70_30.html", label="Section 70/30")
    section_75_25 = blocks.StructBlock([
        ('left', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne gauche (75%)")),
        ('right', blocks.RichTextBlock(features=['bold', 'italic', 'link', 'ol', 'ul', 'code'], label="Colonne droite (25%)")),
    ], template="exo/blocks/section_content_75_25.html", label="Section 75/25")

    class Meta:
        template = "exo/blocks/exo_content.html"


class EnonceBlock(blocks.StructBlock):
    """Bloc pour le contenu d'énoncé"""
    content = ExoContentBlock(label="Contenu")

    class Meta:
        template = "exo/blocks/enonce.html"
        icon = "doc-full"
        label = "Énoncé"


class Section100Block(blocks.StructBlock):
    """Section pleine largeur"""
    content = ExoContentBlock(label="Contenu")

    class Meta:
        template = "exo/blocks/section_100.html"
        icon = "arrows-up-down"
        label = "Section 100%"


class Section50_50Block(blocks.StructBlock):
    """Section deux colonnes équilibrées"""
    left = ExoContentBlock(label="Colonne gauche")
    right = ExoContentBlock(label="Colonne droite")

    class Meta:
        template = "exo/blocks/section_50_50.html"
        icon = "arrows-left-right"
        label = "Section 50/50"


class Section70_30Block(blocks.StructBlock):
    """Section gauche 70% / droite 30%"""
    left = ExoContentBlock(label="Colonne gauche (70%)")
    right = ExoContentBlock(label="Colonne droite (30%)")

    class Meta:
        template = "exo/blocks/section_70_30.html"
        icon = "arrows-left-right"
        label = "Section 70/30"


class Section75_25Block(blocks.StructBlock):
    """Section gauche 75% / droite 25%"""
    left = ExoContentBlock(label="Colonne gauche (75%)")
    right = ExoContentBlock(label="Colonne droite (25%)")

    class Meta:
        template = "exo/blocks/section_75_25.html"
        icon = "arrows-left-right"
        label = "Section 75/25"


class QuestionBlock(blocks.StructBlock):
    """Bloc pour une question"""
    numero = blocks.CharBlock(
        help_text="Numéro libre : 1, 2, 3 ou 4.a, 4.b, etc.",
        label="Numéro"
    )
    content = ExoContentBlock(label="Contenu de la question")
    points = blocks.DecimalBlock(
        max_digits=5,
        decimal_places=2,
        help_text="ex : 0.25 (affiché 0,25)",
        label="Points"
    )
    fc = blocks.BooleanBlock(
        required=False,
        help_text="Flashcard",
        label="Flashcard"
    )
    solution = ExoContentBlock(
        required=False,
        label="Solution"
    )

    class Meta:
        template = "exo/blocks/question.html"
        icon = "help"
        label = "Question"
