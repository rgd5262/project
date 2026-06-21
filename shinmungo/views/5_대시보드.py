from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.clustering import build_duplicate_clusters
from services.db import get_session, init_db
from services.models import Ticket
from services.priority import IMPACT_WEIGHTS
from services.seed import seed_if_empty
from services.ui import apply_page_config, apply_styles, current_user, html_escape, status_label

try:
    import plotly.express as px
except Exception:  # pragma: no cover - Streamlit fallback path
    px = None

DONE_STATUSES = {"DONE", "REJECTED"}
PLOT_FONT = "#111827"
PLOT_TITLE = "#0f172a"
PLOT_GRID = "#cbd5e1"
PLOT_AXIS = "#475569"
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}
STANDARD_CHART_HEIGHT = 430
BUBBLE_CHART_HEIGHT = 700


def ensure_data() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


def ticket_dataframe(tickets: list[Ticket]) -> pd.DataFrame:
    now = datetime.now()
    return pd.DataFrame(
        [
            {
                "ticket_id": ticket.id,
                "화면번호": ticket.screen_code,
                "화면명": ticket.screen_name,
                "상태": ticket.status,
                "상태명": status_label(ticket.status),
                "AI분류": ticket.category or "미분류",
                "부서": ticket.assigned_department.name if ticket.assigned_department else "미배정",
                "팔로워": len(ticket.followers),
                "경과일": max(0, (now - ticket.created_at).days),
                "완료여부": "완료" if ticket.status in DONE_STATUSES else "미처리",
            }
            for ticket in tickets
        ]
    )


