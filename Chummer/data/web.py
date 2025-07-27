import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide")
st.title("🔍 Interactive XML Analyzer")
st.write("Upload an XML file to see its structure, get aggregated statistics, and explore its contents.")


# --- Data Collection & Analysis ---

def collect_stats(element, path="", stats_counter=None):
    """
    Recursively traverses the XML tree to collect detailed statistics.
    """
    if stats_counter is None:
        stats_counter = defaultdict(lambda: defaultdict(int))
    tag_path = f"{path}/{element.tag}" if path else element.tag
    stats_counter[tag_path]['__count__'] += 1
    if element.text and element.text.strip():
        stats_counter[tag_path][element.text.strip()] += 1
    for attr, val in element.attrib.items():
        attr_path = f"{tag_path}[@{attr}]"
        stats_counter[attr_path]['__count__'] += 1
        stats_counter[attr_path][val] += 1
    for child in element:
        collect_stats(child, tag_path, stats_counter)
    return stats_counter

def check_if_element_matches(element, config):
    """Checks if a single element matches the search criteria."""
    filter_type = config.get("type")
    
    def text_contains(search_in, search_for):
        return search_for.lower() in search_in.lower()

    if filter_type == "Tag Name":
        return text_contains(element.tag, config.get("tag_name", ""))
    elif filter_type == "Attribute Value":
        attr_name = config.get("attr_name", "")
        attr_value = config.get("attr_value", "")
        return attr_name in element.attrib and text_contains(element.attrib[attr_name], attr_value)
    elif filter_type == "Text Content":
        return element.text and text_contains(element.text.strip(), config.get("text_value", ""))
    return False

def find_matching_elements(element, config, matches):
    """Recursively finds all elements for the flat list view."""
    if check_if_element_matches(element, config):
        matches.append(element)
    for child in element:
        find_matching_elements(child, config, matches)

def filter_tree(element, config):
    """
    Recursively filters the XML tree.
    Keeps an element if it matches the search or has descendants that do.
    """
    # First, filter the children of the current element.
    kept_children = []
    for child in element:
        filtered_child = filter_tree(child, config)
        if filtered_child is not None:
            kept_children.append(filtered_child)
            
    # Now, check if the element itself is a match.
    is_direct_match = check_if_element_matches(element, config)
    
    # Keep this element if it's a direct match OR if it has children that were kept.
    if is_direct_match or kept_children:
        # Create a copy of the element to avoid modifying the original tree.
        element_copy = ET.Element(element.tag, element.attrib)
        element_copy.text = element.text
        
        # Add the filtered children to the copy.
        for child in kept_children:
            element_copy.append(child)
        return element_copy
        
    return None


# --- UI Display Functions ---

def display_node_summary(element, path, stats):
    """
    Displays the summarized view for a group of elements with the same tag.
    """
    children_grouped = defaultdict(list)
    for child in element:
        children_grouped[child.tag].append(child)

    if element.text and element.text.strip():
        st.markdown("**Text:**"); st.code(element.text.strip(), language=None)
    if element.attrib:
        st.markdown("**Attributes:**"); st.json(element.attrib)
    if not children_grouped:
        st.info("This element has no nested children.")
        
    for tag, children in children_grouped.items():
        child_path = f"{path}/{tag}"; count = len(children)
        label = f"🔸 {tag} ({count} element{'s' if count > 1 else ''})"
        with st.expander(label):
            representative_child = children[0]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Text Content Summary**")
                text_counts = {k: v for k, v in stats.get(child_path, {}).items() if k != '__count__'}
                if text_counts: st.dataframe(pd.Series(text_counts, name="Count"), use_container_width=True)
                else: st.caption("No direct text content.")
            with col2:
                st.markdown("**Attribute Summary**")
                found_attrs = [
                    (attr, f"{child_path}[@{attr}]") for attr in representative_child.attrib
                    if f"{child_path}[@{attr}]" in stats
                ]
                if not found_attrs: st.caption("No attributes found.")
                else:
                    for attr_name, attr_path in found_attrs:
                        st.write(f"`@{attr_name}`")
                        value_counts = {k: v for k, v in stats[attr_path].items() if k != '__count__'}
                        st.dataframe(pd.Series(value_counts, name="Count"), use_container_width=True)
            st.markdown("---")
            st.markdown(f"**Exploring structure of the first `{tag}` element:**")
            display_node_summary(representative_child, child_path, stats)

