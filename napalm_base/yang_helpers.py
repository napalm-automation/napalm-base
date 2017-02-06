import napalm_yang

import re


def translate_string(string, **kwargs):
    if string:
        return string.format(**kwargs)
    else:
        return ""


class TextTranslator:

    def translate(self, obj, translation_map, previous=None):
        return self._translate_yang_model(obj, translation_map, previous, None, None)

    def _translate_yang_model(self, obj, translation_map, previous, key, parent_key):
        translation = ""
        for k, v in obj.items():
            previous_v = getattr(previous, k) if previous is not None else None
            if issubclass(v.__class__, napalm_yang.List):
                translation += self._yang_translate_list(v, translation_map[k], previous_v, key)
            else:
                if issubclass(v.__class__, napalm_yang.BaseBinding):
                    if not v._meta["config"]:
                        continue
                    translation += self._translate_yang_model(getattr(obj, k), translation_map[k],
                                                              previous_v, key, parent_key)
                translation += self._yang_translate_string(translation_map[k].get("_string", ""),
                                                           value=getattr(obj, k), key=key,
                                                           parent_key=parent_key)
                translation += self._yang_translate_map(translation_map[k].get("_map", {}),
                                                        value=getattr(obj, k), key=key,
                                                        parent_key=parent_key)
        return translation

    def _yang_translate_list(self, l, translation_map, previous, parent_key):
        translation = ""

        if previous is not None:
            for k in previous.keys():
                if k not in l.keys():
                    translation += translate_string(translation_map.get("_remove", ""),
                                                    key=k)

        for element_key, element_data in l.items():
            previous_element = previous.get(element_key, None) if previous is not None else None

            translation += self._yang_translate_string(translation_map.get("_string", ""),
                                                       key=element_key, parent_key=parent_key)
            translation += self._translate_yang_model(element_data, translation_map,
                                                      previous_element, element_key, parent_key)

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

    def populate(self, model, config, mappings):
        self.parse_text(model, config, config, mappings)

    def parse_text(self, model, config, partial_config, mappings):
        for k, v in model.items():
            if issubclass(v.__class__, napalm_yang.List):
                self.parse_text_to_list(v, config, partial_config, mappings[k])
            elif issubclass(v.__class__, napalm_yang.BaseBinding):
                if v._meta["config"]:
                    self.parse_text(v, config, partial_config, mappings[k])
            else:
                self.parse_text_to_attr(v, partial_config, mappings[k])

    def parse_text_to_list(self, model, config, partial_config, mappings):
        if "_block_capture" in mappings.keys():
            regexp = translate_string(mappings["_block_capture"], parent_key=self.key)
            block_matches = re.finditer(regexp, config, re.MULTILINE)
        elif "_subblock_capture" in mappings.keys():
            regexp = translate_string(mappings["_subblock_capture"], parent_key=self.key)
            block_matches = re.finditer(regexp, partial_config, re.MULTILINE)

        for match in block_matches:
            name = match.group("key")
            self.key = name
            block_config = match.group("block")

            obj = model.get_element(name)

            self.parse_text(obj, config, block_config, mappings)

    def parse_text_to_attr(self, attr, config, mappings):
        if mappings["_type"] == "boolean":
            if "_absent" in mappings.keys():
                regexp = translate_string(mappings["_absent"], parent_key=self.key)
                match = re.search(regexp, config, re.MULTILINE)
                attr(match is None)
            elif "_present" in mappings.keys():
                regexp = translate_string(mappings["_present"], parent_key=self.key)
                match = re.search(regexp, config, re.MULTILINE)
                attr(match is not None)

            return
        else:
            regexp = translate_string(mappings["_search"], parent_key=self.key)
            match = re.search(regexp, config, re.MULTILINE)

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
