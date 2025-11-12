import streamlit as st
import plotly.graph_objects as go
import trimesh
import os
import pandas as pd
import numpy as np
import tempfile
import zipfile
from io import BytesIO


st.set_page_config(page_title="Impression Browser", layout="wide")

st.markdown("""
    <style>
    /* Większe radio buttons */
    div[role='radiogroup'] label {
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        margin: 4px 8px !important;
        border: 2px solid #bbb !important;
        border-radius: 10px !important;
        background-color: #f8f9fa !important;
        transition: all 0.2s ease-in-out;
    }
    /* Efekt po najechaniu */
    div[role='radiogroup'] label:hover {
        background-color: #e6f0ff !important;
        border-color: #007bff !important;
    }
    /* Zaznaczony */
    div[role='radiogroup'] label[data-baseweb='radio']:has(input:checked),
    div[role='radiogroup'] label:has(input:checked) {
        background-color: #007bff !important;
        color: white !important;
        border-color: #0056b3 !important;
    }

    /* Większe przyciski (Zapisz, Pomiń itp.) */
    button[kind="primary"], button[kind="secondary"] {
        font-size: 20px !important;
        padding: 12px 28px !important;
        border-radius: 10px !important;
    }
            
    h1#impression-orientation-classifier-and-editor {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
    }
            
    </style>
""", unsafe_allow_html=True)

# st.markdown("""
#     <style>
#     /* Ukryj każdy pojedynczy plik */
#     [data-testid="stFileUploaderFile"] {
#         display: none !important;
#     }

#     /* ❗ NOWY, POPRAWNY SELEKTOR DLA CAŁEGO WIDŻETU PAGINACJI ❗ */
#     [data-testid="stFileUploaderPagination"] {
#         display: none !important;
#     }

#     /* Wersja alternatywna (na wypadek zmian w HTML Streamlita) */
#     [data-testid="stFileUploader"] p {
#         display: none !important;
#     }

#     </style>
# """, unsafe_allow_html=True)


st.title("Impression Orientation Classifier and Editor")


uploaded_files = st.file_uploader(
    "Upload one or more STL files", 
    type=["stl"], 
    accept_multiple_files=True
    
)

if "folder" not in st.session_state:
    st.session_state.folder = tempfile.mkdtemp()
folder = st.session_state.folder

processed_dir = os.path.join(folder, "processed")
os.makedirs(processed_dir, exist_ok=True)

if not uploaded_files:
    st.info("Please upload STL files to start.")
    st.stop()

# --- CSV ---
csv_path = os.path.join(folder, "labels.csv")

if "labels_df" not in st.session_state:
    if os.path.exists(csv_path):
        st.session_state.labels_df = pd.read_csv(csv_path)
    else:
        st.session_state.labels_df = pd.DataFrame(columns=[
            "original_filename", "new_filename", "side", "band",
            "rotation_x", "rotation_y", "rotation_z"
        ])

# 📦 Zapisz wgrane pliki do folderu tymczasowego
for file in uploaded_files:
    file_path = os.path.join(folder, file.name)
    with open(file_path, "wb") as f:
        f.write(file.getbuffer())

# 📋 Lista plików STL do przetworzenia
files = [f.name for f in uploaded_files if f.name.lower().endswith(".stl")]

if not files:
    st.success("🎉 All Files processed!")
    st.dataframe(st.session_state.labels_df)
    st.stop()

# --- Stan sesji ---
if "scan_index" not in st.session_state:
    st.session_state.scan_index = len(os.listdir(processed_dir)) + 1
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "rot_x" not in st.session_state:
    st.session_state.rot_x = 0
if "rot_y" not in st.session_state:
    st.session_state.rot_y = 0
if "rot_z" not in st.session_state:
    st.session_state.rot_z = 0
if "side_selection" not in st.session_state:
    st.session_state.side_selection = ""
if "band_selection" not in st.session_state:
    st.session_state.band_selection = ""

if "total_files" not in st.session_state:
    st.session_state.total_files = len(files)

remaining = st.session_state.total_files - st.session_state.current_index
st.markdown(f"### 📊 Files remaining: **{remaining} / {st.session_state.total_files}**")


# --- Aktualny plik ---
if st.session_state.current_index >= len(files):
    st.success("✅ All files processed!")
    st.dataframe(st.session_state.labels_df)
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for filename in os.listdir(processed_dir):
            file_path = os.path.join(processed_dir, filename)
            zipf.write(file_path, arcname=filename)
        st.session_state.labels_df.to_csv(csv_path, index=False)
        zipf.write(csv_path, arcname="labels.csv")
    zip_buffer.seek(0)
    st.download_button(
        label="📦 Download files (.zip)",
        data=zip_buffer,
        file_name="processed_files.zip",
        mime="application/zip"
    )
    st.stop()