def display_search_results_flat(results, parent_map):
    """Displays a flat list of elements found by the search."""
    st.header(f"Found {len(results)} matching element(s) in Flat List View")
    if not results:
        st.warning("Your search did not return any results. Try different criteria.")
        return
    for i, el in enumerate(results):
        with st.container(border=True):
            st.subheader(f"Result {i+1}: `<{el.tag}>`")
            if el.attrib: st.markdown("**Attributes:**"); st.json(el.attrib)
            if el.text and el.text.strip(): st.markdown("**Text:**"); st.code(el.text.strip())
            child_tags = [child.tag for child in el]
            if child_tags:
                with st.expander(f"View {len(child_tags)} direct child tag(s)"):
                    st.info(", ".join(f"`<{tag}>`" for tag in child_tags))
            with st.expander("**Show Full XML Element**"):
                el_copy = deepcopy(el)
                try: ET.indent(el_copy, space="  ")
                except AttributeError: pass
                st.code(ET.tostring(el_copy, encoding='unicode'), language='xml')
            parent = parent_map.get(el)
            if parent is not None:
                with st.expander("⬆️ **Show Parent Element (One Level Up)**"):
                    st.write(f"**Parent Tag:** `<{parent.tag}>`")
                    if parent.attrib: st.write("**Parent Attributes:**"); st.json(parent.attrib)
                    st.markdown("---"); st.write("**Full Parent XML:**")
                    parent_copy = deepcopy(parent)
                    try: ET.indent(parent_copy, space="  ")
                    except AttributeError: pass
                    st.code(ET.tostring(parent_copy, encoding='unicode'), language='xml')

# --- Main Application Logic ---
if 'search_active' not in st.session_state:
    st.session_state.search_active = False
if 'search_config' not in st.session_state:
    st.session_state.search_config = {}

uploaded_file = st.file_uploader("Choose an XML file", type=["xml"])

if uploaded_file:
    try:
        xml_bytes = uploaded_file.getvalue()
        root = ET.fromstring(xml_bytes)
        parent_map = {c: p for p in root.iter() for c in p} # For flat view context
        
        st.success(f"Successfully parsed XML with root element: `<{root.tag}>`")
        
        with st.expander("🔎 **Search & Filter**", expanded=st.session_state.search_active):
            search_config = {"type": "Tag Name"} # Default
            
            c1, c2 = st.columns([2, 1])
            with c1:
                search_type = st.selectbox("Filter by", ("Tag Name", "Attribute Value", "Text Content"))
                search_config["type"] = search_type
                if search_type == "Tag Name":
                    search_config["tag_name"] = st.text_input("Tag name contains (case-insensitive)", key="tag_name_in")
                elif search_type == "Attribute Value":
                    sc1, sc2 = st.columns(2)
                    search_config["attr_name"] = sc1.text_input("Attribute name is exactly", key="attr_name_in")
                    search_config["attr_value"] = sc2.text_input("Value contains (case-insensitive)", key="attr_val_in")
                elif search_type == "Text Content":
                    search_config["text_value"] = st.text_input("Text content contains (case-insensitive)", key="text_val_in")
            
            with c2:
                st.session_state.display_mode = st.radio(
                    "Search display mode:", 
                    ("Filtered Tree View", "Flat List View"),
                    key="display_mode_radio"
                )
            
            b_col1, b_col2 = st.columns(2)
            if b_col1.button("Search", type="primary", use_container_width=True):
                st.session_state.search_active = True
                st.session_state.search_config = search_config
                st.rerun()
            if b_col2.button("Clear Search", use_container_width=True):
                st.session_state.search_active = False
                st.session_state.search_config = {}
                st.rerun()
        
        st.markdown("---")
        
        # Determine which data to display
        display_root = root
        display_stats = collect_stats(root)
        is_filtered = False

        if st.session_state.search_active:
            if st.session_state.display_mode == "Filtered Tree View":
                with st.spinner("Filtering tree..."):
                    filtered_root = filter_tree(root, st.session_state.search_config)
                if filtered_root:
                    display_root = filtered_root
                    display_stats = collect_stats(filtered_root)
                    is_filtered = True
                else:
                    st.warning("Your search returned no results in the tree view.")
            else: # Flat List View
                with st.spinner("Searching for elements..."):
                    search_results = []
                    find_matching_elements(root, st.session_state.search_config, search_results)
                    display_search_results_flat(search_results, parent_map)
                # Stop execution here for flat view to avoid showing the main tabs
                st.stop() 

        # --- Main Display (for full or filtered tree) ---
        if is_filtered:
            st.info("Displaying a **filtered** view of the XML. Clear the search to see the full file.")

        tab1, tab2 = st.tabs(["📊 Interactive Tree View", "📈 Raw Statistics"])
        with tab1:
            st.header("Interactive Element Tree")
            display_node_summary(display_root, display_root.tag, display_stats)
        with tab2:
            st.header("Statistical Summary")
            report_data = []
            for path, values in sorted(display_stats.items()):
                report_data.append({
                    "Type": "Attribute" if "[@" in path else "Element/Tag",
                    "Path / Name": path,
                    "Total Occurrences": values.get('__count__', 0)
                })
            df = pd.DataFrame(report_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Awaiting XML file upload...")
