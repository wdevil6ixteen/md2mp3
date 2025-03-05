import tkinter as tk
from tkinter import filedialog, messagebox
import markdown
import pyttsx3
import os
import threading
import queue
from bs4 import BeautifulSoup
from langdetect import detect
from tkinterdnd2 import DND_FILES, TkinterDnD  

class MarkdownSpeaker:
    def __init__(self, master):
        self.master = master
        self.master.title("Markdown Speaker")
        self.master.geometry("400x250")

        self.master.drop_target_register(DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.on_drop)

        self.label = tk.Label(master, text="Перетащите сюда файл .md", padx=10, pady=10)
        self.label.pack(expand=True)

        self.button = tk.Button(master, text="Выбрать файл", command=self.open_file)
        self.button.pack(pady=5)
        
        self.stop_button = tk.Button(master, text="Остановить", command=self.stop_speech)
        self.stop_button.pack(pady=5)

        self.engine = pyttsx3.init()
        self.is_speaking = False 
        self.speech_thread = None  
        self.text_queue = queue.Queue()  

       
        # self.engine.setProperty('rate', 130)  
        # self.engine.setProperty('pitch', 70)  

    def on_drop(self, event):
        file_path = event.data.strip("{}")
        if file_path.endswith('.md'):
            self.convert_and_speak(file_path)
        else:
            messagebox.showerror("Ошибка", "Пожалуйста, перетащите файл .md")

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Markdown Files", "*.md")])
        if file_path:
            self.convert_and_speak(file_path)

    def convert_and_speak(self, markdown_file):
        if self.is_speaking:  
            messagebox.showwarning("Внимание", "Озвучивание уже идет. Остановите его перед запуском нового.")
            return

        try:
            with open(markdown_file, 'r', encoding='utf-8') as file:
                markdown_content = file.read()
            
            html = markdown.markdown(markdown_content)
            soup = BeautifulSoup(html, 'html.parser')
            plain_text = soup.get_text().strip()
            
            if not plain_text:
                messagebox.showerror("Ошибка", "Файл пуст или не содержит текста.")
                return

            lang = detect(plain_text)  
            self.engine.setProperty('voice', self.get_voice_for_lang(lang))
            
            self.is_speaking = True  
            self.text_queue.queue.clear()  
            self.text_queue.put(plain_text)
            
          
            self.speech_thread = threading.Thread(target=self.speak_text, daemon=True)
            self.speech_thread.start()

           
            messagebox.showinfo("Успех", "Озвучивание началось!")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось озвучить файл:\n{str(e)}")
    
    def speak_text(self):
        while self.is_speaking and not self.text_queue.empty():
            text = self.text_queue.get()
            sentences = text.split(". ")  
            for sentence in sentences:
                if not self.is_speaking:
                    break
                self.engine.say(sentence)
                self.engine.runAndWait()
        
        self.is_speaking = False
        if not self.text_queue.empty():
            messagebox.showinfo("Успех", "Озвучивание завершено!")

    def get_voice_for_lang(self, lang):
        voices = self.engine.getProperty('voices')
        if lang == 'ru':
            for voice in voices:
                if "russian" in voice.name.lower():
                    return voice.id
        return voices[0].id
    
    def stop_speech(self):
        if not self.is_speaking:
            messagebox.showwarning("Внимание", "Озвучивание уже остановлено.")
            return

        self.is_speaking = False 
        self.engine.stop()  
        messagebox.showinfo("Остановлено", "Озвучивание остановлено.") 

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = MarkdownSpeaker(root)
    root.mainloop()
