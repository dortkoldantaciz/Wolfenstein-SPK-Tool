# SPK Tool

A tool for extracting and repacking **SPK/MPK archive files** used by **Wolfenstein (2009)** (Raven Software / id Software).

The original community extractor ([Wolfenstein SPK MPK Extractor](https://www.moddb.com/games/wolfenstein/downloads/wolfenstein-spk-mpk-extractor-v02)) could only **extract** archives. This tool adds full **repacking** support, making it ideal for modding and translation projects.

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

- Format research based on [Wolfenstein SPK MPK Extractor](https://www.moddb.com/games/wolfenstein/downloads/wolfenstein-spk-mpk-extractor-v02) by daedalus
- Repacking implementation by dortkoldantaciz
