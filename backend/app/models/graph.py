from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True) # 实体名：如“酒后驾驶”
    category = Column(String(50))                      # 类别：如“违法行为”、“处罚”

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("graph_nodes.id")) # 起点
    target_id = Column(Integer, ForeignKey("graph_nodes.id")) # 终点
    relation = Column(String(100))                            # 关系：如“导致”、“依据”