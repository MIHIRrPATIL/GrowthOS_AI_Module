"""
GrowthOS Mock Customer Graph Model (Neo4j Bridge)
Maps ingested behavioral events and signals into customer relationship nodes.
"""

from typing import Dict, List, Any
from schemas import EventEnvelope, DerivedBehavioralSignal


class CustomerGraphBridge:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []

    def ingest_event_to_graph(self, event: EventEnvelope):
        cust_id = event.customer_id or event.anonymous_id
        session_id = event.session_id

        # 1. Customer Node
        if cust_id not in self.nodes:
            self.nodes[cust_id] = {
                "id": cust_id,
                "label": "Customer" if event.customer_id else "AnonymousUser",
                "properties": {
                    "anonymous_id": event.anonymous_id,
                    "first_seen": event.timestamp,
                    "last_seen": event.timestamp,
                    "device_type": event.device.device_type
                }
            }
        else:
            self.nodes[cust_id]["properties"]["last_seen"] = event.timestamp
            if event.customer_id:
                self.nodes[cust_id]["label"] = "Customer"
                self.nodes[cust_id]["properties"]["customer_id"] = event.customer_id

        # 2. Session Node
        if session_id not in self.nodes:
            self.nodes[session_id] = {
                "id": session_id,
                "label": "Session",
                "properties": {
                    "started_at": event.timestamp,
                    "entry_url": event.page.url,
                    "utm_source": event.utm.source,
                    "utm_campaign": event.utm.campaign
                }
            }
            self.relationships.append({
                "from": cust_id,
                "to": session_id,
                "type": "PERFORMED_SESSION"
            })

        # 3. Product View Edge
        if event.event_name == "product.viewed":
            product_id = event.properties.get("product_id") or "prod_unknown"
            if product_id not in self.nodes:
                self.nodes[product_id] = {
                    "id": product_id,
                    "label": "Product",
                    "properties": {
                        "name": event.properties.get("name"),
                        "price": event.properties.get("price"),
                        "category": event.properties.get("category")
                    }
                }
            self.relationships.append({
                "from": cust_id,
                "to": product_id,
                "type": "VIEWED",
                "properties": {"timestamp": event.timestamp, "session_id": session_id}
            })

        # 4. Cart Added Edge
        elif event.event_name == "cart.item_added":
            product_id = event.properties.get("product_id") or "prod_unknown"
            self.relationships.append({
                "from": cust_id,
                "to": product_id,
                "type": "ADDED_TO_CART",
                "properties": {
                    "timestamp": event.timestamp,
                    "quantity": event.properties.get("quantity", 1)
                }
            })

    def attach_signal_to_graph(self, signal: DerivedBehavioralSignal):
        user_key = signal.customer_id or signal.anonymous_id
        sig_id = signal.signal_id

        self.nodes[sig_id] = {
            "id": sig_id,
            "label": "BehavioralSignal",
            "properties": {
                "signal_type": signal.signal_type,
                "confidence": signal.confidence,
                "summary": signal.summary,
                "detected_at": signal.detected_at
            }
        }

        self.relationships.append({
            "from": user_key,
            "to": sig_id,
            "type": "EXHIBITS_SIGNAL"
        })

    def get_graph_for_customer(self, customer_id: str) -> Dict[str, Any]:
        related_rel = [r for r in self.relationships if r["from"] == customer_id or r["to"] == customer_id]
        node_ids = set([customer_id] + [r["from"] for r in related_rel] + [r["to"] for r in related_rel])
        relevant_nodes = [self.nodes[nid] for nid in node_ids if nid in self.nodes]

        return {
            "customer_id": customer_id,
            "nodes": relevant_nodes,
            "relationships": related_rel,
            "total_nodes": len(relevant_nodes),
            "total_edges": len(related_rel)
        }
