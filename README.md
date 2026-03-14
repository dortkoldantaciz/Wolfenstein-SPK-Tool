# SPK Tool

A command-line tool for extracting and repacking **SPK/MPK archive files** used by **Wolfenstein (2009)** (Raven Software / id Software).

The original community extractor ([Wolfenstein SPK MPK Extractor](https://forum.xentax.com)) could only **extract** archives. This tool adds full **repacking** support, making it ideal for modding and translation projects.

## Features

- **Extract** all files from SPK/MPK archives
- **Repack** modified files back into SPK/MPK format
- **Batch** extract/repack multiple archives at once
- **Info** view to inspect archive structure
- Supports all known chunk types (see below)
- Pure Python — no external dependencies
- Cross-platform (Windows, Linux, macOS)

## Requirements

- Python 3.6 or later (uses only standard library modules)

## Usage

```
python spk_tool.py <command> [arguments]
```

### Commands

| Command         | Description                              |
|-----------------|------------------------------------------|
| `info`          | Display archive contents and structure   |
| `extract`       | Extract all files from an archive        |
| `pack`          | Repack modified files into an archive    |
| `batch-extract` | Extract all archives from a directory    |
| `batch-pack`    | Repack all archives from a directory     |

### Examples

**View archive info:**
```bash
python spk_tool.py info english.spk
```

**Extract a single archive:**
```bash
python spk_tool.py extract english.spk ./extracted
```

**Repack a modified archive:**
```bash
python spk_tool.py pack english.spk ./modified ./english_new.spk
```

**Batch extract all archives:**
```bash
python spk_tool.py batch-extract ./spk_files ./extracted
```

**Batch repack all archives:**
```bash
python spk_tool.py batch-pack ./original_spk ./modified ./repacked
```

## Modding Workflow

Here's the typical workflow for modding Wolfenstein (2009) SPK files:

```
1. Extract original SPK    →  python spk_tool.py extract english.spk ./work
2. Edit files (DDS, SGFX)  →  (use your favorite editor)
3. Repack into new SPK     →  python spk_tool.py pack english.spk ./work ./english_new.spk
4. Replace in game folder  →  copy english_new.spk to game directory
```

> **Note:** The `pack` command requires the **original archive** to read the chunk structure (file order, chunk types). It then reads the actual file data from your **source directory**.

## SPK File Format

SPK/MPK archives use the following binary structure:

```
[4 bytes]  File signature: 0x12C (300)

For each chunk:
  [4 bytes]  Chunk magic number (reversed, e.g. "TXTR" stored as "RTXT")
  [4 bytes]  Uncompressed data size
  [4 bytes]  Compressed data size (zlib)
  [N bytes]  Zlib-compressed payload

  The decompressed payload contains:
    [4 bytes]         Number of files
    For each file:
      [N+1 bytes]     Null-terminated file path (without extension)
      [4 bytes]       File size
      [4 bytes]       File size (repeated)
    [0-3 bytes]       Padding to 4-byte alignment
    For each file:
      [N bytes]       Raw file data
      [0-3 bytes]     Padding to 4-byte alignment
```

## Supported Chunk Types

| Magic  | Extension   | Content Type                         |
|--------|-------------|--------------------------------------|
| `TXTR` | `.dds`      | DirectDraw Surface (textures)        |
| `SNDS` | `.mp3`      | MPEG-1 Audio Layer 3 (sounds)        |
| `SGFX` | `.SGFX`     | Scaleform GFx (UI elements)          |
| `MODL` | `.md5r`     | MD5 Model (GPU representation)       |
| `VIDO` | `.bik`      | Bink Video                           |
| `HKXA` | `.HKXA`     | Havok Animation                      |
| `HKXR` | `.af`       | Havok Ragdoll / Articulated Figure   |
| `HKXS` | `.HKXS`     | Havok Collision                      |
| `SKEL` | `.SKEL`     | Havok Skeleton                       |
| `PROC` | `.procb`    | MD5RProc (processed geometry)        |
| `PBBF` | `.MD5RBin`  | MD5R Binary                          |
| `DECL` | `.decls`    | Declarations                         |
| `ENTS` | `.emap`     | Entity Map                           |
| `BRAI` | `.brain`    | AI Brain                             |
| `AASS` | `.aas28`    | Area Awareness System                |

## Credits

- Format research based on [Wolfenstein SPK MPK Extractor](https://forum.xentax.com) by daedalus (thx to asmxtx)
- Repacking implementation by Bedirhan

## License

MIT License — see [LICENSE](LICENSE) for details.
