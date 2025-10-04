# PyInstaller hook for tiktok_uploader
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules
hiddenimports = collect_submodules('tiktok_uploader')

# Add specific modules that might be missed
hiddenimports += [
    'tiktok_uploader.tiktok',
    'tiktok_uploader.Browser',
    'tiktok_uploader.cookies',
    'tiktok_uploader.Config',
    'tiktok_uploader.Video',
    'tiktok_uploader.basics',
    'tiktok_uploader.bot_utils',
    'tiktok_uploader.tiktok-signature.index',
    'tiktok_uploader.tiktok-signature.browser',
    'tiktok_uploader.tiktok-signature.utils',
    'tiktok_uploader.tiktok-signature.javascript.signer',
    'tiktok_uploader.tiktok-signature.javascript.webmssdk',
    'tiktok_uploader.tiktok-signature.javascript.xbogus',
]

# Collect data files
datas = collect_data_files('tiktok_uploader')
