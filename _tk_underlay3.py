import tkinter as tk
from pathlib import Path
root = tk.Tk()
root.title("underlay")
root.overrideredirect(True)
root.geometry("420x620+1420+430")
root.attributes("-topmost", False)
marker = Path(r"F:\WhaleGirlPet\docs\_click_through_marker.txt")
def hit():
    marker.write_text("clicked")
b = tk.Button(root, text="underlay button", command=hit, bg="yellow")
b.place(x=0, y=0, width=180, height=100)
root.mainloop()
