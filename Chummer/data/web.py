import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔍 Interactive XML Analyzer")

uploaded_file = st.file_uploader("Choose an XML file", type=["xml"])

def collect_stats(elem, path="", counter=None):
    if counter is None:
        counter = defaultdict(lambda: defaultdict(int))

    tag_path = f"{path}/{elem.tag}" if path else elem.tag
    counter[tag_path]['__count__'] += 1

    if elem.text and elem.text.strip():
        val = elem.text.strip()
        counter[tag_path][val] += 1

    for attr, val in elem.attrib.items():
        attr_path = f"{tag_path}[@{attr}]"
        counter[attr_path]['__count__'] += 1
        counter[attr_path][val] += 1

    for child in elem:
        collect_stats(child, tag_path, counter)

    return counter

def show_tree(elem, path="", counter=None, level=0):
    tag_path = f"{path}/{elem.tag}" if path else elem.tag
    indent_px = level * 20

    # Expander label with uppercase + emoji for emphasis
    label = f"🔹 {elem.tag.upper()} ({counter[tag_path]['__count__']})"

    with st.expander(label, expanded=False):
        st.markdown(f"<div style='margin-left: {indent_px}px'>", unsafe_allow_html=True)

        # Show current element's attributes (single element)
        if elem.attrib:
            st.markdown("**Attributes:**")
            st.json(elem.attrib)

        # Show current element's text
        if elem.text and elem.text.strip():
            st.markdown("**Text:**")
            st.code(elem.text.strip())

        # Group children by tag
        children_by_tag = defaultdict(list)
        for child in elem:
            children_by_tag[child.tag].append(child)

        for tag, elements in children_by_tag.items():
            child_path = f"{tag_path}/{tag}"
            indent_inner = indent_px + 20
            child_label = f"🔸 {tag.upper()} ({len(elements)})"

            with st.expander(child_label, expanded=False):
                st.markdown(f"<div style='margin-left: {indent_inner}px'>", unsafe_allow_html=True)

                # Count attribute values and text occurrences across repeated children
                merged_attributes = defaultdict(lambda: defaultdict(int))  # attr -> val -> count
                merged_texts = defaultdict(int)  # text -> count
                grandchildren_by_tag = defaultdict(list)

                for child in elements:
                    for attr, val in child.attrib.items():
                        merged_attributes[attr][val] += 1
                    if child.text and child.text.strip():
                        merged_texts[child.text.strip()] += 1
                    for grandchild in child:
                        grandchildren_by_tag[grandchild.tag].append(grandchild)

                # Display attribute counts
                if merged_attributes:
                    st.markdown("🔸 Attributes:")
                    for attr, val_counts in merged_attributes.items():
                        lines = [f"{val} ({count})" for val, count in sorted(val_counts.items())]
                        st.markdown(f"- **{attr}** =\n    " + "\n    ".join(lines))

                # Display text counts
                if merged_texts:
                    st.markdown("🔹 Text:")
                    lines = [f"{val} ({count})" for val, count in sorted(merged_texts.items())]
                    st.markdown("[" + ", ".join(lines) + "]")

                # Recurse into grandchildren grouped by tag
                if grandchildren_by_tag:
                    group_elem = ET.Element(tag)
                    for group in grandchildren_by_tag.values():
                        for g in group:
                            group_elem.append(g)
                    print(child_path)
                    show_tree(group_elem, child_path, counter, level + 2)

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file:
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        stats = collect_stats(root)
        show_tree(root, counter=stats)
    except Exception as e:
        st.error(f"Error parsing XML: {e}")
