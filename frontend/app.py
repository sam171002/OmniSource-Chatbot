import os
import uuid

import requests
import streamlit as st
import pandas as pd
import altair as alt


BACKEND_URL = os.getenv("OMNISOURCE_BACKEND_URL", "http://localhost:8000")


def ensure_conversation_id():
    if "conversation_id" not in st.session_state:
        st.session_state["conversation_id"] = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


def render_chat():
    st.subheader("OmniSource Chatbot")
    ensure_conversation_id()

    # Example questions to guide the user
    with st.expander("See example questions"):
        st.markdown(
            "- **Excel / CSV examples**:\n"
            "  - What is the average price of all Smart Phone models sold by Bestbuy?\n"
            "  - How many Laptop products are sold by Walmart?\n"
            "  - What is the average review rating for Samsung TVs?\n\n"
            "- **PDF examples**:\n"
            "  - Summarize the key recommendations from the omnichannel strategy document.\n"
            "  - What are the main challenges mentioned for social listening in large enterprises?"
        )

    # Render chat history
    for m in st.session_state["messages"]:
        role = "user" if m["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(m["content"])

    # Chat input at the very bottom so it stays anchored after responses
    user_input = st.chat_input("Ask about your data...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "conversation_id": st.session_state["conversation_id"],
                        "messages": st.session_state["messages"],
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["answer"]
                # Store query_id for latest answer for feedback linkage
                st.session_state["last_query_id"] = data.get("query_id")
                st.markdown(answer)
                st.session_state["messages"].append(
                    {"role": "assistant", "content": answer}
                )
                # Force rerun to show feedback controls
                st.rerun()

    # Feedback controls for most recent assistant message (after input, so it appears below chat)
    if st.session_state["messages"]:
        last_msg = st.session_state["messages"][-1]
        qid = st.session_state.get("last_query_id")
        if last_msg["role"] == "assistant" and qid is not None:
            st.markdown("---")
            st.markdown("**Rate this answer**")
            feedback_text = st.text_input(
                "Optional feedback", key=f"fb_text_{qid}", placeholder="Tell us what worked well or what was missing..."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Helpful", key=f"up_{qid}"):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/feedback",
                            json={
                                "query_id": qid,
                                "feedback": 1,
                                "feedback_text": feedback_text or None,
                            },
                            timeout=10,
                        )
                        resp.raise_for_status()
                        st.success("Thanks for the feedback.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit feedback: {e}")
            with col2:
                if st.button("Not helpful", key=f"down_{qid}"):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/feedback",
                            json={
                                "query_id": qid,
                                "feedback": -1,
                                "feedback_text": feedback_text or None,
                            },
                            timeout=10,
                        )
                        resp.raise_for_status()
                        st.info("Feedback recorded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit feedback: {e}")


def render_analytics():
    st.subheader("Analytics Dashboard")
    resp = requests.get(f"{BACKEND_URL}/analytics/summary", timeout=30)
    if not resp.ok:
        st.error("Failed to load analytics summary.")
        return
    data = resp.json()

    st.metric("Total Queries", data["total_queries"])
    st.metric("Avg Response Time (ms)", round(data["avg_response_time_ms"], 1))

    if data["total_queries"] == 0:
        st.info("No queries yet. Start chatting to see analytics here.")
        return

    # Query source usage (routing patterns)
    st.markdown("### Query Source Usage")
    if data["by_source"]:
        source_df = pd.DataFrame(
            [
                {"Source": src.capitalize(), "Count": count}
                for src, count in data["by_source"].items()
            ]
        )
        source_chart = (
            alt.Chart(source_df)
            .mark_bar()
            .encode(
                x=alt.X("Source", sort="-y", title="Primary routed source"),
                y=alt.Y("Count", title="Number of queries"),
                tooltip=["Source", "Count"],
            )
            .properties(height=300)
        )
        st.altair_chart(source_chart, use_container_width=True)
    else:
        st.write("No source routing data yet.")

    # Feedback distribution
    st.markdown("### Feedback Overview")
    fb_up = data["feedback_summary"].get("up", 0)
    fb_down = data["feedback_summary"].get("down", 0)
    if fb_up == 0 and fb_down == 0:
        st.write("No feedback provided yet.")
    else:
        fb_df = pd.DataFrame(
            [
                {"Feedback": "Helpful", "Count": fb_up},
                {"Feedback": "Not helpful", "Count": fb_down},
            ]
        )
        fb_chart = (
            alt.Chart(fb_df)
            .mark_bar()
            .encode(
                x=alt.X("Feedback", title="User feedback"),
                y=alt.Y("Count", title="Number of responses"),
                color=alt.Color("Feedback", legend=None),
                tooltip=["Feedback", "Count"],
            )
            .properties(height=300)
        )
        st.altair_chart(fb_chart, use_container_width=True)


def main():
    st.set_page_config(page_title="OmniSource Chatbot")
    st.title("Multi-Source Analytics Assistant")

    tab_chat, tab_analytics = st.tabs(["Chat", "Analytics"])
    with tab_chat:
        render_chat()
    with tab_analytics:
        render_analytics()


if __name__ == "__main__":
    main()



