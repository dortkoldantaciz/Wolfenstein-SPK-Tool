#!/usr/bin/env python3
"""
SPK Tool - Wolfenstein (2009) SPK/MPK Archive Packer & Unpacker

A command-line tool for extracting and repacking SPK/MPK archive files
used by Wolfenstein (2009) developed by Raven Software / id Software.

Supports all known chunk types: TXTR, SNDS, SGFX, MODL, VIDO, HKXA,
HKXR, HKXS, SKEL, PROC, PBBF, DECL, ENTS, BRAI, AASS.

Usage:
    Extract:  python spk_tool.py extract <input.spk> <output_dir>
    Pack:     python spk_tool.py pack <original.spk> <source_dir> <output.spk>
    Info:     python spk_tool.py info <input.spk>
    Batch:    python spk_tool.py batch-extract <input_dir> <output_dir>
              python spk_tool.py batch-pack <original_dir> <source_dir> <output_dir>

Author:  dortkoldantaciz (github.com/dortkoldantaciz)
License: MIT
Version: 1.0.0
"""

__version__ = "1.0.0"

import struct
import zlib
import os
import sys
import argparse
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

SPK_MAGIC = 0x12C  # File signature for SPK/MPK archives

# Chunk type magic numbers mapped to their file extensions
# The magic numbers are stored in reverse byte order in the archive
CHUNK_TYPES = {
    "TXTR": ".dds",       # DirectDraw Surface (textures)
    "SNDS": ".mp3",       # MPEG-1 Audio Layer 3
    "SGFX": ".SGFX",      # Scaleform GFx (UI)
    "MODL": ".md5r",      # MD5 Model (GPU representation)
    "VIDO": ".bik",       # Bink Video
    "HKXA": ".HKXA",      # Havok Animation
    "HKXR": ".af",        # Havok Ragdoll / Articulated Figure
    "HKXS": ".HKXS",      # Havok Collision
    "SKEL": ".SKEL",      # Havok Skeleton
    "PROC": ".procb",     # MD5RProc (processed geometry)
    "PBBF": ".MD5RBin",   # MD5R Binary
    "DECL": ".decls",     # Declarations
    "ENTS": ".emap",      # Entity Map
    "BRAI": ".brain",     # AI Brain
    "AASS": ".aas28",     # Area Awareness System
}

# Reverse mapping: extension -> chunk type
EXT_TO_CHUNK = {v.lower(): k for k, v in CHUNK_TYPES.items()}


# ─────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────