selected_file = files[st.session_state.current_index]
file_path = os.path.join(folder, selected_file)

# --- Wczytaj model ---
try:
    mesh = trimesh.load_mesh(file_path)
except Exception as e:
    st.error(f"Failed to load file {selected_file}: {e}")
    st.stop()

# 📁 Folder z plikami STL
#folder = st.text_input("Path to the folder with STL files:", "data/ears")

#if not os.path.exists(folder):
#    st.warning("Folder does not exist.")
#    st.stop()


# --- INICJALIZACJA STANU SESJI ---
# 🧠 Numer skanu
if "scan_index" not in st.session_state:
    st.session_state.scan_index = len(os.listdir(processed_dir)) + 1

# 🔁 Rotacje — stan
for axis in ["rot_x", "rot_y", "rot_z"]:
    if axis not in st.session_state:
        st.session_state[axis] = 0

# 🏷️ Stan etykiet
if "side_selection" not in st.session_state:
    st.session_state.side_selection = ""
if "band_selection" not in st.session_state:
    st.session_state.band_selection = ""

# 📝 Aktualny plik (teraz ustawiany za każdym razem na files[0])
st.session_state.current_file = selected_file # Zapisujemy nazwę aktualnego pliku do stanu

# 📊 Wczytaj model
try:
    # Model wczytujemy na podstawie selected_file, który jest aktualnym files[0]
    mesh = trimesh.load_mesh(file_path) 
except Exception as e:
    st.error(f"Failed to load file {selected_file}: {e}")
    st.stop()


# 🔢 Funkcja obrotu (poza callbackiem)
def rotate_mesh(mesh, rx, ry, rz):
    # Zabezpieczenie przed brakiem trimesh.transformations
    if 'trimesh.transformations' not in globals():
        import trimesh.transformations
    mx = trimesh.transformations.rotation_matrix(np.radians(rx), [1, 0, 0])
    my = trimesh.transformations.rotation_matrix(np.radians(ry), [0, 1, 0])
    mz = trimesh.transformations.rotation_matrix(np.radians(rz), [0, 0, 1])
    # Zastosuj transformację
    # Używamy np.dot zamiast operatora @ w celu kompatybilności
    transform = np.dot(mx, np.dot(my, mz))
    mesh.apply_transform(transform)
    return mesh

def center_mesh(mesh):
    """
    Przesuwa siatkę tak, by środek jej osiowy znalazł się w (0, 0, 0).
    """
    # Można użyć środka bounding boxa lub środka masy
    center = mesh.center_mass
    mesh.apply_translation(-center)
    return mesh


def skip_file():
    current_file = st.session_state.current_file
    try:
        # Przenieś pominięty plik do folderu backup, aby nie był ponownie wczytany
        st.toast(f"File skipped: {current_file}", icon="➡️")
    except Exception as e:
        st.error(f"Error: {e}")
        return

    # Zwiększamy indeks skanu, aby zachować ciągłość numeracji
        # 🔄 RESETOWANIE STANU SESJI
    st.session_state.scan_index += 1
    st.session_state.current_index += 1
    st.session_state.rot_x = 0
    st.session_state.rot_y = 0
    st.session_state.rot_z = 0
    st.session_state.side_selection = ""
    st.session_state.band_selection = ""
    
  

# 💾 FUNKCJA CALLBACK
def reset_and_process():
    selected_file = files[st.session_state.current_index]
    file_path = os.path.join(folder, selected_file)

    side = st.session_state.side_selection
    band = st.session_state.band_selection
    if side == "" or band == "":
        st.error("Please select side and canal length.")
        return
    rot_x = st.session_state.rot_x
    rot_y = st.session_state.rot_y
    rot_z = st.session_state.rot_z
    band_code = {"too short": 0, "1st band": 1, "2nd band": 2}[band]
    scan_num = st.session_state.scan_index
    new_name = f"{scan_num}{side}_{band_code}.stl"
    new_path = os.path.join(processed_dir, new_name)

    try:
        mesh = trimesh.load_mesh(file_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.dump()))

        mesh = rotate_mesh(mesh, rot_x, rot_y, rot_z)
        mesh = center_mesh(mesh)
        mesh.export(new_path)
    except Exception as e:
        st.error(f"Error while saving: {e}")
        return

    # --- Zapisz do CSV ---
    new_row = pd.DataFrame([[selected_file, new_name, side, band, rot_x, rot_y, rot_z]],
                           columns=st.session_state.labels_df.columns)
    st.session_state.labels_df = pd.concat(
        [st.session_state.labels_df, new_row],
        ignore_index=True
    )
    st.session_state.labels_df.to_csv(csv_path, index=False)

    st.toast(f"💾 Saved as {new_name}")
    st.session_state.scan_index += 1
    st.session_state.current_index += 1
    st.session_state.rot_x = 0
    st.session_state.rot_y = 0
    st.session_state.rot_z = 0
    st.session_state.side_selection = ""
    st.session_state.band_selection = ""
   
    
    # Po zakończeniu callbacku Streamlit automatycznie przeładuje skrypt,
    # co spowoduje odświeżenie listy 'files' i wybranie kolejnego pliku.


