import cv2
import torch
import numpy as np
from ultralytics import YOLO

# Cek GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Load model YOLO ke GPU
model = YOLO("yolov8l.pt").to(device)

# Kelas kendaraan yang mau dihitung
target_classes = ["car", "truck", "bus"]

# Ambil ID kelas COCO yang sesuai
coco_classes = model.names
target_class_ids = [i for i, name in coco_classes.items() if name in target_classes]

# Link CCTV
url = "https://mitradarat-vidstream.kemenhub.go.id//stream//KM160AKM160A//stream.m3u8"

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 10)

if not cap.isOpened():
    print("Gagal membuka stream")
    exit()

# Inisialisasi posisi garis & counter
line_y = 400  # Posisi garis di tengah frame
vehicle_count = 0
detected_vehicles = set()  

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal membaca frame, lanjut...")
        continue  

    # Resize frame ke 640x640 buat YOLO
    frame_resized = cv2.resize(frame, (640, 640))
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

    # Convert ke Tensor & Normalisasi
    frame_tensor = torch.from_numpy(frame_rgb).float() / 255.0
    frame_tensor = frame_tensor.permute(2, 0, 1).unsqueeze(0).to(device)

    # Deteksi objek
    results = model(frame_tensor)

    # Gambar garis counting
    cv2.line(frame_resized, (0, line_y), (640, line_y), (0, 255, 255), 2)

    # Gambar bounding box untuk kendaraan aja
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls.item())  
            conf = float(box.conf.item())  

            if cls_id in target_class_ids:  
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())  
                label = f"{coco_classes[cls_id]} {conf:.2f}"  

                # Hitung kendaraan kalau lewat garis
                center_y = (y1 + y2) // 2  
                vehicle_id = f"{cls_id}_{x1}"  # ID unik buat kendaraan

                if vehicle_id not in detected_vehicles and center_y > line_y - 10 and center_y < line_y + 10:
                    vehicle_count += 1
                    detected_vehicles.add(vehicle_id)

                # Gambar bounding box
                cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame_resized, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.putText(frame_resized, f"Count: {vehicle_count}", (500, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("CCTV Stream (Vehicle Counting)", frame_resized)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
