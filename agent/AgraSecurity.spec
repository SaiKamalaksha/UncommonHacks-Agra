# -*- mode: python ; coding: utf-8 -*-


hiddenimports = [
    'plyer.platforms.win.notification',

    # Pickled ML models reference these private modules dynamically.
    'sklearn.ensemble._forest',
    'sklearn.tree._classes',
    'sklearn.tree._criterion',
    'sklearn.tree._splitter',
    'sklearn.tree._tree',
    'sklearn.cluster._kmeans',
    'sklearn.preprocessing._data',
    'sklearn.decomposition._base',
    'sklearn.decomposition._pca',
    'sklearn.utils._cython_blas',
    'sklearn.utils._heap',
    'sklearn.utils._random',
    'sklearn.utils._sorting',
    'sklearn.utils._typedefs',
    'sklearn.utils._vector_sentinel',

    'hdbscan',
    'hdbscan.hdbscan_',
    'hdbscan.prediction',
    'hdbscan._hdbscan_boruvka',
    'hdbscan._hdbscan_linkage',
    'hdbscan._hdbscan_tree',
    'hdbscan._prediction_utils',
]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Kami\\UncommonHacks-Agra\\model', 'model')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AgraSecurity',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