# 🔄 Suwaki rotacji
st.subheader("Set new orientation")
col1, col2, col3 = st.columns(3)
with col1:
    # Używamy key dla płynnej interakcji
    st.slider("Rotation X (°)", -180, 180, key="rot_x", step=5)
with col2:
    st.slider("Rotation Y (°)", -180, 180, key="rot_y", step=5)
with col3:
    st.slider("Rotation Z (°)", -180, 180, key="rot_z", step=5)

# 🔍 Obrócony model (Używa wartości z session_state)
rotated_mesh = mesh.copy()
rotated_mesh = rotate_mesh(rotated_mesh, st.session_state.rot_x, st.session_state.rot_y, st.session_state.rot_z)
x, y, z = rotated_mesh.vertices.T
i, j, k = rotated_mesh.faces.T



# --- Wizualizacja Plotly (bez zmian) ---
fig = go.Figure(data=[
    go.Mesh3d(
        x=x, y=y, z=z, 
        i=i, j=j, k=k, 
        color='lightblue',
        lighting=dict(ambient=0.5, diffuse=0.5, roughness=0.5, specular=0.3),
        opacity=1,
        lightposition=dict(
            x=100, y=200, z=300
        )
    )
])
    
fig.update_layout(
    scene=dict(
        xaxis=dict(
            title=dict(
                text='X',
                font=dict(size=18, family='Arial', color='red', weight='bold')
            ),
            showgrid=True,
            linewidth=4,
            linecolor='red'
        ),
        yaxis=dict(
            title=dict(
                text='Y',
                font=dict(size=18, family='Arial', color='green', weight='bold')
            ),
            showgrid=True,
            linewidth=4,
            linecolor='green'
        ),
        zaxis=dict(
            title=dict(
                text='Z',
                font=dict(size=18, family='Arial', color='blue', weight='bold')
            ),
            showgrid=True,
            linewidth=4,
            linecolor='blue'
        ),
        aspectmode='data',
        camera=dict(
            eye=dict(x=0, y=-2, z=0.1) # = rotacja Y
            #eye=dict(x=2, y=0, z=0.1) # = rotacja X
            #eye=dict(x=0, y=0, z=2) # = rotacja Z
        ),
        #bgcolor="rgba(30, 30, 30, 1)"
    ),
    paper_bgcolor="rgba(20, 20, 20, 0.2)",
    height=600,
    margin=dict(l=0, r=0, b=0, t=0)
)

st.plotly_chart(fig, use_container_width=True)

# 🏷️ Etykiety

col1, col2, col3 = st.columns([2,2,1], border=True)
with col1:
    pass
with col2:
    st.radio("Side:", ["L","", "R"], key="side_selection", horizontal=True)
    st.radio("Canal length:", ["","too short", "1st band", "2nd band"], key="band_selection", horizontal=True)
with col3:
    st.button("💾 Save and next file", on_click=reset_and_process)
    st.button("⏭️ Skip file", on_click=skip_file)

    # --- ZIP zawsze dostępny ---
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for filename in os.listdir(processed_dir):
            file_path = os.path.join(processed_dir, filename)
            zipf.write(file_path, arcname=filename)
        st.session_state.labels_df.to_csv(csv_path, index=False)
        zipf.write(csv_path, arcname="labels.csv")
    zip_buffer.seek(0)
    st.download_button(
        label="📦 Download files (.zip)",
        data=zip_buffer,
        file_name="processed_files.zip",
        mime="application/zip",
        disabled=len(os.listdir(processed_dir)) == 0  # nieaktywny, gdy brak plików
    )


st.subheader(f"File in use: `{selected_file}`")


# 📜 Podgląd etykiet
st.subheader("Labels:")
st.dataframe(st.session_state.labels_df)
#st.dataframe(labels_df.tail(10))

