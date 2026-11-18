"""Build deterministic NuttyMod Client TAR, distribution ZIP and checksums."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.2'
NAME = f'NuttyMod-Client-{VERSION}'


def build_package(output):
    source = ROOT/'python'/'nuttymod_client.py'
    code = source.read_bytes()
    compile(code, source.name, 'exec')
    name = 'python/nuttymod_client.py'
    manifest = {'schema': 1, 'api': 'CubeBeta/1', 'name': 'NuttyMod Client', 'version': VERSION,
                'startup': name, 'files': {name: hashlib.sha256(code).hexdigest()}}
    files = {name: code, 'custom-cube.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    package = output/(NAME+'.tar')
    with tarfile.open(package, 'w') as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            archive.addfile(info, io.BytesIO(data))
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    (output/(NAME+'.tar.sha256')).write_text(checksum+'  '+package.name+'\n', encoding='utf-8', newline='\n')
    return package


def build_distribution(output):
    package = build_package(output)
    output = package.parent
    bundle = output/(NAME+'.zip')
    files = {
        package.name: package.read_bytes(),
        package.name+'.sha256': package.with_suffix('.tar.sha256').read_bytes(),
        'INSTALL.md': (ROOT/'docs'/'INSTALL.md').read_bytes(),
        'LICENSE': (ROOT/'LICENSE').read_bytes(),
        'source/nuttymod_client.py': (ROOT/'python'/'nuttymod_client.py').read_bytes(),
        'preview.png': (ROOT/'docs'/'display.png').read_bytes(),
        'GET-CPE-FLASHER.txt': b'Get CPE Flasher Tool: https://nuttyinc578.github.io/CPE-flashing-tool/\nInstall the client TAR through 05 Custom Cube and rebuild. Press F8 in game.\nSee INSTALL.md for the complete setup.\n',
    }
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    checksums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n'
                        for path in (package, bundle))
    (output/'SHA256SUMS.txt').write_text(checksums, encoding='utf-8', newline='\n')
    return package, bundle


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'downloads')
    for path in build_distribution(parser.parse_args().output):
        print(path)