def format_size(size_bytes):
    """Format byte count into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def align4(value):
    """Round up to the next 4-byte boundary."""
    return (value + 3) & ~3


def print_header():
    """Print the tool banner."""
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║       SPK Tool v{:<8s}                        ║".format(__version__))
    print("  ║       Wolfenstein (2009) Archive Packer          ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()


# ─────────────────────────────────────────────────────────────
# SPK Archive Reading
# ─────────────────────────────────────────────────────────────

def read_archive_structure(archive_path):
    """Read the chunk structure and file table from an SPK/MPK archive.

    Args:
        archive_path: Path to the SPK/MPK archive file.

    Returns:
        A list of chunks, where each chunk is a dict:
        {
            "type":  str,   # e.g. "TXTR"
            "ext":   str,   # e.g. ".dds"
            "files": list,  # [(internal_path, file_size), ...]
        }
    """
    chunks = []

    with open(archive_path, "rb") as f:
        file_size = f.seek(0, 2)
        f.seek(0)

        # Verify file signature
        magic = struct.unpack("<I", f.read(4))[0]
        if magic != SPK_MAGIC:
            raise ValueError(
                f"Not a valid SPK/MPK file: expected magic 0x{SPK_MAGIC:X}, "
                f"got 0x{magic:X}"
            )

        # Iterate over compressed chunks
        while f.tell() < file_size:
            chunk_magic_bytes = f.read(4)
            if len(chunk_magic_bytes) < 4:
                break

            # Magic number is stored in reverse byte order
            chunk_type = chunk_magic_bytes[::-1].decode("ascii", errors="replace")
            uncompressed_size = struct.unpack("<I", f.read(4))[0]
            compressed_size = struct.unpack("<I", f.read(4))[0]

            # Read and decompress the chunk data
            compressed_data = f.read(compressed_size)
            decompressed = zlib.decompress(compressed_data)

            if len(decompressed) != uncompressed_size:
                raise ValueError(
                    f"Decompression size mismatch in {chunk_type} chunk: "
                    f"expected {uncompressed_size}, got {len(decompressed)}"
                )

            # Parse file table from decompressed data
            pos = 0
            num_files = struct.unpack_from("<I", decompressed, pos)[0]
            pos += 4

            files = []
            for _ in range(num_files):
                # Read null-terminated file name (without extension)
                name_end = decompressed.index(b"\x00", pos)
                name = decompressed[pos:name_end].decode("ascii")
                pos = name_end + 1

                # Read file size (stored twice, both values must match)
                size_a = struct.unpack_from("<I", decompressed, pos)[0]
                pos += 4
                size_b = struct.unpack_from("<I", decompressed, pos)[0]
                pos += 4

                if size_a != size_b:
                    raise ValueError(
                        f"Mismatched file sizes for '{name}': {size_a} vs {size_b}"
                    )

                files.append((name, size_a))

            ext = CHUNK_TYPES.get(chunk_type, f".{chunk_type.lower()}")
            chunks.append({
                "type": chunk_type,
                "ext": ext,
                "files": files,
            })

    return chunks


def extract_archive(archive_path, output_dir):
    """Extract all files from an SPK/MPK archive.

    Args:
        archive_path: Path to the SPK/MPK archive file.
        output_dir:   Directory to extract files into.

    Returns:
        Total number of files extracted.
    """
    archive_name = os.path.basename(archive_path)
    print(f"  Extracting: {archive_name}")

    with open(archive_path, "rb") as f:
        file_size = f.seek(0, 2)
        f.seek(0)

        # Verify signature
        magic = struct.unpack("<I", f.read(4))[0]
        if magic != SPK_MAGIC:
            raise ValueError(f"Not a valid SPK/MPK file (magic: 0x{magic:X})")

        total_files = 0
        log_lines = [archive_name]

        while f.tell() < file_size:
            chunk_magic_bytes = f.read(4)
            if len(chunk_magic_bytes) < 4:
                break

            chunk_type = chunk_magic_bytes[::-1].decode("ascii", errors="replace")
            uncompressed_size = struct.unpack("<I", f.read(4))[0]
            compressed_size = struct.unpack("<I", f.read(4))[0]

            ext = CHUNK_TYPES.get(chunk_type, f".{chunk_type.lower()}")

            # Decompress chunk
            compressed_data = f.read(compressed_size)
            decompressed = zlib.decompress(compressed_data)

            # Parse file table
            pos = 0
            num_files = struct.unpack_from("<I", decompressed, pos)[0]
            pos += 4

            file_entries = []
            for _ in range(num_files):
                name_end = decompressed.index(b"\x00", pos)
                name = decompressed[pos:name_end].decode("ascii")
                pos = name_end + 1

                size_a = struct.unpack_from("<I", decompressed, pos)[0]
                pos += 4
                size_b = struct.unpack_from("<I", decompressed, pos)[0]
                pos += 4

                file_entries.append((name, size_a))
                log_lines.append(f"\t{name}{ext}")

            log_lines.append("")

            # Align to 4-byte boundary after file table
            pos = align4(pos)

            # Extract files
            for name, size in file_entries:
                # Build output path
                parts = name.replace("/", os.sep).split(os.sep)
                file_dir = os.path.join(output_dir, *parts[:-1]) if len(parts) > 1 else output_dir
                os.makedirs(file_dir, exist_ok=True)

                out_path = os.path.join(file_dir, parts[-1] + ext)

                # Write file data
                file_data = decompressed[pos:pos + size]
                with open(out_path, "wb") as out_f:
                    out_f.write(file_data)

                pos += size
                pos = align4(pos)
                total_files += 1

            print(f"    {chunk_type} chunk: {num_files} file(s) extracted")

    # Write extraction log
    log_path = os.path.join(output_dir, "log.txt")
    with open(log_path, "w", encoding="utf-8") as log_f:
        log_f.write("\n".join(log_lines))

    print(f"  Total: {total_files} file(s) extracted")
    return total_files


# ─────────────────────────────────────────────────────────────
# SPK Archive Writing
# ─────────────────────────────────────────────────────────────

def build_chunk(chunk_type, file_entries, source_dir):
    """Build a compressed chunk from source files.

    The chunk format is:
        [4 bytes] Magic number (reversed)
        [4 bytes] Uncompressed data size
        [4 bytes] Compressed data size
        [N bytes] Zlib-compressed data

    The uncompressed data contains:
        [4 bytes]     Number of files
        For each file:
            [N bytes] Null-terminated file name (without extension)
            [4 bytes] File size (repeated twice)
        [padding]     Align to 4-byte boundary
        For each file:
            [N bytes] Raw file data
            [padding] Align to 4-byte boundary

    Args:
        chunk_type:   Chunk type string (e.g. "TXTR").
        file_entries: List of (internal_path, original_size) tuples.
        source_dir:   Directory containing the source files.

    Returns:
        bytes: Complete chunk data (header + compressed payload).
    """
    ext = CHUNK_TYPES.get(chunk_type, f".{chunk_type.lower()}")

    # ── Collect file data ──
    file_data_list = []
    missing_count = 0

    for file_name, original_size in file_entries:
        file_path = os.path.join(source_dir, file_name.replace("/", os.sep) + ext)

        if os.path.exists(file_path):
            with open(file_path, "rb") as fh:
                data = fh.read()
            file_data_list.append((file_name, data))
        else:
            print(f"    WARNING: File not found: {file_path}")
            print(f"             Padding with {original_size} zero bytes.")
            file_data_list.append((file_name, b"\x00" * original_size))
            missing_count += 1

    # ── Build uncompressed payload ──
    payload = bytearray()

    # Number of files
    payload += struct.pack("<I", len(file_data_list))

    # File table
    for name, data in file_data_list:
        payload += name.encode("ascii") + b"\x00"
        payload += struct.pack("<I", len(data))  # size written twice
        payload += struct.pack("<I", len(data))

    # Align file table to 4-byte boundary
    while len(payload) % 4 != 0:
        payload += b"\x00"

    # File data (each aligned to 4 bytes)
    for name, data in file_data_list:
        payload += data
        while len(payload) % 4 != 0:
            payload += b"\x00"

    # ── Compress ──
    compressed = zlib.compress(bytes(payload), zlib.Z_DEFAULT_COMPRESSION)

    # ── Build chunk header ──
    # Magic number stored in reverse byte order
    magic_bytes = chunk_type.encode("ascii")[::-1]
    header = (
        magic_bytes
        + struct.pack("<I", len(payload))
        + struct.pack("<I", len(compressed))
    )

    if missing_count:
        print(f"    WARNING: {missing_count} file(s) were missing in this chunk.")

    return header + compressed


def pack_archive(original_path, source_dir, output_path):
    """Repack an SPK/MPK archive using modified source files.

    The structure (chunk order, file order, chunk types) is read from the
    original archive so that the output is a faithful reconstruction.

    Args:
        original_path: Path to the original SPK/MPK archive (for structure).
        source_dir:    Directory containing the (possibly modified) files.
        output_path:   Path for the output SPK/MPK archive.

    Returns:
        int: Total number of files packed.
    """
    archive_name = os.path.basename(original_path)
    print(f"  Packing: {archive_name}")

    # Read original structure
    chunks = read_archive_structure(original_path)

    total_files = 0

    with open(output_path, "wb") as out:
        # Write file signature
        out.write(struct.pack("<I", SPK_MAGIC))

        # Rebuild each chunk
        for chunk in chunks:
            chunk_type = chunk["type"]
            file_count = len(chunk["files"])
            total_files += file_count

            print(f"    {chunk_type} chunk: {file_count} file(s)...", end=" ")
            chunk_data = build_chunk(chunk_type, chunk["files"], source_dir)
            out.write(chunk_data)
            print(f"({format_size(len(chunk_data))})")

    original_size = os.path.getsize(original_path)
    output_size = os.path.getsize(output_path)
    print(f"  Original size: {format_size(original_size)}")
    print(f"  New size:      {format_size(output_size)}")
    print(f"  Total: {total_files} file(s) packed")

    return total_files


# ─────────────────────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────────────────────

def cmd_info(args):
    """Display information about an SPK/MPK archive."""
    archive_path = args.archive
    if not os.path.isfile(archive_path):
        print(f"  ERROR: File not found: {archive_path}")
        return 1

    print(f"  Archive: {os.path.basename(archive_path)}")
    print(f"  Size:    {format_size(os.path.getsize(archive_path))}")
    print()

    try:
        chunks = read_archive_structure(archive_path)
    except ValueError as e:
        print(f"  ERROR: {e}")
        return 1

    total_files = 0
    total_uncompressed = 0

    for chunk in chunks:
        chunk_type = chunk["type"]
        ext = chunk["ext"]
        files = chunk["files"]
        chunk_size = sum(size for _, size in files)
        total_files += len(files)
        total_uncompressed += chunk_size

        print(f"  ┌─ {chunk_type} Chunk ({ext}) ── {len(files)} file(s), "
              f"{format_size(chunk_size)} uncompressed")

        for i, (name, size) in enumerate(files):
            connector = "└" if i == len(files) - 1 else "├"
            print(f"  │  {connector}── {name}{ext}  ({format_size(size)})")

        print()

    print(f"  Summary: {len(chunks)} chunk(s), {total_files} file(s), "
          f"{format_size(total_uncompressed)} total uncompressed")
    return 0


def cmd_extract(args):
    """Extract files from an SPK/MPK archive."""
    archive_path = args.archive
    output_dir = args.output

    if not os.path.isfile(archive_path):
        print(f"  ERROR: File not found: {archive_path}")
        return 1

    os.makedirs(output_dir, exist_ok=True)

    try:
        start = time.time()
        count = extract_archive(archive_path, output_dir)
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
    except (ValueError, zlib.error) as e:
        print(f"  ERROR: {e}")
        return 1

    return 0


def cmd_pack(args):
    """Repack modified files into an SPK/MPK archive."""
    original_path = args.original
    source_dir = args.source
    output_path = args.output

    if not os.path.isfile(original_path):
        print(f"  ERROR: Original archive not found: {original_path}")
        return 1

    if not os.path.isdir(source_dir):
        print(f"  ERROR: Source directory not found: {source_dir}")
        return 1

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        start = time.time()
        count = pack_archive(original_path, source_dir, output_path)
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
    except (ValueError, zlib.error) as e:
        print(f"  ERROR: {e}")
        return 1

    return 0


def cmd_batch_extract(args):
    """Extract all SPK/MPK files from a directory."""
    input_dir = args.input_dir
    output_dir = args.output_dir

    if not os.path.isdir(input_dir):
        print(f"  ERROR: Directory not found: {input_dir}")
        return 1

    archives = sorted(
        f for f in os.listdir(input_dir)
        if f.lower().endswith((".spk", ".mpk"))
    )

    if not archives:
        print(f"  ERROR: No SPK/MPK files found in: {input_dir}")
        return 1

    print(f"  Found {len(archives)} archive(s) in: {input_dir}")
    print()

    os.makedirs(output_dir, exist_ok=True)
    total = 0
    start = time.time()

    for archive_name in archives:
        archive_path = os.path.join(input_dir, archive_name)
        try:
            count = extract_archive(archive_path, output_dir)
            total += count
        except (ValueError, zlib.error) as e:
            print(f"  ERROR extracting {archive_name}: {e}")

        print()

    elapsed = time.time() - start
    print(f"  Batch complete: {total} file(s) from {len(archives)} archive(s) "
          f"in {elapsed:.2f}s")
    return 0


def cmd_batch_pack(args):
    """Repack all SPK/MPK files using modified source files."""
    original_dir = args.original_dir
    source_dir = args.source_dir
    output_dir = args.output_dir

    if not os.path.isdir(original_dir):
        print(f"  ERROR: Original directory not found: {original_dir}")
        return 1

    if not os.path.isdir(source_dir):
        print(f"  ERROR: Source directory not found: {source_dir}")
        return 1

    archives = sorted(
        f for f in os.listdir(original_dir)
        if f.lower().endswith((".spk", ".mpk"))
    )

    if not archives:
        print(f"  ERROR: No SPK/MPK files found in: {original_dir}")
        return 1

    print(f"  Found {len(archives)} archive(s) to repack")
    print()

    os.makedirs(output_dir, exist_ok=True)
    total = 0
    start = time.time()

    for archive_name in archives:
        original_path = os.path.join(original_dir, archive_name)
        output_path = os.path.join(output_dir, archive_name)
        try:
            count = pack_archive(original_path, source_dir, output_path)
            total += count
        except (ValueError, zlib.error) as e:
            print(f"  ERROR packing {archive_name}: {e}")

        print()

    elapsed = time.time() - start
    print(f"  Batch complete: {total} file(s) into {len(archives)} archive(s) "
          f"in {elapsed:.2f}s")
    return 0


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="spk_tool",
        description=(
            "SPK Tool - Extract and repack Wolfenstein (2009) SPK/MPK archives.\n\n"
            "Supports all known chunk types including textures (DDS), sounds (MP3),\n"
            "UI assets (SGFX/GFx), models, videos, and more."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s info english.spk\n"
            "  %(prog)s extract english.spk ./extracted\n"
            "  %(prog)s pack english.spk ./modified ./english_new.spk\n"
            "  %(prog)s batch-extract ./spk_files ./extracted\n"
            "  %(prog)s batch-pack ./spk_files ./modified ./repacked\n"
        ),
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── info ──
    p_info = subparsers.add_parser(
        "info", help="Display archive contents and structure"
    )
    p_info.add_argument("archive", help="Path to the SPK/MPK archive")

    # ── extract ──
    p_extract = subparsers.add_parser(
        "extract", help="Extract all files from an archive"
    )
    p_extract.add_argument("archive", help="Path to the SPK/MPK archive")
    p_extract.add_argument("output", help="Output directory for extracted files")

    # ── pack ──
    p_pack = subparsers.add_parser(
        "pack",
        help="Repack modified files into an archive",
        description=(
            "Reads the chunk structure from the original archive, then rebuilds\n"
            "the archive using files from the source directory. Files must be in\n"
            "the same directory structure as the extraction output."
        ),
    )
    p_pack.add_argument(
        "original", help="Path to the original SPK/MPK archive (for structure)"
    )
    p_pack.add_argument(
        "source", help="Directory containing the (modified) extracted files"
    )
    p_pack.add_argument("output", help="Path for the output SPK/MPK archive")

    # ── batch-extract ──
    p_bextract = subparsers.add_parser(
        "batch-extract", help="Extract all archives from a directory"
    )
    p_bextract.add_argument(
        "input_dir", help="Directory containing SPK/MPK archives"
    )
    p_bextract.add_argument(
        "output_dir", help="Output directory for extracted files"
    )

    # ── batch-pack ──
    p_bpack = subparsers.add_parser(
        "batch-pack", help="Repack all archives from a directory"
    )
    p_bpack.add_argument(
        "original_dir", help="Directory containing original SPK/MPK archives"
    )
    p_bpack.add_argument(
        "source_dir", help="Directory containing the (modified) extracted files"
    )
    p_bpack.add_argument(
        "output_dir", help="Output directory for repacked archives"
    )

    args = parser.parse_args()

    print_header()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "info": cmd_info,
        "extract": cmd_extract,
        "pack": cmd_pack,
        "batch-extract": cmd_batch_extract,
        "batch-pack": cmd_batch_pack,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
