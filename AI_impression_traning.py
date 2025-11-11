import streamlit as st
import plotly.graph_objects as go
import trimesh
import os
import pandas as pd
import shutil
import numpy as np

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


st.title("Impression Orientation Classifier and Editor")


uploaded_files = st.file_uploader(
    "Upload one or more STL files", 
    type=["stl"], 
    accept_multiple_files=True
    
)

st.markdown("""
    <style>
    /* Ukryj każdy pojedynczy plik */
    [data-testid="stFileUploaderFile"] {
        display: none !important;
    }

    /* Ukryj listę plików */
    [data-testid="stFileUploaderFileList"] {
        display: none !important;
    }

    /* ❗ NOWY, POPRAWNY SELEKTOR DLA CAŁEGO WIDŻETU PAGINACJI ❗ */
    [data-testid="stFileUploaderPagination"] {
        display: none !important;
    }
    
    /* Wciąż trzymaj ten poniżej jako zabezpieczenie, choć rzadko działa sam */
    [data-testid="stFileUploaderFilePaginator"] {
        display: none !important;
    }

    /* Wersja alternatywna (na wypadek zmian w HTML Streamlita) */
    [data-testid="stFileUploader"] p {
        display: none !important;
    }

    /* Poprawka estetyczna */
    [data-testid="stFileUploaderDropzone"] {
        margin-bottom: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)


if uploaded_files:
    import tempfile, os
    folder = tempfile.mkdtemp()
    for file in uploaded_files:
        with open(os.path.join(folder, file.name), "wb") as f:
            f.write(file.getbuffer())
    st.success(f"{len(uploaded_files)} files uploaded successfully.")
else:
    st.info("Please upload STL files to start.")
    st.stop()



# 📁 Folder z plikami STL
#folder = st.text_input("Path to the folder with STL files:", "data/ears")

#if not os.path.exists(folder):
#    st.warning("Folder does not exist.")
#    st.stop()

# 📂 Folder docelowy
processed_dir = os.path.join(folder, "processed")
backup_dir = os.path.join(folder, "backup")
os.makedirs(processed_dir, exist_ok=True)
os.makedirs(backup_dir, exist_ok=True)

# 📄 CSV z etykietami
csv_path = os.path.join(folder, "labels.csv")
if os.path.exists(csv_path):
    labels_df = pd.read_csv(csv_path)
else:
    labels_df = pd.DataFrame(columns=["original_filename", "new_filename", "side", "band", "rotation_x", "rotation_y", "rotation_z"])

# 📋 Pliki do przetworzenia (odświeżane przy każdym uruchomieniu skryptu)
files = [
    f for f in os.listdir(folder)
    if f.lower().endswith(".stl") and os.path.isfile(os.path.join(folder, f)) and f != "labels.csv"
]

if not files:
    st.success("🎉 All Files processed!")
    st.dataframe(labels_df) # Wyświetlenie końcowej tabeli z etykietami
    st.stop()

# ⚠️ UŻYCIE PIERWSZEGO PLIKU Z AKTUALNEJ LISTY
selected_file = files[0] 
file_path = os.path.join(folder, selected_file)

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


def skip_file():
    current_file = st.session_state.current_file
    original_path = os.path.join(folder, current_file)

    try:
        # Przenieś pominięty plik do folderu backup, aby nie był ponownie wczytany
        shutil.move(original_path, os.path.join(backup_dir, current_file))
        st.toast(f"File skipped: {current_file}", icon="➡️")
    except Exception as e:
        st.error(f"Error: {e}")
        return

    # Zwiększamy indeks skanu, aby zachować ciągłość numeracji
        # 🔄 RESETOWANIE STANU SESJI
    st.session_state.rot_x = 0
    st.session_state.rot_y = 0
    st.session_state.rot_z = 0
    st.session_state.side_selection = ""
    st.session_state.band_selection = ""
    st.session_state.scan_index += 1
    st.session_state.scan_index += 1
  

# 💾 FUNKCJA CALLBACK
def reset_and_process():
    # Pobranie danych ze stanu sesji
    side = st.session_state.side_selection
    band = st.session_state.band_selection
    rot_x = st.session_state.rot_x
    rot_y = st.session_state.rot_y
    rot_z = st.session_state.rot_z

    if side == "":
        st.error("Select impression side:")
        return

    if band == "":
        st.error("Select canal length:")
        return

    # Przetwarzanie nazwy
    band_code = {"too short": 0, "1st band": 1, "2nd band": 2}[band]
    scan_num = st.session_state.scan_index
    current_file = st.session_state.current_file # Nazwa pliku jest w sesji
    
    new_name = f"{scan_num}{side}_{band_code}.stl"
    new_path = os.path.join(processed_dir, new_name)
    original_path = os.path.join(folder, current_file)

    # 🔸 Wczytaj ponownie, zastosuj rotację i zapisz
    try:
        final_mesh = trimesh.load_mesh(original_path)
        final_mesh = rotate_mesh(final_mesh, rot_x, rot_y, rot_z)
        final_mesh.export(new_path)
    except Exception as e:
        st.error(f"Can't save file: {e}")
        return # Przerwij funkcję jeśli błąd zapisu

    # 🔸 Usuń (Przenieś) oryginalny plik
    try:
        shutil.move(original_path, os.path.join(backup_dir, current_file))
    except Exception as e:
        st.error(f"Can't move file: {e}")
        return

    # 🔸 Zapisz do CSV
    global labels_df # Użycie globalnej zmiennej DataFrame
    new_row = pd.DataFrame([[current_file, new_name, side, band, rot_x, rot_y, rot_z]],
                            columns=["original_filename", "new_filename", "side", "band", "rotation_x", "rotation_y", "rotation_z"])
    labels_df = pd.concat([labels_df, new_row], ignore_index=True)
    labels_df.to_csv(csv_path, index=False)
    
    st.toast(f"Saved as: {new_name}", icon="💾")

    # 🔄 RESETOWANIE STANU SESJI
    st.session_state.rot_x = 0
    st.session_state.rot_y = 0
    st.session_state.rot_z = 0
    st.session_state.side_selection = ""
    st.session_state.band_selection = ""
    st.session_state.scan_index += 1
    
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
    st.radio("Side:", ["L","", "R"], key="side_selection", horizontal=True)
with col2:
    st.radio("Canal length:", ["","too short", "1st band", "2nd band"], key="band_selection", horizontal=True)
with col3:
    st.markdown("""
        <style>
        .right-align {
            display: flex;
            flex-direction: column;
            align-items: flex-end; /* wyrównanie do prawej */
            gap: 8px;
        }
        .right-align button {
            min-width: 18px; /* opcjonalnie: szerokość przycisków */
        }
        </style>
        <div class="right-align">
    """, unsafe_allow_html=True)

    # 💾 Zapis i przejście dalej
    st.button("Save and next file", on_click=reset_and_process)
    # ⏭️ Pominięcie pliku
    st.button("Skip file", on_click=skip_file)

    st.markdown("</div>", unsafe_allow_html=True)


st.subheader(f"File in use: `{selected_file}`")


# 📜 Podgląd etykiet
st.subheader("Labels:")
st.dataframe(labels_df)
#st.dataframe(labels_df.tail(10))
