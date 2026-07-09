Running

pip install -r requirements.txt

python app.py

Building

pip install -r requirements.txt pyinstaller

  pyinstaller --noconfirm --onefile --windowed \
  
  --name RemoveLoopPoints \
  
  --collect-all customtkinter \
  
  --collect-all tkinterdnd2 \
  
  app.py

  
