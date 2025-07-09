import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔍 Interactive XML Analyzer")
st.write("Upload an XML file to see its structure, get aggregated statistics, and explore its contents.")

# --- Data Collection ---
def collect_stats(element, path="", stats_counter=None):
    """
    Recursively traverses the XML tree to collect detailed statistics.
    It counts tag occurrences, attribute names/values, and text content.
    """
    if stats_counter is None:
        stats_counter = defaultdict(lambda: defaultdict(int))

    # Build the XPath-like path for the current element
    tag_path = f"{path}/{element.tag}" if path else element.tag
    stats_counter[tag_path]['__count__'] += 1

    # Count text content if it exists
    if element.text and element.text.strip():
        val = element.text.strip()
        stats_counter[tag_path][val] += 1

    # Count attributes and their values
    for attr, val in element.attrib.items():
        attr_path = f"{tag_path}[@{attr}]"
        stats_counter[attr_path]['__count__'] += 1
        stats_counter[attr_path][val] += 1

    # Recurse for all children
    for child in element:
        collect_stats(child, tag_path, stats_counter)

    return stats_counter


# --- UI Display Functions ---
def display_node_summary(element, path, stats):
    """
    Displays the summarized view for a group of elements with the same tag.
    This function is the core of the interactive tree.
    """
    children_grouped = defaultdict(list)
    for child in element:
        children_grouped[child.tag].append(child)

    if element.text and element.text.strip():
        st.markdown("**Text:**")
        st.code(element.text.strip(), language=None)

    if element.attrib:
        st.markdown("**Attributes:**")
        st.json(element.attrib)

    if not children_grouped:
        st.info("This element has no nested children.")
        
    for tag, children in children_grouped.items():
        child_path = f"{path}/{tag}"
        count = len(children)
        label = f"🔸 {tag} ({count} element{'s' if count > 1 else ''})"

        with st.expander(label):
            representative_child = children[0]
            
            # --- IMPROVEMENT: Left-Right Layout for Summaries ---
            col1, col2 = st.columns(2)

            # --- Left Column: Text Content Summary ---
            with col1:
                st.markdown("**Text Content Summary**")
                text_counts = {k: v for k, v in stats[child_path].items() if k != '__count__'}
                if text_counts:
                    st.dataframe(pd.Series(text_counts, name="Count"), use_container_width=True)
                else:
                    st.caption("No direct text content found.")

            # --- Right Column: Attribute Summary ---
            with col2:
                st.markdown("**Attribute Summary**")
                
                # Check which attributes from the representative element have stats
                found_attrs = []
                for attr_name in representative_child.attrib.keys():
                    attr_path = f"{child_path}[@{attr_name}]"
                    if attr_path in stats:
                        found_attrs.append((attr_name, attr_path))

                if not found_attrs:
                    st.caption("No attributes found.")
                else:
                    for attr_name, attr_path in found_attrs:
                        st.write(f"`@{attr_name}`")
                        value_counts = {k: v for k, v in stats[attr_path].items() if k != '__count__'}
                        st.dataframe(pd.Series(value_counts, name="Count"), use_container_width=True)

            # --- Recursion into child's structure ---
            st.markdown("---")
            st.markdown(f"**Exploring structure of the first `{tag}` element:**")
            display_node_summary(representative_child, child_path, stats)


# --- Main Application Logic ---
uploaded_file = st.file_uploader("Choose an XML file", type=["xml"])

if uploaded_file:
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()

        with st.spinner("Analyzing XML..."):
            stats = collect_stats(root)

        st.success(f"Successfully parsed XML with root element: `<{root.tag}>`")

        tab1, tab2 = st.tabs(["📊 Interactive Tree View", "📈 Raw Statistics"])

        with tab1:
            st.header("Interactive Element Tree")
            st.write("Expand any element to see a summary of its children and explore the hierarchy.")
            display_node_summary(root, root.tag, stats)

        with tab2:
            st.header("Statistical Summary")
            st.write("This table shows the counts for every unique element path, attribute, and value found in the file.")
            
            report_data = []
            for path, values in sorted(stats.items()):
                total_occurrences = values.get('__count__', 0)
                item_type = "Attribute" if "[@" in path else "Element/Tag"
                report_data.append({
                    "Type": item_type,
                    "Path / Name": path,
                    "Total Occurrences": total_occurrences
                })

            df = pd.DataFrame(report_data)
            
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Path / Name": st.column_config.TextColumn("Path / Name", width="large"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Total Occurrences": st.column_config.NumberColumn("Total Occurrences", width="small"),
                },
                hide_index=True,
            )

    except Exception as e:
        st.error(f"An error occurred while parsing the XML file: {e}")

else:
    st.info("Awaiting XML file upload...")