import cdsapi
import os
import zipfile
import shutil

os.makedirs("data", exist_ok=True)
c = cdsapi.Client()

AREA = [-22.5, -44.0, -23.5, -43.0]
TIMES = ["00:00", "03:00", "06:00", "09:00",
         "12:00", "15:00", "18:00", "21:00"]
DATE_RANGE = "2008-01-01/2025-12-31"

SINGLE_LEVEL = [
    ("particulate_matter_2.5um", "pm25"),
    ("particulate_matter_10um",  "pm10"),
]

MULTI_LEVEL = [
    ("sulphur_dioxide", "so2", "1000"),
]

def download_and_extract(var_name, fname, extra_params=None):
    out = f"data/{fname}.nc"
    if os.path.exists(out):
        print(f"⏭️  {fname}.nc já existe, a saltar")
        return
    print(f"⬇️  A descarregar {var_name}...")
    params = {
        "variable": var_name,
        "date": DATE_RANGE,
        "time": TIMES,
        "area": AREA,
        "format": "netcdf_zip",
    }
    if extra_params:
        params.update(extra_params)

    zip_path = f"data/{fname}.zip"
    c.retrieve("cams-global-reanalysis-eac4", params, zip_path)

    # Extrair para pasta temporária
    tmp_dir = f"data/{fname}_tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp_dir)
    os.remove(zip_path)

    # Mover o ficheiro .nc extraído para o nome correto
    for f in os.listdir(tmp_dir):
        if f.endswith(".nc"):
            shutil.move(os.path.join(tmp_dir, f), out)
            break

    # Limpar pasta temporária
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"✅ {fname}.nc pronto")

for var_name, fname in SINGLE_LEVEL:
    download_and_extract(var_name, fname)

for var_name, fname, pressure in MULTI_LEVEL:
    download_and_extract(var_name, fname, {"pressure_level": pressure})

print("\n🎉 Tudo descarregado para ./data/")