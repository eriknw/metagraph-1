from metagraph import translator
from metagraph.plugins import has_pandas, has_networkx


if has_networkx and has_pandas:
    import networkx as nx
    from .types import NetworkXGraph
    from ..pandas.types import PandasEdgeMap

    # @translator
    # def edgemap_from_pandas(x: PandasEdgeMap, **props) -> NetworkXGraph:
    #     cur_props = PandasEdgeMap.Type.compute_abstract_properties(x, ["is_directed"])
    #
    #     if cur_props["is_directed"]:
    #         out = nx.DiGraph()
    #     else:
    #         out = nx.Graph()
    #
    #     g = x.value[[x.src_label, x.dst_label, x.weight_label]]
    #     out.add_weighted_edges_from(g.itertuples(index=False, name="WeightedEdge"))
    #     return NetworkXGraph(out, edge_weight_label="weight",)