def recent_ticket_dataframe(tickets: list[Ticket], *, limit: int = 30, clustered_ids: set[int] | None = None) -> pd.DataFrame:
    clustered_ids = clustered_ids or set()
    rows = []
    for ticket in sorted(tickets, key=lambda item: item.created_at, reverse=True)[:limit]:
        rows.append(
            {
                "접수번호": ticket.id,
                "화면번호": ticket.screen_code,
                "화면명": ticket.screen_name,
                "제목": ticket.title,
                "상태": status_label(ticket.status),
                "AI분류": ticket.category or "미분류",
                "부서": ticket.assigned_department.name if ticket.assigned_department else "미배정",
                "군집여부": "군집 포함" if ticket.id in clustered_ids else "미군집",
                "접수일시": ticket.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    return pd.DataFrame(rows)


def unclustered_ticket_dataframe(tickets: list[Ticket], clustered_ids: set[int], *, limit: int = 20) -> pd.DataFrame:
    rows = []
    unclustered = [ticket for ticket in tickets if ticket.id not in clustered_ids]
    for ticket in sorted(unclustered, key=lambda item: item.created_at, reverse=True)[:limit]:
        rows.append(
            {
                "접수번호": ticket.id,
                "화면번호": ticket.screen_code,
                "제목": ticket.title,
                "상태": status_label(ticket.status),
                "AI분류": ticket.category or "미분류",
                "부서": ticket.assigned_department.name if ticket.assigned_department else "미배정",
                "접수일시": ticket.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    return pd.DataFrame(rows)


def render_bar(title: str, df: pd.DataFrame, x: str, y: str, *, orientation: str = "v", key: str) -> None:
    st.subheader(title)
    if df.empty:
        st.caption("표시할 데이터가 없습니다.")
        return
    if px:
        if orientation == "h":
            plot_df = df.sort_values(y, ascending=True)
            fig = px.bar(plot_df, x=y, y=x, text=y, orientation="h")
            xaxis_title = y
            yaxis_title = None
            margin = dict(l=168, r=28, t=24, b=54)
        else:
            fig = px.bar(df, x=x, y=y, text=y)
            xaxis_title = x
            yaxis_title = y
            margin = dict(l=68, r=28, t=24, b=86)
        fig.update_layout(
            height=STANDARD_CHART_HEIGHT,
            dragmode=False,
            margin=margin,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#f8fafc",
            font=dict(color=PLOT_FONT),
            xaxis=dict(
                automargin=True,
                gridcolor=PLOT_GRID,
                linecolor=PLOT_AXIS,
                fixedrange=True,
                showline=True,
                tickcolor=PLOT_AXIS,
                tickfont=dict(color=PLOT_FONT, size=12),
                title=xaxis_title,
                title_font=dict(color=PLOT_TITLE, size=13),
                zeroline=False,
            ),
            yaxis=dict(
                automargin=True,
                gridcolor=PLOT_GRID,
                linecolor=PLOT_AXIS,
                fixedrange=True,
                showline=True,
                tickcolor=PLOT_AXIS,
                tickfont=dict(color=PLOT_FONT, size=12),
                title=yaxis_title,
                title_font=dict(color=PLOT_TITLE, size=13),
                zeroline=False,
            ),
            hoverlabel=dict(bgcolor="#ffffff", bordercolor="#2563eb", font=dict(color=PLOT_FONT, size=12)),
            uniformtext_minsize=10,
            uniformtext_mode="hide",
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOTLY_CONFIG, key=key)
    else:
        st.bar_chart(df.set_index(x)[y])


def render_pie_or_bar(title: str, df: pd.DataFrame, names: str, values: str, *, key: str) -> None:
    st.subheader(title)
    if df.empty:
        st.caption("표시할 데이터가 없습니다.")
        return
    if px:
        fig = px.pie(df, names=names, values=values, hole=0.35)
        fig.update_layout(
            height=STANDARD_CHART_HEIGHT,
            dragmode=False,
            margin=dict(l=24, r=24, t=26, b=104),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#f8fafc",
            font=dict(color=PLOT_FONT),
            legend=dict(
                orientation="h",
                bgcolor="rgba(255,255,255,0.96)",
                bordercolor=PLOT_GRID,
                borderwidth=1,
                font=dict(color=PLOT_FONT, size=12),
                title_font=dict(color=PLOT_TITLE, size=12),
                x=0,
                xanchor="left",
                y=-0.16,
                yanchor="top",
            ),
            hoverlabel=dict(bgcolor="#ffffff", bordercolor="#2563eb", font=dict(color=PLOT_FONT, size=12)),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOTLY_CONFIG, key=key)
    else:
        st.bar_chart(df.set_index(names)[values])


def render_metric_card(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="dashboard-metric-card" style="--metric-accent:{accent}">
          <div class="dashboard-metric-label">{html_escape(label)}</div>
          <div class="dashboard-metric-value">{html_escape(value)}</div>
          <div class="dashboard-metric-note">{html_escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cluster_status_text(status_counts: dict[str, int]) -> str:
    return " · ".join(
        f"{status_label(status)} {count}건"
        for status, count in sorted(status_counts.items(), key=lambda item: status_label(item[0]))
    )


def cluster_category_text(category_counts: dict[str, int]) -> str:
    return " · ".join(
        f"{category} {count}건"
        for category, count in sorted(category_counts.items(), key=lambda item: item[0])
    )


def dominant_value(counts: dict[str, int], default: str) -> str:
    if not counts:
        return default
    return sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)[0][0]


def cluster_priority_score(cluster: dict, ticket_by_id: dict[int, Ticket]) -> int:
    cluster_tickets = [ticket_by_id[ticket_id] for ticket_id in cluster["ticket_ids"] if ticket_id in ticket_by_id]
    if not cluster_tickets:
        return 0

    category = dominant_value(cluster["category_counts"], "미분류")
    frequency_score = min(40, int(cluster["size"]) * 7 + int(cluster["follower_count"]) * 3)
    impact_score = IMPACT_WEIGHTS.get(category, 10)
    now = datetime.now()
    unresolved_ages = [
        max(0, (now - ticket.created_at).days)
        for ticket in cluster_tickets
        if ticket.status not in DONE_STATUSES
    ]
    age_score = min(30, (max(unresolved_ages) if unresolved_ages else 0) * 2)
    unresolved_bonus = min(10, sum(1 for ticket in cluster_tickets if ticket.status not in DONE_STATUSES) * 2)
    return min(100, frequency_score + impact_score + age_score + unresolved_bonus)


def cluster_dataframe(clusters: list[dict], ticket_by_id: dict[int, Ticket]) -> pd.DataFrame:
    rows = []
    for cluster in clusters:
        cluster_tickets = [ticket_by_id[ticket_id] for ticket_id in cluster["ticket_ids"] if ticket_id in ticket_by_id]
        if not cluster_tickets:
            continue
        unresolved_count = sum(1 for ticket in cluster_tickets if ticket.status not in DONE_STATUSES)
        done_count = sum(1 for ticket in cluster_tickets if ticket.status in DONE_STATUSES)
        dominant_status = dominant_value(cluster["status_counts"], "RECEIVED")
        dominant_category = dominant_value(cluster["category_counts"], "미분류")
        status_text = cluster_status_text(cluster["status_counts"])
        category_text = cluster_category_text(cluster["category_counts"])
        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "화면번호": str(cluster["screen_code"]),
                "화면명": cluster["screen_name"],
                "대표접수번호": cluster["representative_ticket_id"],
                "대표제목": cluster["representative_title"],
                "군집크기": int(cluster["size"]),
                "팔로워": int(cluster["follower_count"]),
                "버블크기": max(8, int(cluster["follower_count"]) + int(cluster["size"]) * 2),
                "미처리건수": unresolved_count,
                "종결건수": done_count,
                "대표상태": status_label(dominant_status),
                "대표AI분류": dominant_category,
                "우선순위점수": cluster_priority_score(cluster, ticket_by_id),
                "상태분포": status_text,
                "분류분포": category_text,
            }
        )
    return pd.DataFrame(rows)


def render_cluster_bubble_chart(clusters: list[dict], ticket_by_id: dict[int, Ticket], chart_key: str) -> None:
    chart_df = cluster_dataframe(clusters, ticket_by_id)
    if chart_df.empty:
        st.caption("버블 차트로 표시할 군집이 없습니다.")
        return

    if px:
        fig = px.scatter(
            chart_df,
            x="군집크기",
            y="우선순위점수",
            size="버블크기",
            color="대표AI분류",
            hover_name="대표제목",
            hover_data={
                "대표접수번호": True,
                "화면번호": True,
                "화면명": True,
                "군집크기": True,
                "팔로워": True,
                "미처리건수": True,
                "종결건수": True,
                "대표상태": True,
                "상태분포": True,
                "분류분포": True,
                "버블크기": False,
            },
            labels={
                "군집크기": "군집 크기",
                "우선순위점수": "우선순위 점수",
                "대표AI분류": "대표 AI분류",
            },
            size_max=38,
        )
        fig.update_traces(marker=dict(line=dict(width=1.5, color="#ffffff"), opacity=0.86))
        fig.update_layout(
            height=BUBBLE_CHART_HEIGHT,
            dragmode=False,
            margin=dict(l=82, r=34, t=104, b=78),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#f8fafc",
            font=dict(color=PLOT_FONT),
            legend_title_text="대표 AI분류",
            legend=dict(
                orientation="h",
                bgcolor="rgba(255,255,255,0.96)",
                bordercolor=PLOT_GRID,
                borderwidth=1,
                font=dict(color=PLOT_FONT, size=12),
                title_font=dict(color=PLOT_TITLE, size=12),
                itemsizing="constant",
                x=0,
                xanchor="left",
                y=1.14,
                yanchor="top",
            ),
            hoverlabel=dict(
                bgcolor="#ffffff",
                bordercolor="#2563eb",
                font=dict(color=PLOT_FONT, size=12),
            ),
            xaxis=dict(
                automargin=True,
                gridcolor=PLOT_GRID,
                linecolor=PLOT_AXIS,
                fixedrange=True,
                linewidth=1,
                mirror=False,
                showline=True,
                tickcolor=PLOT_AXIS,
                tickfont=dict(color=PLOT_FONT, size=12),
                title_font=dict(color=PLOT_TITLE, size=13),
                zeroline=False,
            ),
            yaxis=dict(
                automargin=True,
                gridcolor=PLOT_GRID,
                linecolor=PLOT_AXIS,
                fixedrange=True,
                linewidth=1,
                mirror=False,
                range=[-5, 118],
                showline=True,
                tickcolor=PLOT_AXIS,
                tickfont=dict(color=PLOT_FONT, size=12),
                title_font=dict(color=PLOT_TITLE, size=13),
                zeroline=False,
            ),
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            theme=None,
            config=PLOTLY_CONFIG,
            key=f"cluster_bubble_{chart_key}",
        )
    else:
        st.caption("Plotly를 사용할 수 없어 기본 산점도로 표시합니다.")
        st.scatter_chart(chart_df, x="군집크기", y="우선순위점수", size="버블크기")


def render_cluster_card(cluster: dict) -> None:
    ticket_lines = []
    visible_ticket_count = 12
    for ticket in cluster["tickets"][:visible_ticket_count]:
        ticket_lines.append(
            f"#{ticket.id} · {html_escape(status_label(ticket.status))} · "
            f"{html_escape(ticket.title)}"
        )
    if len(cluster["tickets"]) > visible_ticket_count:
        ticket_lines.append(f"외 {len(cluster['tickets']) - visible_ticket_count}건")

    status_text = cluster_status_text(cluster["status_counts"])
    category_text = cluster_category_text(cluster["category_counts"])
    ticket_text = "<br>".join(ticket_lines)
    st.markdown(
        f"""
        <div class="dashboard-cluster-card">
          <div class="dashboard-cluster-title">{html_escape(cluster["representative_title"])}</div>
          <div class="dashboard-cluster-meta">
            대표 화면: {html_escape(cluster["screen_code"])} {html_escape(cluster["screen_name"])}<br>
            대표 접수: #{cluster["representative_ticket_id"]}
          </div>
          <div class="dashboard-cluster-pills">
            <span class="dashboard-cluster-pill">포함 {cluster["size"]}건</span>
            <span class="dashboard-cluster-pill">팔로워 {cluster["follower_count"]}명</span>
          </div>
          <div class="dashboard-cluster-meta dashboard-cluster-status">상태: {html_escape(status_text)}</div>
          <div class="dashboard-cluster-meta dashboard-cluster-category">분류: {html_escape(category_text)}</div>
          <div class="dashboard-cluster-ticket">{ticket_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cluster_cards(clusters: list[dict]) -> None:
    if not clusters:
        st.caption("표시할 중복 클러스터가 없습니다.")
        return
    for index in range(0, len(clusters), 2):
        cols = st.columns(2)
        for col, cluster in zip(cols, clusters[index : index + 2]):
            with col:
                render_cluster_card(cluster)


def render_cluster_tabs(clusters: list[dict], ticket_by_id: dict[int, Ticket]) -> None:
    if not clusters:
        st.caption("중복 클러스터가 없습니다.")
        return

    grouped: dict[str, list[dict]] = {}
    for cluster in clusters:
        grouped.setdefault(str(cluster["screen_code"]), []).append(cluster)

    screen_labels = {
        code: f"{code} {items[0]['screen_name']}"
        for code, items in sorted(grouped.items(), key=lambda item: item[0])
    }
    tab_keys = ["전체"] + list(screen_labels.keys())
    tabs = st.tabs(["전체"] + [screen_labels[code] for code in screen_labels])

    for tab_key, tab in zip(tab_keys, tabs):
        with tab:
            current_clusters = clusters if tab_key == "전체" else grouped.get(tab_key, [])
            st.caption(f"중복 요청 군집 {len(current_clusters)}개")
            render_cluster_bubble_chart(current_clusters, ticket_by_id, tab_key)
            render_cluster_cards(current_clusters[:10])


def main() -> None:
    apply_page_config("대시보드")
    apply_styles()
    ensure_data()
    user = current_user()
    st.title("관리자 대시보드")

    if user.role != "관리자":
        st.warning("본부부서로 전환해야 접근할 수 있습니다. 사이드바에서 역할을 본부부서로 선택해 주세요.")
        return

    session = get_session()
    try:
        tickets = session.query(Ticket).all()
        df = ticket_dataframe(tickets)
        if df.empty:
            st.info("집계할 접수 내역이 없습니다.")
            return

        total = len(df)
        unresolved = int((~df["상태"].isin(DONE_STATUSES)).sum())
        delayed = int(((~df["상태"].isin(DONE_STATUSES)) & (df["경과일"] >= 7)).sum())
        done = int((df["상태"] == "DONE").sum())
        completion_rate = done / total if total else 0
        metric_cols = st.columns(4)
        with metric_cols[0]:
            render_metric_card("총 접수", f"{total:,}", "전체 접수 기준", "#2563eb")
        with metric_cols[1]:
            render_metric_card("미처리", f"{unresolved:,}", "완료/반려 제외", "#d97706")
        with metric_cols[2]:
            render_metric_card("지연", f"{delayed:,}", "미처리 7일 이상", "#dc2626")
        with metric_cols[3]:
            render_metric_card("완료율", f"{completion_rate:.1%}", f"완료 {done:,}건", "#059669")

        top_screen = (
            df.groupby(["화면번호", "화면명"], as_index=False)
            .size()
            .rename(columns={"size": "건수"})
            .sort_values("건수", ascending=False)
            .head(10)
        )
        top_screen["화면"] = top_screen["화면번호"] + " " + top_screen["화면명"]
        status_dist = df.groupby("상태명", as_index=False).size().rename(columns={"size": "건수"})
        category_dist = df.groupby("AI분류", as_index=False).size().rename(columns={"size": "건수"})
        dept_dist = df.groupby("부서", as_index=False).size().rename(columns={"size": "건수"})

        chart_cols = st.columns(2)
        with chart_cols[0]:
            render_bar(
                "빈도 높은 화면 Top N",
                top_screen,
                "화면",
                "건수",
                orientation="h",
                key="dashboard_chart_top_screen",
            )
        with chart_cols[1]:
            render_pie_or_bar("상태별 분포", status_dist, "상태명", "건수", key="dashboard_chart_status")

        chart_cols2 = st.columns(2)
        with chart_cols2[0]:
            render_bar("분류별 분포", category_dist, "AI분류", "건수", key="dashboard_chart_category")
        with chart_cols2[1]:
            render_bar(
                "부서별 분포",
                dept_dist,
                "부서",
                "건수",
                orientation="h",
                key="dashboard_chart_department",
            )

        clusters = build_duplicate_clusters(session)
        clustered_ids = {
            int(ticket_id)
            for cluster in clusters
            for ticket_id in cluster["ticket_ids"]
        }

        st.subheader("최근 접수 내역")
        st.caption("신규 접수 확인용 목록입니다. 중복 군집에 아직 묶이지 않은 단독 요청도 여기에서 바로 확인할 수 있습니다.")
        recent_df = recent_ticket_dataframe(tickets, limit=30, clustered_ids=clustered_ids)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)

        st.subheader("중복 클러스터")
        st.caption("같은 화면 안에서 임베딩 유사도 기준을 넘은 2건 이상 요청만 군집으로 표시합니다. 기준 미달 단독 요청은 아래 미군집 목록에 표시됩니다.")
        ticket_by_id = {ticket.id: ticket for ticket in tickets}
        render_cluster_tabs(clusters, ticket_by_id)

        st.markdown("#### 최근 미군집 요청")
        unclustered_df = unclustered_ticket_dataframe(tickets, clustered_ids, limit=20)
        if unclustered_df.empty:
            st.caption("최근 미군집 요청이 없습니다.")
        else:
            st.dataframe(unclustered_df, use_container_width=True, hide_index=True)

    finally:
        session.close()


main()
