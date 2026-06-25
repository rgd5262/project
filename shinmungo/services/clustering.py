from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import networkx as nx
from sqlalchemy.orm import Session

from services.models import Ticket
from services.similarity import cosine_similarity, deserialize_embedding, ensure_ticket_embedding


@dataclass(frozen=True)
class ClusterTicket:
    id: int
    title: str
    status: str
    screen_code: str
    follower_count: int


def build_duplicate_clusters(session: Session, threshold: float = 0.83) -> list[dict]:
    tickets = session.query(Ticket).all()
    for ticket in tickets:
        ensure_ticket_embedding(ticket)
    session.commit()

    vectors = {ticket.id: deserialize_embedding(ticket.embedding_json) for ticket in tickets}
    graph = nx.Graph()
    for ticket in tickets:
        graph.add_node(ticket.id)

    for left_index, left_ticket in enumerate(tickets):
        left_vector = vectors.get(left_ticket.id)
        if left_vector is None:
            continue
        for right_ticket in tickets[left_index + 1 :]:
            if left_ticket.screen_code != right_ticket.screen_code:
                continue
            right_vector = vectors.get(right_ticket.id)
            if right_vector is None:
                continue
            score = cosine_similarity(left_vector, right_vector)
            if score >= threshold:
                graph.add_edge(left_ticket.id, right_ticket.id, weight=score)

    ticket_by_id = {ticket.id: ticket for ticket in tickets}
    clusters: list[dict] = []
    for cluster_index, component in enumerate(nx.connected_components(graph), start=1):
        if len(component) < 2:
            continue
        component_tickets = [ticket_by_id[ticket_id] for ticket_id in component]
        representative = sorted(
            component_tickets,
            key=lambda ticket: (len(ticket.followers), ticket.updated_at, ticket.id),
            reverse=True,
        )[0]
        status_counts = Counter(ticket.status for ticket in component_tickets)
        category_counts = Counter(ticket.category or "미분류" for ticket in component_tickets)
        follower_count = sum(len(ticket.followers) for ticket in component_tickets)
        clusters.append(
            {
                "cluster_id": cluster_index,
                "representative_ticket_id": representative.id,
                "representative_title": representative.title,
                "screen_code": representative.screen_code,
                "screen_name": representative.screen_name,
                "size": len(component_tickets),
                "follower_count": follower_count,
                "ticket_ids": sorted(component),
                "status_counts": dict(status_counts),
                "category_counts": dict(category_counts),
                "tickets": [
                    ClusterTicket(
                        id=ticket.id,
                        title=ticket.title,
                        status=ticket.status,
                        screen_code=ticket.screen_code,
                        follower_count=len(ticket.followers),
                    )
                    for ticket in sorted(component_tickets, key=lambda item: item.id)
                ],
            }
        )
    return sorted(clusters, key=lambda row: (row["size"], row["follower_count"]), reverse=True)


def cluster_size_by_ticket_id(session: Session, threshold: float = 0.83) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for cluster in build_duplicate_clusters(session, threshold=threshold):
        for ticket_id in cluster["ticket_ids"]:
            mapping[int(ticket_id)] = int(cluster["size"])
    return mapping
