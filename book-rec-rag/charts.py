"""Module handling analytical graph rendering workloads."""

import matplotlib.pyplot as plt
import streamlit as st


def render_analytics_dashboard(analytics_logs: list, target_goal: int, completed_count: int) -> None:
    """Renders progression metrics including a horizontal bar and a circular milestone gauge."""
    
    # 1. Horizontal Progress Completion Bar Layout
    st.write("#### 🎯 Goal Completion Progress")
    progress_percentage = min(1.0, completed_count / max(1, target_goal))
    
    st.progress(progress_percentage)
    st.caption(f"You have written review notes for **{completed_count}** out of **{target_goal}** books (**{progress_percentage*100:.1f}%** towards your goal).")
    
    # 2. Side-by-Side Analytics Graphs Layout
    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.write("📈 **Goal Adjustment History**")
        if not analytics_logs:
            st.info("No reading pace adjustments logged in this session yet.")
        else:
            # Render a clean chronological timeline log tracking performance adjustments
            dates = [row[0] for row in analytics_logs]
            targets = [row[1] for row in analytics_logs]
            
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.plot(dates, targets, marker='o', linestyle='-', color='#1f77b4', linewidth=2)
            ax.set_title("Sliding Goal Baseline Metric Changes", fontsize=10, fontweight='bold')
            ax.set_ylabel("Book Target Limit", fontsize=9)
            ax.grid(True, linestyle='--', alpha=0.5)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(fontsize=8)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    with col_right:
        st.write("🍩 **Milestone Gauge**")
        
        # 3. Circular Milestone Gauge (Donut Chart representation)
        fig, ax = plt.subplots(figsize=(4, 4))
        remaining = max(0, target_goal - completed_count)
        
        # Slices config: completed items vs what is left to hit the active sidebar target
        sizes = [completed_count, remaining]
        colors = ['#2ca02c', '#e0e0e0'] if completed_count > 0 or remaining > 0 else ['#e0e0e0', '#e0e0e0']
        
        wedges, texts = ax.pie(
            sizes, 
            colors=colors, 
            startangle=90, 
            counterclock=False,
            wedgeprops=dict(width=0.3, edgecolor='white') # Donut hole thickness configuration
        )
        
        # Center numerical text rendering showing current standing
        percentage_text = f"{(completed_count / max(1, target_goal)) * 100:.0f}%"
        ax.text(0, 0, f"{completed_count}/{target_goal}\n({percentage_text})", ha='center', va='center', fontsize=12, fontweight='bold', color='#333333')
        
        ax.axis('equal')  
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
