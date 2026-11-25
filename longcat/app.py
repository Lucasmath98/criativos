"""Local upload interface. Launch inside the LongCat Conda environment."""
from pathlib import Path
import uuid
import streamlit as st
from generate import RUNTIME, make_job, run_job

st.set_page_config(page_title="Estúdio de Criativos", page_icon="🎬")
st.title("Estúdio de Criativos")
st.write("Envie a foto do personagem e a narração pronta para criar seu vídeo.")
photo = st.file_uploader("Foto do personagem", type=["jpg", "jpeg", "png", "webp"])
audio = st.file_uploader("Narração", type=["mp3", "wav", "m4a"])
prompt = st.text_area("Descrição da cena em inglês", value=(
    "A woman in a home kitchen, wearing an apron, speaking naturally to the camera. "
    "Gentle head movements, natural facial expressions, stable framing and soft lighting."
))
short = st.checkbox("Fazer primeiro um teste curto de até 3,72 segundos", value=True)
if st.button("Gerar vídeo", disabled=not (photo and audio and prompt.strip())):
    folder = RUNTIME / "uploads" / uuid.uuid4().hex
    folder.mkdir(parents=True)
    image_path = folder / ("photo" + Path(photo.name).suffix.lower())
    audio_path = folder / ("voice" + Path(audio.name).suffix.lower())
    image_path.write_bytes(photo.getvalue())
    audio_path.write_bytes(audio.getvalue())
    try:
        with st.spinner("Preparando e gerando seu vídeo…"):
            job = make_job(image_path, audio_path, prompt, test=short)
            result = run_job(job)
        st.session_state["result"] = str(result)
        st.success("Vídeo pronto!")
    except Exception as exc:
        st.error(str(exc))

if st.session_state.get("result"):
    result = Path(st.session_state["result"])
    if result.is_file():
        st.video(str(result))
        st.download_button("Baixar vídeo", result.read_bytes(), file_name="criativo.mp4", mime="video/mp4")
