import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.database import Base
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageEdgeHistory
from backend.modules.trust_score.models import TrustScore
from backend.modules.anomaly.models import AnomalyDetection
from backend.modules.incidents.models import Incident
from backend.modules.lineage.temporal_service import TemporalLineageService
from backend.modules.lineage.health_propagation import get_critical_path, propagate_health_score, schedule_propagation
from backend.modules.lineage.anomaly_suppression import get_downstream_nodes
from backend.modules.lineage.silent_failure_detection import compare_schema

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:")
    # Register all models on Metadata
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()

def test_lineage_models_crud(db_session):
    """Verify that lineage nodes, edges, and edge history can be created and queried."""
    now = datetime.now(timezone.utc)
    
    # 1. Create nodes
    node_a = LineageNode(
        id=uuid.uuid4(),
        node_id="model.qolyx.node_a",
        name="node_a",
        type="model",
        schema="public",
        database="qolyx_prod",
        materialized_type="table",
        trust_score=100.0,
        last_updated_at=now,
        created_at=now,
        updated_at=now
    )
    node_b = LineageNode(
        id=uuid.uuid4(),
        node_id="model.qolyx.node_b",
        name="node_b",
        type="model",
        schema="public",
        database="qolyx_prod",
        materialized_type="table",
        trust_score=100.0,
        last_updated_at=now,
        created_at=now,
        updated_at=now
    )
    db_session.add_all([node_a, node_b])
    db_session.commit()
    
    # 2. Create edge
    edge = LineageEdge(
        id=uuid.uuid4(),
        source_node_id="model.qolyx.node_a",
        target_node_id="model.qolyx.node_b",
        edge_type="depends_on",
        valid_from=now,
        valid_to=None
    )
    db_session.add(edge)
    db_session.commit()
    
    # 3. Verify querying
    queried_node = db_session.query(LineageNode).filter_by(node_id="model.qolyx.node_a").first()
    assert queried_node is not None
    assert queried_node.name == "node_a"
    
    queried_edge = db_session.query(LineageEdge).filter_by(source_node_id="model.qolyx.node_a").first()
    assert queried_edge is not None
    assert queried_edge.target_node_id == "model.qolyx.node_b"

def test_temporal_lineage_service(db_session):
    """Test time-travel query functions in TemporalLineageService."""
    t_past = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_edge_birth = datetime(2026, 6, 5, 0, 0, 0, tzinfo=timezone.utc)
    t_future = datetime(2026, 6, 10, 0, 0, 0, tzinfo=timezone.utc)
    
    node_a = LineageNode(
        id=uuid.uuid4(),
        node_id="model.qolyx.node_a",
        name="node_a",
        type="model",
        schema="public",
        trust_score=100.0,
        last_updated_at=t_edge_birth,
        created_at=t_edge_birth,
        updated_at=t_edge_birth
    )
    node_b = LineageNode(
        id=uuid.uuid4(),
        node_id="model.qolyx.node_b",
        name="node_b",
        type="model",
        schema="public",
        trust_score=100.0,
        last_updated_at=t_edge_birth,
        created_at=t_edge_birth,
        updated_at=t_edge_birth
    )
    db_session.add_all([node_a, node_b])
    
    # Create temporal edge history
    history = LineageEdgeHistory(
        id=uuid.uuid4(),
        source_node_id="model.qolyx.node_a",
        target_node_id="model.qolyx.node_b",
        edge_type="depends_on",
        valid_from=t_edge_birth,
        valid_to=None,
        recorded_at=t_edge_birth
    )
    db_session.add(history)
    db_session.commit()
    
    # Query past (should be empty edges)
    past_graph = TemporalLineageService.get_lineage_at_time(db_session, "model.qolyx.node_a", t_past)
    assert len(past_graph["edges"]) == 0
    
    # Query future (should contain the edge)
    future_graph = TemporalLineageService.get_lineage_at_time(db_session, "model.qolyx.node_a", t_future)
    assert len(future_graph["edges"]) == 1
    assert future_graph["edges"][0]["source_node_id"] == "model.qolyx.node_a"

def test_temporal_lineage_diff(db_session):
    """Test get_lineage_diff between two different points in time."""
    t1 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 10, 0, 0, 0, tzinfo=timezone.utc)
    t_edge_birth = datetime(2026, 6, 5, 0, 0, 0, tzinfo=timezone.utc)
    
    node_a = LineageNode(id=uuid.uuid4(), node_id="model.qolyx.node_a", name="node_a", type="model", schema="public")
    node_b = LineageNode(id=uuid.uuid4(), node_id="model.qolyx.node_b", name="node_b", type="model", schema="public")
    db_session.add_all([node_a, node_b])
    
    history = LineageEdgeHistory(
        id=uuid.uuid4(),
        source_node_id="model.qolyx.node_a",
        target_node_id="model.qolyx.node_b",
        edge_type="depends_on",
        valid_from=t_edge_birth,
        valid_to=None,
        recorded_at=t_edge_birth
    )
    db_session.add(history)
    db_session.commit()
    
    diff = TemporalLineageService.get_lineage_diff(db_session, "model.qolyx.node_a", t1, t2)
    assert len(diff["nodes"]["added"]) > 0
    assert len(diff["edges"]["added"]) == 1
    assert diff["edges"]["added"][0]["source_node_id"] == "model.qolyx.node_a"

