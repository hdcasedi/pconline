from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.admin.rich_text.editors.draftail.features import InlineStyleFeature

@hooks.register("register_rich_text_features")
def register_underline(features):
    feature_name = "underline"
    type_ = "UNDERLINE"
    tag = "u"

    control = {
        "type": type_,
        "label": "U",
        "description": "Underline",
        "element": tag,
    }
    features.register_editor_plugin("draftail", feature_name, InlineStyleFeature(control))
    features.register_converter_rule("contentstate", feature_name, {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {"style_map": {type_: tag}},
    })
    if "underline" not in features.default_features:
        features.default_features.append("underline")
