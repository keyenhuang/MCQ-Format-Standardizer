import copy


def create_run_xml(text):
    from docx.oxml import OxmlElement
    r = OxmlElement('w:r')
    t = OxmlElement('w:t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)
    return r


def create_br_xml():
    from docx.oxml import OxmlElement
    r = OxmlElement('w:r')
    br = OxmlElement('w:br')
    r.append(br)
    return r


def get_para_xml_elements(para) -> list:
    elements = []
    for child in para._p:
        if child.tag.endswith('}pPr'):
            continue
        elements.append(copy.deepcopy(child))
    return elements


def strip_xml_prefix(elements: list, count: int) -> None:
    if count <= 0:
        return
    for elem in elements:
        for text_node in elem.iter():
            if text_node.tag.endswith('}t'):
                node_text = text_node.text or ""
                node_len = len(node_text)
                if node_len >= count:
                    text_node.text = node_text[count:]
                    return
                text_node.text = ""
                count -= node_len


def _split_single_node_elem(elem, t_node, sep, current_xml, options_xml):
    t_parts = (t_node.text or "").split(sep)
    t_node.text = t_parts[0]
    current_xml.append(elem)
    options_xml.append(current_xml)
    for part in t_parts[1:-1]:
        new_elem = copy.deepcopy(elem)
        new_t = [t for t in new_elem.iter() if t.tag.endswith('}t')][0]
        new_t.text = part
        options_xml.append([new_elem])
    new_elem = copy.deepcopy(elem)
    new_t = [t for t in new_elem.iter() if t.tag.endswith('}t')][0]
    new_t.text = t_parts[-1]
    return [new_elem]


def _split_multi_node_elem(elem, text_nodes, sep, current_xml, options_xml):
    trailing_texts = [t.text or "" for t in text_nodes]
    first_idx = next((i for i, txt in enumerate(trailing_texts) if sep in txt), None)
    if first_idx is None:
        current_xml.append(elem)
        return current_xml

    parts = trailing_texts[first_idx].split(sep)
    text_nodes[first_idx].text = parts[0]
    for k in range(first_idx + 1, len(text_nodes)):
        text_nodes[k].text = ""
    current_xml.append(elem)
    options_xml.append(current_xml)

    for mid_part in parts[1:-1]:
        mid_elem = copy.deepcopy(elem)
        mid_nodes = [t for t in mid_elem.iter() if t.tag.endswith('}t')]
        for k, node in enumerate(mid_nodes):
            node.text = mid_part if k == first_idx else ""
        options_xml.append([mid_elem])

    tail_elem = copy.deepcopy(elem)
    tail_nodes = [t for t in tail_elem.iter() if t.tag.endswith('}t')]
    for k in range(first_idx):
        tail_nodes[k].text = ""
    tail_nodes[first_idx].text = parts[-1]
    for k in range(first_idx + 1, len(tail_nodes)):
        tail_nodes[k].text = trailing_texts[k]
    return _split_tail_if_needed(tail_elem, sep, options_xml)


def _split_tail_if_needed(elem, sep, options_xml):
    text_nodes = [t for t in elem.iter() if t.tag.endswith('}t')]
    if any(sep in (t.text or "") for t in text_nodes):
        return _split_multi_node_elem(elem, text_nodes, sep, [], options_xml)
    return [elem]


def split_xml_elements_by_separator(elements: list, sep: str = "|") -> list:
    options_xml = []
    current_xml = []

    for elem in elements:
        text_nodes = [t for t in elem.iter() if t.tag.endswith('}t')]
        elem_text = "".join(t.text or "" for t in text_nodes)

        if sep not in elem_text:
            current_xml.append(elem)
            continue

        if len(text_nodes) == 1:
            current_xml = _split_single_node_elem(elem, text_nodes[0], sep, current_xml, options_xml)
        else:
            current_xml = _split_multi_node_elem(elem, text_nodes, sep, current_xml, options_xml)

    if current_xml:
        options_xml.append(current_xml)
    return options_xml


def get_paragraph_text_with_math(para) -> str:
    text_parts = []
    for elem in para._element.iter():
        if elem.tag.endswith('}t'):
            text_parts.append(elem.text or '')
    return "".join(text_parts)


def _count_omath_in_elements(elements: list) -> int:
    count = 0
    for child in elements:
        for node in child.iter():
            if node.tag.endswith('}oMath'):
                count += 1
    return count


def count_math_formulas(questions: list) -> int:
    math_count = 0
    for q in questions:
        if q.question_xml:
            math_count += _count_omath_in_elements(q.question_xml)
        if q.options_xml:
            for _, opt_elements in q.options_xml:
                math_count += _count_omath_in_elements(opt_elements)
        if getattr(q, "explanation_xml", None):
            math_count += _count_omath_in_elements(q.explanation_xml)
    return math_count

