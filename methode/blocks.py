from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.contrib.table_block.blocks import TableBlock


# Bloc de compatibilité avec anciennes migrations
class StyledRichTextBlock(blocks.RichTextBlock):
    class Meta:
        icon = "doc-full"
        label = "Texte riche (stylé)"


# Bloc paragraphe avec styles (inspiré de cours)
class ParagrapheBlock(blocks.StructBlock):
    style = blocks.ChoiceBlock(
        choices=[
            ('normal', 'Normal'),
            ('etape', 'Étape avec titre'),
            ('protocole', 'Protocole'),
            ('exemple', 'Exemple'),
            ('methode', 'Méthode'),
        ],
        default='normal',
        label="Style",
    )
    contenu = blocks.RichTextBlock(
        features=[
            'h2', 'h3', 'bold', 'italic', 'underline', 'link',
            'superscript', 'subscript', 'strikethrough', 'ol',
            'ul', 'hr', 'blockquote', 'code', 'image', 'embed'
        ],
        label="Contenu",
    )
    titre = blocks.CharBlock(required=False, label="Titre (pour étape/exemple/méthode)")

    class Meta:
        template = "methode/blocks/paragraphe.html"
        icon = "doc-full"
        label = "Paragraphe"


# Bloc titre
class TitreBlock(blocks.StructBlock):
    niveau = blocks.ChoiceBlock(
        choices=[('h1', 'H1'), ('h2', 'H2'), ('h3', 'H3')],
        default='h2',
        label="Niveau",
    )
    texte = blocks.CharBlock(label="Texte")

    class Meta:
        template = "methode/blocks/titre.html"
        icon = "title"
        label = "Titre"


# Bloc code
class CodeBlock(blocks.StructBlock):
    langage = blocks.ChoiceBlock(
        choices=[
            ('python', 'Python'), ('javascript', 'JavaScript'),
            ('html', 'HTML'), ('css', 'CSS'),
            ('c', 'C'), ('cpp', 'C++'), ('java', 'Java'),
            ('php', 'PHP'), ('sql', 'SQL'), ('bash', 'Bash'),
        ],
        default='python',
        label="Langage",
    )
    code = blocks.TextBlock(label="Code")

    class Meta:
        template = "methode/blocks/code.html"
        icon = "code"
        label = "Code"


# Bloc image simple
class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True, label="Image")
    caption = blocks.CharBlock(required=False, label="Légende")

    class Meta:
        template = "methode/blocks/image.html"
        icon = "image"
        label = "Image"


# Bloc carte
class CardBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, label="Titre")
    image = ImageChooserBlock(required=False, label="Image")
    text = blocks.RichTextBlock(required=False, label="Texte")

    class Meta:
        template = "methode/blocks/card.html"
        icon = "placeholder"
        label = "Carte"


# Section 2 colonnes (inspiré de cours)
class TwoColsBlock(blocks.StructBlock):
    ratio = blocks.ChoiceBlock(
        choices=[
            ("50-50", "50 / 50"),
            ("70-30", "70 / 30"),
            ("30-70", "30 / 70"),
        ],
        default="50-50",
        label="Disposition"
    )

    left = blocks.StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("image", ImageBlock()),
            ("code", CodeBlock()),
            ("card", CardBlock()),
            ("tableau", TableBlock()),
        ],
        required=False,
        label="Colonne gauche"
    )
    right = blocks.StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("image", ImageBlock()),
            ("code", CodeBlock()),
            ("card", CardBlock()),
            ("tableau", TableBlock()),
        ],
        required=False,
        label="Colonne droite"
    )
    video_url = blocks.URLBlock(required=False, label="URL vidéo")

    class Meta:
        template = "methode/blocks/section_two_cols.html"
        icon = "placeholder"
        label = "Section 2 colonnes"


# Section 3 colonnes
class ThreeColsBlock(blocks.StructBlock):
    col1 = blocks.StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("image", ImageBlock()),
            ("code", CodeBlock()),
            ("card", CardBlock()),
            ("tableau", TableBlock()),
        ],
        required=False,
        label="Colonne 1"
    )
    col2 = blocks.StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("image", ImageBlock()),
            ("code", CodeBlock()),
            ("card", CardBlock()),
            ("tableau", TableBlock()),
        ],
        required=False,
        label="Colonne 2"
    )
    col3 = blocks.StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("image", ImageBlock()),
            ("code", CodeBlock()),
            ("card", CardBlock()),
            ("tableau", TableBlock()),
        ],
        required=False,
        label="Colonne 3"
    )
    video_url = blocks.URLBlock(required=False, label="URL vidéo")

    class Meta:
        template = "methode/blocks/section_three_cols.html"
        icon = "placeholder"
        label = "Section 3 colonnes"




# Bloc principal qui contient tous les blocs disponibles
class MethodeContentBlock(blocks.StreamBlock):
    paragraphe = ParagrapheBlock()
    titre = TitreBlock()
    image = ImageBlock()
    code = CodeBlock()
    card = CardBlock()
    tableau = TableBlock()
    section_2cols = TwoColsBlock()
    section_3cols = ThreeColsBlock()



