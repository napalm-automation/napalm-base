import napalm_yang

import yaml
import re


def translate_string(string, **kwargs):
    if string:
        return string.format(**kwargs)
    else:
        return ""


class TextTranslator:

    def translate(self, model):
        with open("napalm_eos/openconfig_translation.yaml", "r") as f:
            translation_map = yaml.load(f.read())["interfaces"]

        return self._translate_yang_model(model, translation_map)

    def _translate_yang_model(self, model, translation_map):
        translation = ""
        for k, v in model.items():
            if issubclass(v.__class__, napalm_yang.List):
                translation += self._yang_translate_list(v, translation_map[k])
            else:
                if issubclass(v.__class__, napalm_yang.BaseBinding):
                    if not v._meta["config"]:
                        continue
                    translation += self._translate_yang_model(getattr(model, k), translation_map[k])
                translation += self._yang_translate_string(translation_map[k].get("_string", ""),
                                                           value=getattr(model, k))
                translation += self._yang_translate_map(translation_map[k].get("_map", {}),
                                                        value=getattr(model, k))
        return translation

    def _yang_translate_list(self, l, translation_map):
        translation = ""
        for element_key, element_data in l.items():
            translation += self._yang_translate_string(translation_map.get("_string", ""),
                                                       key=element_key)
            translation += self._translate_yang_model(element_data, translation_map)

        return translation

    def _yang_translate_map(self, m, value, **kwargs):
        if m:
            return self._yang_translate_string(m[str(value)]["_string"], value=value, **kwargs)
        else:
            return ""

    def _yang_translate_string(self, string, **kwargs):
        if string:
            return string.format(**kwargs)
        else:
            return ""


class TextExtractor:

    def __init__(self):
        self.key = None

    def populate(self, model, config):
        with open("napalm_eos/openconfig_mappings.yaml", "r") as f:
            oc_mappings = yaml.load(f.read())

        self.parse_text(model, config, config, oc_mappings["interfaces"])

    def parse_text(self, model, config, partial_config, mappings):
        for k, v in model.items():
            if issubclass(v.__class__, napalm_yang.List):
                self.parse_text_to_list(v, config, mappings[k])
            elif issubclass(v.__class__, napalm_yang.BaseBinding):
                if v._meta["config"]:
                    self.parse_text(v, config, partial_config, mappings[k])
            else:
                self.parse_text_to_attr(v, partial_config, mappings[k])

    def parse_text_to_list(self, model, config, mappings):
        regexp = translate_string(mappings["_block_capture"], parent_key=self.key)
        block_matches = re.finditer(regexp, config, re.MULTILINE)

        for match in block_matches:
            name = match.group("key")
            self.key = name
            block_config = match.group("block")

            obj = model.get_element(name)

            self.parse_text(obj, config, block_config, mappings)

    def parse_text_to_attr(self, attr, config, mappings):
        regexp = translate_string(mappings["_search"], parent_key=self.key)
        match = re.search(regexp, config, re.MULTILINE)

        if mappings["_type"] == "boolean":
            attr(match is not None)
            return

        if match:
            if mappings["_type"] == "mapping":
                value = mappings["_map"][match.group("value")]
            else:
                value = match.group("value")
        else:
            value = mappings["_default"]

        try:
            attr(value)
        except ValueError:
            attr(eval(value))
