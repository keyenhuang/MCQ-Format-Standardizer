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


def get_para_xml_elements(para):
    elements = []
    for child in para._p:
        if child.tag.endswith('}pPr'):
            continue
        elements.append(copy.deepcopy(child))
    return elements


def strip_xml_prefix(elements, count):
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


def split_xml_elements_by_separator(elements, sep="|"):
    options_xml = []
    current_xml = []

    for elem in elements:
        text_parts = []
        for t in elem.iter():
            if t.tag.endswith('}t'):
                text_parts.append(t.text or "")
        elem_text = "".join(text_parts)

        if sep in elem_text:
            text_nodes = [t for t in elem.iter() if t.tag.endswith('}t')]
            if len(text_nodes) == 1:
                t_node = text_nodes[0]
                t_text = t_node.text or ""
                t_parts = t_text.split(sep)
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
                current_xml = [new_elem]
            else:
                split_done = False
                for t_node in text_nodes:
                    t_text = t_node.text or ""
                    if sep in t_text:
                        t_parts = t_text.split(sep)
                        t_node.text = t_parts[0]
                        current_xml.append(elem)
                        options_xml.append(current_xml)
                        new_elem = copy.deepcopy(elem)
                        new_text_nodes = [t for t in new_elem.iter() if t.tag.endswith('}t')]
                        idx_of_node = text_nodes.index(t_node)
                        for k in range(idx_of_node):
                            new_text_nodes[k].text = ""
                        new_text_nodes[idx_of_node].text = t_parts[1]
                        current_xml = [new_elem]
                        split_done = True
                        break
                if not split_done:
                    current_xml.append(elem)
        else:
            current_xml.append(elem)

    if current_xml:
        options_xml.append(current_xml)
    return options_xml


def get_paragraph_text_with_math(para):
    text_parts = []
    for elem in para._element.iter():
        if elem.tag.endswith('}t'):
            text_parts.append(elem.text or '')
    return "".join(text_parts)


def count_math_formulas(questions):
    math_count = 0
    for q in questions:
        if q.question_xml:
            for child in q.question_xml:
                for node in child.iter():
                    if node.tag.endswith('}oMath'):
                        math_count += 1
        if q.options_xml:
            for letter, opt_elements in q.options_xml:
                for child in opt_elements:
                    for node in child.iter():
                        if node.tag.endswith('}oMath'):
                            math_count += 1
    return math_count
