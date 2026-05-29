"""Python implementation of the procedural mesh binary payload contract."""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

MCPM_MAGIC = 0x4D43504D
MCPM_VERSION = 1
MCPM_HEADER_SIZE = 104
MAX_VERTEX_COUNT = 1_000_000
MAX_INDEX_COUNT = 6_000_000
MAX_PAYLOAD_BYTES = 256 * 1024 * 1024
MAX_ABS_COORDINATE = 10_000_000.0
FLAG_HAS_UV = 0x01
FLAG_HAS_TANGENT = 0x02
FLAG_HAS_COLOR = 0x04
FLAG_HAS_MATERIAL_ID = 0x08
SUPPORTED_FLAGS = FLAG_HAS_UV | FLAG_HAS_TANGENT | FLAG_HAS_COLOR | FLAG_HAS_MATERIAL_ID


class MeshValidationError(ValueError):
    """Raised when a mesh payload violates the MCPM protocol contract."""


@dataclass
class ProceduralMeshHeader:
    flags: int
    vertex_count: int
    index_count: int
    payload_crc32: int
    request_id: int
    mcp_id: str
    magic: int = MCPM_MAGIC
    version: int = MCPM_VERSION
    header_size: int = MCPM_HEADER_SIZE
    reserved: int = 0

    def to_bytes(self) -> bytes:
        mcp_bytes = self.mcp_id.encode("utf-8")[:63]
        mcp_bytes = mcp_bytes + b"\0" * (64 - len(mcp_bytes))
        return struct.pack(
            "<IIIIIIIIQ64s",
            self.magic,
            self.version,
            self.header_size,
            self.flags,
            self.vertex_count,
            self.index_count,
            self.payload_crc32,
            self.reserved,
            self.request_id,
            mcp_bytes,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProceduralMeshHeader":
        if len(data) < MCPM_HEADER_SIZE:
            raise MeshValidationError("header too short")
        magic, version, header_size, flags, vertex_count, index_count, payload_crc32, reserved, request_id, mcp_bytes = struct.unpack(
            "<IIIIIIIIQ64s", data[:MCPM_HEADER_SIZE]
        )
        mcp_id = mcp_bytes.split(b"\0", 1)[0].decode("utf-8", errors="replace")
        return cls(
            magic=magic,
            version=version,
            header_size=header_size,
            flags=flags,
            vertex_count=vertex_count,
            index_count=index_count,
            payload_crc32=payload_crc32,
            request_id=request_id,
            reserved=reserved,
            mcp_id=mcp_id,
        )


@dataclass
class ProceduralMeshPayload:
    mcp_id: str
    request_id: int
    positions: List[List[float]]
    normals: List[List[float]]
    indices: List[int]
    uvs: Optional[List[List[float]]] = None
    tangents: Optional[List[List[float]]] = None
    colors: Optional[List[List[int]]] = None
    material_ids: Optional[List[int]] = None
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    @property
    def flags(self) -> int:
        flags = 0
        if self.uvs is not None:
            flags |= FLAG_HAS_UV
        if self.tangents is not None:
            flags |= FLAG_HAS_TANGENT
        if self.colors is not None:
            flags |= FLAG_HAS_COLOR
        if self.material_ids is not None:
            flags |= FLAG_HAS_MATERIAL_ID
        return flags

    @property
    def header(self) -> ProceduralMeshHeader:
        return ProceduralMeshHeader(self.flags, len(self.positions), len(self.indices), 0, self.request_id, self.mcp_id)

    def validate(self) -> None:
        if len(self.positions) > MAX_VERTEX_COUNT:
            raise MeshValidationError("vertex count too large")
        if len(self.indices) > MAX_INDEX_COUNT:
            raise MeshValidationError("index count too large")
        if len(self.indices) % 3 != 0:
            raise MeshValidationError("index count must be a multiple of 3")
        if len(self.normals) != len(self.positions):
            raise MeshValidationError("normals length mismatch")
        for pos in self.positions:
            if len(pos) < 3 or not all(math.isfinite(float(v)) for v in pos[:3]):
                raise MeshValidationError("invalid position")
            if any(abs(float(v)) > MAX_ABS_COORDINATE for v in pos[:3]):
                raise MeshValidationError("position exceeds max coordinate")
        for normal in self.normals:
            if len(normal) < 3 or not all(math.isfinite(float(v)) for v in normal[:3]):
                raise MeshValidationError("invalid normal")
        for idx in self.indices:
            if int(idx) < 0 or int(idx) >= len(self.positions):
                raise MeshValidationError(f"index out of bounds: {idx}")
        if self.uvs is not None:
            if len(self.uvs) != len(self.positions):
                raise MeshValidationError("uv length mismatch")
            for uv in self.uvs:
                if len(uv) < 2 or not all(math.isfinite(float(v)) for v in uv[:2]):
                    raise MeshValidationError("invalid uv")
        if self.tangents is not None and len(self.tangents) != len(self.positions):
            raise MeshValidationError("tangent length mismatch")
        if self.colors is not None and len(self.colors) != len(self.positions):
            raise MeshValidationError("color length mismatch")
        if self.material_ids is not None and len(self.material_ids) != len(self.indices) // 3:
            raise MeshValidationError("material id length mismatch")
        self.warnings = mesh_warnings(self.indices)
        if self.total_bytes() > MAX_PAYLOAD_BYTES:
            raise MeshValidationError("payload too large")

    def total_bytes(self) -> int:
        v = len(self.positions)
        i = len(self.indices)
        size = MCPM_HEADER_SIZE + v * 12 + v * 12 + i * 4
        if self.uvs is not None:
            size += v * 8
        if self.tangents is not None:
            size += v * 16
        if self.colors is not None:
            size += v * 4
        if self.material_ids is not None:
            size += (i // 3) * 2
        return size

    def to_bytes(self) -> bytes:
        payload = bytearray()
        for pos in self.positions:
            payload.extend(struct.pack("<fff", float(pos[0]), float(pos[1]), float(pos[2])))
        for normal in self.normals:
            payload.extend(struct.pack("<fff", float(normal[0]), float(normal[1]), float(normal[2])))
        if self.uvs is not None:
            for uv in self.uvs:
                payload.extend(struct.pack("<ff", float(uv[0]), float(uv[1])))
        if self.tangents is not None:
            for tangent in self.tangents:
                payload.extend(struct.pack("<ffff", float(tangent[0]), float(tangent[1]), float(tangent[2]), float(tangent[3])))
        if self.colors is not None:
            for color in self.colors:
                payload.extend(bytes(int(max(0, min(255, v))) for v in color[:4]))
        if self.material_ids is not None:
            for material_id in self.material_ids:
                payload.extend(struct.pack("<H", int(material_id)))
        for index in self.indices:
            payload.extend(struct.pack("<I", int(index)))
        header = self.header
        header.payload_crc32 = zlib.crc32(payload) & 0xFFFFFFFF
        return header.to_bytes() + bytes(payload)

    def to_dict(self) -> dict:
        return {
            "mcp_id": self.mcp_id,
            "request_id": self.request_id,
            "vertex_count": len(self.positions),
            "index_count": len(self.indices),
            "positions": self.positions,
            "normals": self.normals,
            "indices": self.indices,
            "uvs": self.uvs,
            "warnings": list(self.warnings),
            "flags": self.flags,
        }


def mesh_warnings(indices: Sequence[int]) -> List[str]:
    warnings: List[str] = []
    seen = set()
    for tri_index in range(0, len(indices), 3):
        tri = tuple(int(v) for v in indices[tri_index : tri_index + 3])
        if len(set(tri)) < 3:
            warnings.append(f"DEGENERATE_TRIANGLE:{tri_index // 3}")
            continue
        key = tuple(sorted(tri))
        if key in seen:
            warnings.append(f"DUPLICATE_TRIANGLE:{tri_index // 3}")
        seen.add(key)
    return warnings
