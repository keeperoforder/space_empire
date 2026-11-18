# PyInstaller spec for Space Empire (onedir; reliable asset/data loading).
from pathlib import Path
root=Path(SPECPATH)
datas=[
    (str(root/"assets"),"assets"),
    (str(root/"buildings"/"catalog.json"),"buildings"),
    (str(root/"technology"/"technology_tree.json"),"technology"),
    (str(root/"galaxy"/"galaxy_catalog.json"),"galaxy"),
    (str(root/"automation"/"market.json"),"automation"),
    (str(root/"campaign"/"campaign.json"),"campaign"),
    (str(root/"colonies"/"planet_types.json"),"colonies"),
    (str(root/"progression"/"progression.json"),"progression"),
    (str(root/"progression"/"tutorial.json"),"progression"),
    (str(root/"progression"/"campaign_progression.json"),"progression"),
]
a=Analysis(["main.py"],pathex=[str(root)],binaries=[],datas=datas,hiddenimports=["pygame","pygame.mixer"],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name="SpaceEmpire",debug=False,bootloader_ignore_signals=False,strip=False,upx=True,console=False,icon=str(root/"assets"/"icons"/"space_empire.ico"))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=True,upx_exclude=[],name="SpaceEmpire")