def test_impact_analysis(db_session):
    """Verify recursive downstream dependency tracking (impact analysis)."""
    now = datetime.now(timezone.utc)
    nodes = [
        LineageNode(id=uuid.uuid4(), node_id="A", name="A", type="model", schema="public"),
        LineageNode(id=uuid.uuid4(), node_id="B", name="B", type="model", schema="public"),
        LineageNode(id=uuid.uuid4(), node_id="C", name="C", type="model", schema="public"),
    ]
    db_session.add_all(nodes)
    
    edges = [
        LineageEdge(id=uuid.uuid4(), source_node_id="A", target_node_id="B", edge_type="depends_on", valid_from=now),
        LineageEdge(id=uuid.uuid4(), source_node_id="B", target_node_id="C", edge_type="depends_on", valid_from=now),
    ]
    db_session.add_all(edges)
    db_session.commit()
    
    downstream = get_downstream_nodes(db_session, "A")
    assert "B" in downstream
    assert "C" in downstream

def test_critical_path(db_session):
    """Test critical path detection based on the worst upstream health penalty."""
    now = datetime.now(timezone.utc)
    node_a = LineageNode(id=uuid.uuid4(), node_id="A", name="A", type="model", schema="public", trust_score=50.0)
    node_b = LineageNode(id=uuid.uuid4(), node_id="B", name="B", type="model", schema="public", trust_score=90.0)
    node_c = LineageNode(id=uuid.uuid4(), node_id="C", name="C", type="model", schema="public", trust_score=100.0)
    db_session.add_all([node_a, node_b, node_c])
    
    edges = [
        LineageEdge(id=uuid.uuid4(), source_node_id="A", target_node_id="C", edge_type="depends_on", valid_from=now),
        LineageEdge(id=uuid.uuid4(), source_node_id="B", target_node_id="C", edge_type="depends_on", valid_from=now),
    ]
    db_session.add_all(edges)
    db_session.commit()
    
    # Path to C should trace upstream to the worst node (A, trust_score=50.0 vs B, trust_score=90.0)
    crit_path = get_critical_path(db_session, "C")
    node_ids = [n["node_id"] for n in crit_path]
    assert "A" in node_ids
    assert "C" in node_ids

def test_health_propagation(db_session):
    """Test trust score penalty decay propagation to downstream nodes."""
    now = datetime.now(timezone.utc)
    node_a = LineageNode(id=uuid.uuid4(), node_id="A", name="A", type="model", schema="public", trust_score=100.0)
    node_b = LineageNode(id=uuid.uuid4(), node_id="B", name="B", type="model", schema="public", trust_score=100.0)
    db_session.add_all([node_a, node_b])
    
    edge = LineageEdge(id=uuid.uuid4(), source_node_id="A", target_node_id="B", edge_type="depends_on", valid_from=now)
    db_session.add(edge)
    db_session.commit()
    
    # Propagate health penalty starting with A = 60.0 (penalty = 40.0)
    propagate_health_score(db_session, "A", 60.0)
    
    # B should have a decayed penalty of 40.0 * 0.9 = 36.0, resulting in a score of 64.0
    db_session.refresh(node_b)
    assert node_b.trust_score == pytest.approx(64.0)

def test_schema_comparison(db_session):
    """Verify schema drift detection and initial baselining."""
    node_a = LineageNode(
        id=uuid.uuid4(),
        node_id="model.qolyx.node_a",
        name="node_a",
        type="model",
        schema="public",
        meta=None
    )
    db_session.add(node_a)
    db_session.commit()
    
    actual_schema = {
        "id": "INTEGER",
        "name": "VARCHAR",
        "created_at": "TIMESTAMP"
    }
    
    # First compare should baseline the schema
    res1 = compare_schema(db_session, "model.qolyx.node_a", actual_schema)
    assert res1["drift_detected"] is False
    assert "Baselined" in res1["message"]
    
    # Re-fetch node to check saved baseline
    db_session.refresh(node_a)
    assert node_a.meta["columns"] == actual_schema
    
    # Compare with identical schema (no drift)
    res2 = compare_schema(db_session, "model.qolyx.node_a", actual_schema)
    assert res2["drift_detected"] is False
    
    # Compare with drifted schema (added column)
    drifted_schema = {
        "id": "INTEGER",
        "name": "VARCHAR",
        "created_at": "TIMESTAMP",
        "status": "VARCHAR"
    }
    res3 = compare_schema(db_session, "model.qolyx.node_a", drifted_schema)
    assert res3["drift_detected"] is True
    assert "status" in res3["added"]
