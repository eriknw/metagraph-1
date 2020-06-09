from metagraph import ConcreteType, dtypes
from metagraph.types import Vector, Matrix, NodeSet, NodeMap, EdgeSet, EdgeMap
from metagraph.wrappers import (
    NodeSetWrapper,
    NodeMapWrapper,
    EdgeSetWrapper,
    EdgeMapWrapper,
)
from metagraph.plugins import has_grblas

from typing import List, Dict, Any


if has_grblas:
    import grblas

    dtype_mg_to_grblas = {
        dtypes.bool: grblas.dtypes.BOOL,
        dtypes.int8: grblas.dtypes.INT8,
        dtypes.int16: grblas.dtypes.INT16,
        dtypes.int32: grblas.dtypes.INT32,
        dtypes.int64: grblas.dtypes.INT64,
        dtypes.uint8: grblas.dtypes.UINT8,
        dtypes.uint16: grblas.dtypes.UINT16,
        dtypes.uint32: grblas.dtypes.UINT32,
        dtypes.uint64: grblas.dtypes.UINT64,
        dtypes.float32: grblas.dtypes.FP32,
        dtypes.float64: grblas.dtypes.FP64,
    }

    dtype_grblas_to_mg = {v.name: k for k, v in dtype_mg_to_grblas.items()}

    class GrblasVectorType(ConcreteType, abstract=Vector):
        value_type = grblas.Vector

        @classmethod
        def _compute_abstract_properties(
            cls, obj, props: List[str], known_props: Dict[str, Any]
        ) -> Dict[str, Any]:
            ret = known_props.copy()

            # fast properties
            for prop in {"is_dense", "dtype"} - ret.keys():
                if prop == "is_dense":
                    ret[prop] = obj.nvals == obj.size
                if prop == "dtype":
                    ret[prop] = dtypes.dtypes_simplified[
                        dtype_grblas_to_mg[obj.dtype.name]
                    ]

            return ret

        @classmethod
        def assert_equal(cls, obj1, obj2, props1, props2, *, rel_tol=1e-9, abs_tol=0.0):
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            if obj1.dtype.name in {"FP32", "FP64"}:
                assert obj1.isclose(
                    obj2, rel_tol=rel_tol, abs_tol=abs_tol, check_dtype=True
                )
            else:
                assert obj1.isequal(obj2, check_dtype=True)

    class GrblasNodeSet(NodeSetWrapper, abstract=NodeSet):
        def __init__(self, data):
            self._assert_instance(data, grblas.Vector)
            self.value = data

        @classmethod
        def assert_equal(
            cls, obj1, obj2, props1, props2, *, rel_tol=None, abs_tol=None
        ):
            v1, v2 = obj1.value, obj2.value
            assert v1.size == v2.size, f"size mismatch: {v1.size} != {v2.size}"
            assert v1.nvals == v2.nvals, f"num nodes mismatch: {v1.nvals} != {v2.nvals}"
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            # Compare
            shape_match = obj1.value.ewise_mult(obj2.value, grblas.binary.pair).new()
            assert shape_match.nvals == v1.nvals, f"node ids do not match"

    class GrblasNodeMap(NodeMapWrapper, abstract=NodeMap):
        def __init__(self, data):
            self._assert_instance(data, grblas.Vector)
            self.value = data

        def __getitem__(self, node_id):
            return self.value[node_id].value

        @property
        def num_nodes(self):
            return self.value.nvals

        @classmethod
        def _compute_abstract_properties(
            cls, obj, props: List[str], known_props: Dict[str, Any]
        ) -> Dict[str, Any]:
            ret = known_props.copy()

            # fast properties
            for prop in {"dtype"} - ret.keys():
                if prop == "dtype":
                    ret[prop] = dtypes.dtypes_simplified[
                        dtype_grblas_to_mg[obj.value.dtype.name]
                    ]

            # slow properties, only compute if asked
            for prop in props - ret.keys():
                if prop == "weights":
                    if ret["dtype"] == "str":
                        weights = "any"
                    elif ret["dtype"] == "bool":
                        weights = "non-negative"
                    else:
                        min_val = obj.value.reduce(grblas.monoid.min).new().value
                        if min_val < 0:
                            weights = "any"
                        elif min_val == 0:
                            weights = "non-negative"
                        else:
                            weights = "positive"
                    ret[prop] = weights

            return ret

        @classmethod
        def assert_equal(cls, obj1, obj2, props1, props2, *, rel_tol=1e-9, abs_tol=0.0):
            v1, v2 = obj1.value, obj2.value
            assert v1.size == v2.size, f"size mismatch: {v1.size} != {v2.size}"
            assert v1.nvals == v2.nvals, f"num nodes mismatch: {v1.nvals} != {v2.nvals}"
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            # Compare
            if v1.dtype.name in {"FP32", "FP64"}:
                assert obj1.value.isclose(obj2.value, rel_tol=rel_tol, abs_tol=abs_tol)
            else:
                assert obj1.value.isequal(obj2.value)

    class GrblasMatrixType(ConcreteType, abstract=Matrix):
        value_type = grblas.Matrix
        abstract_property_specificity_limits = {"is_dense": False}

        @classmethod
        def _compute_abstract_properties(
            cls, obj, props: List[str], known_props: Dict[str, Any]
        ) -> Dict[str, Any]:
            ret = known_props.copy()

            # fast properties
            for prop in {"is_dense", "is_square", "dtype"} - ret.keys():
                if prop == "is_dense":
                    ret[prop] = False
                if prop == "is_square":
                    ret[prop] = obj.nrows == obj.ncols
                if prop == "dtype":
                    ret[prop] = dtypes.dtypes_simplified[
                        dtype_grblas_to_mg[obj.dtype.name]
                    ]

            # slow properties, only compute if asked
            for prop in props - ret.keys():
                if prop == "is_symmetric":
                    ret[prop] = obj == obj.T.new()

            return ret

        @classmethod
        def assert_equal(cls, obj1, obj2, props1, props2, *, rel_tol=1e-9, abs_tol=0.0):
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            if obj1.dtype.name in {"FP32", "FP64"}:
                assert obj1.isclose(
                    obj2, rel_tol=rel_tol, abs_tol=abs_tol, check_dtype=True
                )
            else:
                assert obj1.isequal(obj2, check_dtype=True)

    class GrblasEdgeSet(EdgeSetWrapper, abstract=EdgeSet):
        def __init__(
            self, data, transposed=False,
        ):
            self._assert_instance(data, grblas.Matrix)
            self._assert(data.nrows == data.ncols, "adjacency matrix must be square")
            self.value = data
            self.transposed = transposed

        def show(self):
            return self.value.show()

        @classmethod
        def _compute_abstract_properties(
            cls, obj, props: List[str], known_props: Dict[str, Any]
        ) -> Dict[str, Any]:
            ret = known_props.copy()

            # slow properties, only compute if asked
            for prop in props - ret.keys():
                if prop == "is_directed":
                    ret[prop] = obj.value != obj.value.T.new()

            return ret

        @classmethod
        def assert_equal(cls, obj1, obj2, props1, props2, *, rel_tol=1e-9, abs_tol=0.0):
            v1, v2 = obj1.value, obj2.value
            assert v1.nrows == v2.nrows, f"size mismatch: {v1.nrows} != {v2.nrows}"
            assert v1.nvals == v2.nvals, f"num nodes mismatch: {v1.nvals} != {v2.nvals}"
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            # Handle transposed states
            d1 = v1.T if obj1.transposed else v1
            d2 = v2.T if obj2.transposed else v2
            # Compare
            shape_match = d1.ewise_mult(d2, grblas.binary.pair).new()
            assert shape_match.nvals == v1.nvals, f"edges do not match"

    class GrblasEdgeMap(EdgeMapWrapper, abstract=EdgeMap):
        def __init__(
            self, data, transposed=False,
        ):
            self._assert_instance(data, grblas.Matrix)
            self._assert(data.nrows == data.ncols, "adjacency matrix must be square")
            self.value = data
            self.transposed = transposed

        def show(self):
            return self.value.show()

        @classmethod
        def _compute_abstract_properties(
            cls, obj, props: List[str], known_props: Dict[str, Any]
        ) -> Dict[str, Any]:
            ret = known_props.copy()

            # fast properties
            for prop in {"dtype"} - ret.keys():
                if prop == "dtype":
                    ret[prop] = dtype_grblas_to_mg[obj.value.dtype.name]

            # slow properties, only compute if asked
            for prop in props - ret.keys():
                if prop == "is_directed":
                    ret[prop] = obj.value != obj.value.T.new()
                if prop == "weights":
                    if ret["dtype"] == "str":
                        weights = "any"
                    elif ret["dtype"] == "bool":
                        weights = "non-negative"
                    else:
                        min_val = obj.value.reduce_scalar(grblas.monoid.min).new().value
                        if min_val < 0:
                            weights = "any"
                        elif min_val == 0:
                            weights = "non-negative"
                        else:
                            weights = "positive"
                    ret[prop] = weights

            return ret

        @classmethod
        def assert_equal(cls, obj1, obj2, props1, props2, *, rel_tol=1e-9, abs_tol=0.0):
            v1, v2 = obj1.value, obj2.value
            assert v1.nrows == v2.nrows, f"size mismatch: {v1.nrows} != {v2.nrows}"
            assert v1.nvals == v2.nvals, f"num nodes mismatch: {v1.nvals} != {v2.nvals}"
            assert props1 == props2, f"property mismatch: {props1} != {props2}"
            # Handle transposed states
            d1 = v1.T if obj1.transposed else v1
            d2 = v2.T if obj2.transposed else v2
            # Compare
            if v1.dtype.name in {"FP32", "FP64"}:
                assert d1.isclose(d2, rel_tol=rel_tol, abs_tol=abs_tol)
            else:
                assert d1.isequal(d2)
