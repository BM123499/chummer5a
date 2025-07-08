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
    # 1. Group direct children of the current element by their tag name
    children_grouped = defaultdict(list)
    for child in element:
        children_grouped[child.tag].append(child)

    # 2. Display text and attributes of the CURRENT element
    if element.text and element.text.strip():
        st.markdown("**Text:**")
        st.code(element.text.strip(), language=None)

    if element.attrib:
        st.markdown("**Attributes:**")
        st.json(element.attrib)

    # 3. Iterate through each group of children and create an expander for it
    if not children_grouped:
        st.info("This element has no nested children.")
        
    for tag, children in children_grouped.items():
        child_path = f"{path}/{tag}"
        count = len(children)
        label = f"🔸 {tag} ({count} element{'s' if count > 1 else ''})"

        with st.expander(label):
            # Take the first child as a representative sample for recursion
            representative_child = children[0]
            
            # Use columns for a clean layout of stats
            col1, col2 = st.columns(2)

            # Display attribute statistics
            with col1:
                st.markdown("**Attribute Summary**")
                has_attrs = False
                for attr_name in representative_child.attrib.keys():
                    attr_path = f"{child_path}[@{attr_name}]"
                    if attr_path in stats:
                        has_attrs = True
                        st.write(f"`@{attr_name}`")
                        # Filter out the internal count key for display
                        value_counts = {k: v for k, v in stats[attr_path].items() if k != '__count__'}
                        st.dataframe(pd.Series(value_counts, name="Count"), use_container_width=True)
                if not has_attrs:
                    st.caption("No attributes found.")

            # Display text content statistics
            with col2:
                st.markdown("**Text Content Summary**")
                # Filter out the internal count key for display
                text_counts = {k: v for k, v in stats[child_path].items() if k != '__count__'}
                if text_counts:
                    st.dataframe(pd.Series(text_counts, name="Count"), use_container_width=True)
                else:
                    st.caption("No direct text content found.")

            # Recurse into the representative child's structure
            st.markdown("---")
            st.markdown(f"**Exploring structure of the first `{tag}` element:**")
            display_node_summary(representative_child, child_path, stats)


# --- Main Application Logic ---
uploaded_file = st.file_uploader("Choose an XML file", type=["xml"])

if uploaded_file:
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()

        # Perform analysis once
        with st.spinner("Analyzing XML..."):
            stats = collect_stats(root)

        st.success(f"Successfully parsed XML with root element: `<{root.tag}>`")

        # Create tabs for different views
        tab1, tab2 = st.tabs(["📊 Interactive Tree View", "📈 Raw Statistics"])

        with tab1:
            st.header("Interactive Element Tree")
            st.write("Expand any element to see a summary of its children and explore the hierarchy.")
            # Start the recursive display from the root
            display_node_summary(root, root.tag, stats)

        with tab2:
            st.header("Statistical Summary")
            st.write("This table shows the counts for every unique element path, attribute, and value found in the file.")
            
            # Convert the statistics dictionary to a more readable DataFrame
            report_data = []
            for path, values in sorted(stats.items()):
                total_occurrences = values.get('__count__', 0)
                if "[@" in path:
                    item_type = "Attribute"
                else:
                    item_type = "Element/Tag"
                report_data.append({
                    "Type": item_type,
                    "Path / Name": path,
                    "Total Occurrences": total_occurrences
                })

            df = pd.DataFrame(report_data)
            st.dataframe(df, use_container_width=True, height=500)

    except Exception as e:
        st.error(f"An error occurred while parsing the XML file: {e}")

else:
    st.info("Awaiting XML file upload...")
