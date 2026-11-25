#!/usr/bin/env bash
set -euo pipefail
LONGCAT_SOURCE_COMMIT=58eb336edc5c8c63389838727e40b8c18434e54e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LONGCAT_RUNTIME="${LONGCAT_RUNTIME:-$SCRIPT_DIR/runtime}"
export LONGCAT_RUNTIME
mkdir -p "$LONGCAT_RUNTIME"
LONGCAT_RUNTIME="$(cd "$LONGCAT_RUNTIME" && pwd)"
export LONGCAT_RUNTIME
command -v nvidia-smi >/dev/null || { echo 'É necessária uma máquina Linux com GPU NVIDIA.'; exit 1; }
python3 - <<'PY'
import subprocess, shutil, os
row = subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,compute_cap','--format=csv,noheader,nounits'], text=True).strip().splitlines()[0]
memory, capability = (float(v.strip()) for v in row.split(','))
if memory < 76000:
    raise SystemExit('Este instalador foi preparado para uma GPU com aproximadamente 80 GB ou mais.')
if capability >= 10:
    raise SystemExit('GPU Blackwell: a pilha CUDA/PyTorch fixada precisa de uma adaptação antes de instalar.')
if shutil.disk_usage(os.environ['LONGCAT_RUNTIME']).free < 130 * 1024**3:
    raise SystemExit('Reserve pelo menos 130 GiB livres antes da instalação.')
PY
if ! command -v conda >/dev/null; then
    if [[ ! -x "$LONGCAT_RUNTIME/miniforge/bin/conda" ]]; then
        curl --fail --location --retry 3 https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -o "$LONGCAT_RUNTIME/miniforge.sh"
        bash "$LONGCAT_RUNTIME/miniforge.sh" -b -p "$LONGCAT_RUNTIME/miniforge"
    fi
    export PATH="$LONGCAT_RUNTIME/miniforge/bin:$PATH"
fi
source "$(conda info --base)/etc/profile.d/conda.sh"
if [[ ! -x "$LONGCAT_RUNTIME/env/bin/python" ]]; then
    conda create -y -p "$LONGCAT_RUNTIME/env" python=3.10
fi
conda activate "$LONGCAT_RUNTIME/env"
if [[ ! -d "$LONGCAT_RUNTIME/LongCat-Video/.git" ]]; then
    git clone https://github.com/meituan-longcat/LongCat-Video.git "$LONGCAT_RUNTIME/LongCat-Video"
    git -C "$LONGCAT_RUNTIME/LongCat-Video" checkout --detach "$LONGCAT_SOURCE_COMMIT"
fi
cd "$LONGCAT_RUNTIME/LongCat-Video"
[[ "$(git rev-parse HEAD)" == "$LONGCAT_SOURCE_COMMIT" ]] || { echo 'A versão do código é diferente da validada; revise antes de atualizar.'; exit 1; }
python -m pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
python -m pip install ninja psutil packaging
python -m pip install flash_attn==2.7.4.post1 --no-build-isolation
conda install -y -c conda-forge librosa ffmpeg=5.1.0 lame=3.100 libsndfile=1.2.2 mpg123=1.32.9
python - <<'PY'
from pathlib import Path
for name in ('requirements.txt', 'requirements_avatar.txt'):
    lines = Path(name).read_text().splitlines()
    # These two entries are not installable PyPI packages in the upstream list.
    lines = [s for s in lines if not s.startswith(('libsndfile1==', 'tritonserverclient==', 'flash-attn=='))]
    Path('../' + name).write_text('\n'.join(lines) + '\n')
PY
python -m pip install -r ../requirements.txt -r ../requirements_avatar.txt 'huggingface_hub>=0.26,<1'
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('meituan-longcat/LongCat-Video', local_dir='weights/LongCat-Video', allow_patterns=['tokenizer/*','text_encoder/*','vae/*','*.json'])
snapshot_download('meituan-longcat/LongCat-Video-Avatar-1.6', local_dir='weights/LongCat-Video-Avatar-1.6')
PY
printf '\nInstalação concluída. No próximo terminal, ative:\nsource "%s/etc/profile.d/conda.sh"\nconda activate "%s/env"\n' "$(conda info --base)" "$LONGCAT_RUNTIME"
printf '\nAbra a interface:\npython -m streamlit run "%s/app.py" --server.address 127.0.0.1 --server.port 8501\n' "$SCRIPT_DIR"
